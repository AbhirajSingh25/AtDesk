from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from sqlalchemy.orm import selectinload
from backend.app.models.models import (
    Shop, ShopSettlement, SettlementItem, ShopPrepaidAccount, 
    ShopPrepaidLedger, MasterOrder, VendorOrder, Refund, 
    SettlementStatus, RefundStatus, SettlementType, AuditLog,
    OrderUnitEconomics, MasterOrderStatus, VendorOrderStatus
)

class FinanceService:
    @staticmethod
    async def get_or_create_prepaid_account(db: AsyncSession, shop_id: int, lock: bool = False) -> ShopPrepaidAccount:
        """Fetch shop prepaid account with optional row-level database lock (SELECT ... FOR UPDATE)"""
        stmt = select(ShopPrepaidAccount).where(ShopPrepaidAccount.shop_id == shop_id)
        if lock:
            # SQLite does not support FOR UPDATE (it locks the entire DB in write transactions),
            # but in PostgreSQL FOR UPDATE ensures atomic serialization between concurrent workers.
            # We check the dialect or apply safely.
            bind = db.get_bind()
            if bind and bind.dialect.name != "sqlite":
                stmt = stmt.with_for_update()

        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if not account:
            account = ShopPrepaidAccount(
                shop_id=shop_id,
                current_balance=Decimal("5000.00"),  # Default initial seed buffer
                min_threshold_alert=Decimal("1500.00"),
                is_low_balance_alerted=False
            )
            db.add(account)
            await db.flush()
        return account

    @staticmethod
    async def debit_prepaid_for_order(
        db: AsyncSession, 
        shop_id: int, 
        amount: Decimal, 
        vendor_order_id: int
    ) -> bool:
        """
        Atomically deduct confirmed order payable from prepaid shop account.
        Uses row-level locking to guarantee no concurrent balance overdraft.
        """
        account = await FinanceService.get_or_create_prepaid_account(db, shop_id, lock=True)
        
        # Check existing debit to guarantee idempotency
        existing_debit = await db.execute(
            select(ShopPrepaidLedger).where(
                and_(
                    ShopPrepaidLedger.shop_id == shop_id,
                    ShopPrepaidLedger.reference_id == f"VORD-{vendor_order_id}"
                )
            )
        )
        if existing_debit.scalar_one_or_none():
            # Already debited
            return True

        if account.current_balance < amount:
            # Insufficient prepaid balance
            return False

        account.current_balance -= amount
        if account.current_balance < account.min_threshold_alert:
            account.is_low_balance_alerted = True

        ledger = ShopPrepaidLedger(
            shop_id=shop_id,
            account_id=account.id,
            transaction_type="DEBIT_ORDER",
            amount=amount,
            balance_after=account.current_balance,
            reference_id=f"VORD-{vendor_order_id}",
            notes=f"Order fulfillment deduction for Vendor Order #{vendor_order_id}"
        )
        db.add(ledger)
        await db.flush()
        return True

    @staticmethod
    async def credit_prepaid_topup(
        db: AsyncSession,
        shop_id: int,
        amount: Decimal,
        reference_id: str,
        admin_user: str,
        notes: Optional[str] = None
    ) -> ShopPrepaidAccount:
        """Finance admin records a verified advance top-up for a prepaid shop"""
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Deposit amount must be strictly positive")

        # Idempotency check on reference_id
        existing = await db.execute(
            select(ShopPrepaidLedger).where(
                and_(
                    ShopPrepaidLedger.shop_id == shop_id,
                    ShopPrepaidLedger.reference_id == reference_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Duplicate top-up reference: {reference_id} has already been credited")

        account = await FinanceService.get_or_create_prepaid_account(db, shop_id, lock=True)
        account.current_balance += amount
        if account.current_balance >= account.min_threshold_alert:
            account.is_low_balance_alerted = False
        account.last_topped_up_at = datetime.now(timezone.utc)

        ledger = ShopPrepaidLedger(
            shop_id=shop_id,
            account_id=account.id,
            transaction_type="CREDIT_TOPUP",
            amount=amount,
            balance_after=account.current_balance,
            reference_id=reference_id,
            notes=notes or f"Advance top-up verified by {admin_user}"
        )
        db.add(ledger)

        audit = AuditLog(
            user_id=admin_user,
            role="FINANCE",
            action="PREPAID_TOPUP",
            target_entity="shop_prepaid_accounts",
            target_id=str(shop_id),
            details=f"Credited ₹{amount} with reference {reference_id}"
        )
        db.add(audit)
        await db.flush()
        return account

    @staticmethod
    async def restore_prepaid_balance(
        db: AsyncSession,
        shop_id: int,
        amount: Decimal,
        reference_id: str,
        reason: str
    ) -> None:
        """
        Reversal entry in prepaid ledger when an eligible order is cancelled or rejected.
        Checks for duplicate reversals.
        """
        existing = await db.execute(
            select(ShopPrepaidLedger).where(
                and_(
                    ShopPrepaidLedger.shop_id == shop_id,
                    ShopPrepaidLedger.reference_id == reference_id,
                    ShopPrepaidLedger.transaction_type == "REVERSAL_REFUND"
                )
            )
        )
        if existing.scalar_one_or_none():
            # Already restored
            return

        account = await FinanceService.get_or_create_prepaid_account(db, shop_id, lock=True)
        account.current_balance += amount
        if account.current_balance >= account.min_threshold_alert:
            account.is_low_balance_alerted = False

        ledger = ShopPrepaidLedger(
            shop_id=shop_id,
            account_id=account.id,
            transaction_type="REVERSAL_REFUND",
            amount=amount,
            balance_after=account.current_balance,
            reference_id=reference_id,
            notes=f"Reversal: {reason}"
        )
        db.add(ledger)
        await db.flush()

    @staticmethod
    async def generate_daily_settlement(
        db: AsyncSession,
        shop_id: int,
        settlement_date: str
    ) -> Optional[ShopSettlement]:
        """Aggregate fulfilled daily orders for a shop into an auditable daily settlement statement"""
        shop = await db.get(Shop, shop_id)
        if not shop or shop.settlement_type != SettlementType.DAILY:
            return None

        # Check existing settlement for the date
        existing_res = await db.execute(
            select(ShopSettlement).where(
                and_(
                    ShopSettlement.shop_id == shop_id,
                    ShopSettlement.settlement_date == settlement_date
                )
            )
        )
        if existing_res.scalar_one_or_none():
            return None  # Already generated

        # Get vendor orders for this shop that are not already part of an existing settlement
        vo_res = await db.execute(
            select(VendorOrder).where(VendorOrder.shop_id == shop_id)
        )
        all_vendor_orders = vo_res.scalars().all()
        
        # Exclude vendor orders already in a SettlementItem
        settled_items_res = await db.execute(select(SettlementItem.vendor_order_id))
        settled_vo_ids = set(settled_items_res.scalars().all())
        unsettled_orders = [vo for vo in all_vendor_orders if vo.id not in settled_vo_ids]

        total_payable = sum([vo.shop_subtotal for vo in unsettled_orders], Decimal("0.00"))
        order_count = len(unsettled_orders)

        ref = f"SETTLE-{shop_id}-{settlement_date.replace('-', '')}"
        settlement = ShopSettlement(
            settlement_reference=ref,
            shop_id=shop_id,
            settlement_date=settlement_date,
            total_payable=total_payable,
            order_count=order_count,
            status=SettlementStatus.DRAFT
        )
        db.add(settlement)
        await db.flush()

        for vo in unsettled_orders:
            item = SettlementItem(
                settlement_id=settlement.id,
                vendor_order_id=vo.id,
                amount=vo.shop_subtotal
            )
            db.add(item)

        await db.flush()
        return settlement

    @staticmethod
    async def calculate_and_record_unit_economics(
        db: AsyncSession,
        master_order_id: int
    ) -> OrderUnitEconomics:
        """
        Calculates and records actual unit economics for every order:
        - Customer payment (Gross GMV)
        - Shop payable (Food cost)
        - Delivery fee collected (Flat Rs.25.00)
        - Gateway charges (2.36%: 2% Razorpay + 18% GST on fee)
        - Runner payout (Rs.18.00 per drop in JMD Megapolis campus)
        - Packaging cost (Rs.3.50 branded bag & tamper-evident seal)
        - Refunds deducted
        - Net platform contribution margin & margin %
        """
        stmt = (
            select(MasterOrder)
            .where(MasterOrder.id == master_order_id)
            .options(
                selectinload(MasterOrder.vendor_orders),
                selectinload(MasterOrder.refunds),
                selectinload(MasterOrder.unit_economics)
            )
        )
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Master order not found")

        gross_payment = Decimal(str(order.grand_total))
        food_subtotal = Decimal(str(order.items_subtotal))
        delivery_fee = Decimal(str(order.flat_delivery_fee))

        # Sum active shop payables (excluding cancelled/rejected vendor orders)
        shop_payable = sum(
            [Decimal(str(vo.shop_subtotal)) for vo in order.vendor_orders 
             if vo.status not in [VendorOrderStatus.CANCELLED, VendorOrderStatus.REJECTED]],
            Decimal("0.00")
        )

        # Gateway fee: 2% + 18% GST = 2.36% of customer payment
        gateway_fee = round(gross_payment * Decimal("0.0236"), 2)

        # Campus operational costs
        runner_payout = Decimal("18.00") if order.status != MasterOrderStatus.CANCELLED else Decimal("0.00")
        packaging_cost = Decimal("3.50") if order.status != MasterOrderStatus.CANCELLED else Decimal("0.00")

        # Refunds
        refund_amount = sum(
            [Decimal(str(r.amount)) for r in order.refunds if r.status in [RefundStatus.PROCESSED, RefundStatus.APPROVED]],
            Decimal("0.00")
        )

        # Contribution margin: Gross - Shop - Gateway - Runner - Packaging - Refund
        contribution_margin = gross_payment - shop_payable - gateway_fee - runner_payout - packaging_cost - refund_amount
        margin_pct = float((contribution_margin / gross_payment) * 100) if gross_payment > Decimal("0.00") else 0.0

        econ_stmt = select(OrderUnitEconomics).where(OrderUnitEconomics.master_order_id == master_order_id)
        econ_res = await db.execute(econ_stmt)
        econ = econ_res.scalar_one_or_none()

        if econ:
            econ.gross_customer_payment = gross_payment
            econ.food_subtotal = food_subtotal
            econ.delivery_fee_collected = delivery_fee
            econ.shop_payable = shop_payable
            econ.gateway_fee = gateway_fee
            econ.runner_payout = runner_payout
            econ.packaging_cost = packaging_cost
            econ.refund_deduction = refund_amount
            econ.contribution_margin = contribution_margin
            econ.contribution_margin_pct = round(margin_pct, 2)
        else:
            econ = OrderUnitEconomics(
                master_order_id=order.id,
                gross_customer_payment=gross_payment,
                food_subtotal=food_subtotal,
                delivery_fee_collected=delivery_fee,
                shop_payable=shop_payable,
                gateway_fee=gateway_fee,
                runner_payout=runner_payout,
                packaging_cost=packaging_cost,
                refund_deduction=refund_amount,
                contribution_margin=contribution_margin,
                contribution_margin_pct=round(margin_pct, 2),
                created_at=datetime.now(timezone.utc)
            )
            db.add(econ)

        await db.flush()
        return econ
