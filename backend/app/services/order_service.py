from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.core.security import generate_master_otp
from backend.app.models.models import (
    User, MasterOrder, VendorOrder, OrderItem, MenuItem, Shop,
    Payment, Refund, DeliveryAssignment, DeliveryProof, DeliveryOtpRecord,
    MasterOrderStatus, VendorOrderStatus, PaymentStatus, RefundStatus,
    SettlementType, AuditLog, EtaSnapshot, DeliveryPartner, ScheduledOrder
)
from backend.app.services.eta_service import DynamicEtaService
from backend.app.services.finance_service import FinanceService

MAX_SCHEDULED_CAPACITY_PER_SLOT = 25

class OrderService:
    @staticmethod
    async def create_multi_shop_order(
        db: AsyncSession,
        user_id: int,
        cart_items: List[Dict[str, int]],
        tower: str,
        floor: int,
        desk_location: str,
        delivery_instructions: Optional[str] = None,
        scheduled_window: Optional[str] = None,
        payment_method: str = "UPI",
        idempotency_key: Optional[str] = None,
        transaction_mode: str = "TEST_SANDBOX"
    ) -> MasterOrder:
        # 1. Idempotency Check
        if idempotency_key:
            existing_payment = await db.execute(
                select(Payment).where(Payment.idempotency_key == idempotency_key)
            )
            pay = existing_payment.scalar_one_or_none()
            if pay:
                existing_order = await OrderService.get_order_by_id(db, pay.master_order_id)
                if existing_order:
                    return existing_order

        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart cannot be empty")

        # Scheduled order capacity check
        if scheduled_window:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sched_res = await db.execute(
                select(ScheduledOrder).where(
                    and_(
                        ScheduledOrder.scheduled_date == today_str,
                        ScheduledOrder.time_slot == scheduled_window
                    )
                )
            )
            existing_scheduled = sched_res.scalars().all()
            if len(existing_scheduled) >= MAX_SCHEDULED_CAPACITY_PER_SLOT:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Scheduled delivery window '{scheduled_window}' is at full building runner capacity ({MAX_SCHEDULED_CAPACITY_PER_SLOT}/{MAX_SCHEDULED_CAPACITY_PER_SLOT}). Please select another slot."
                )

        # 2. Fetch and validate all menu items from database
        item_ids = [item["menu_item_id"] for item in cart_items]
        stmt = select(MenuItem).where(MenuItem.id.in_(item_ids))
        res = await db.execute(stmt)
        menu_items_map = {mi.id: mi for mi in res.scalars().all()}

        # Group items by shop
        shop_items_map: Dict[int, List[Tuple[MenuItem, int]]] = {}
        for item in cart_items:
            mi = menu_items_map.get(item["menu_item_id"])
            if not mi:
                raise HTTPException(status_code=400, detail=f"Menu item {item['menu_item_id']} not found")
            if not mi.is_available:
                raise HTTPException(status_code=400, detail=f"Item '{mi.name}' is currently unavailable")
            
            qty = max(1, int(item["quantity"]))
            shop_items_map.setdefault(mi.shop_id, []).append((mi, qty))

        # 3. Check prepaid shop balances where applicable (with atomic lock)
        for shop_id, s_items in shop_items_map.items():
            shop = await db.get(Shop, shop_id)
            if not shop or not shop.is_open:
                raise HTTPException(status_code=400, detail=f"Shop '{shop.name if shop else shop_id}' is currently closed")
            
            shop_subtotal = sum(Decimal(str(mi.price)) * Decimal(qty) for mi, qty in s_items)
            if shop.settlement_type == SettlementType.PREPAID:
                account = await FinanceService.get_or_create_prepaid_account(db, shop_id, lock=True)
                if account.current_balance < shop_subtotal:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Shop '{shop.name}' is temporarily at order capacity (Prepaid balance requirement: requires ₹{shop_subtotal}, current balance is ₹{account.current_balance})."
                    )

        # 4. Compute Totals
        total_items_subtotal = Decimal("0.00")
        for s_items in shop_items_map.values():
            for mi, qty in s_items:
                total_items_subtotal += (Decimal(str(mi.price)) * Decimal(qty))

        flat_delivery_fee = Decimal(str(settings.FLAT_DELIVERY_FEE))
        grand_total = total_items_subtotal + flat_delivery_fee

        now = datetime.now(timezone.utc)
        cancellation_deadline = now + timedelta(seconds=settings.CANCELLATION_WINDOW_SECONDS)
        master_otp = generate_master_otp()
        order_number = f"ATD-{now.strftime('%Y%m%d%H%M%S')}-{user_id}"

        # 5. Create Master Order
        master_order = MasterOrder(
            order_number=order_number,
            user_id=user_id,
            status=MasterOrderStatus.CONFIRMED,
            tower=tower,
            floor=floor,
            desk_location=desk_location,
            delivery_instructions=delivery_instructions,
            items_subtotal=total_items_subtotal,
            flat_delivery_fee=flat_delivery_fee,
            discount_amount=Decimal("0.00"),
            grand_total=grand_total,
            payment_status=PaymentStatus.PAID,
            idempotency_key=idempotency_key,
            master_otp=master_otp,
            cancellation_deadline=cancellation_deadline,
            scheduled_window=scheduled_window,
            transaction_mode=transaction_mode,
            created_at=now,
            updated_at=now
        )
        db.add(master_order)
        await db.flush()

        # 6. Record ScheduledOrder reservation if window selected
        if scheduled_window:
            sched = ScheduledOrder(
                master_order_id=master_order.id,
                scheduled_date=now.strftime("%Y-%m-%d"),
                time_slot=scheduled_window,
                capacity_reserved=1,
                is_triggered=False,
                created_at=now
            )
            db.add(sched)

        # 7. Create Vendor Orders & Order Items
        shop_prep_times = []
        for shop_id, s_items in shop_items_map.items():
            shop = await db.get(Shop, shop_id)
            shop_subtotal = sum(Decimal(str(mi.price)) * Decimal(qty) for mi, qty in s_items)
            max_prep = max([mi.prep_time_mins for mi, _ in s_items] + [shop.prep_lead_time_mins if shop else 10])
            shop_prep_times.append(max_prep)

            vendor_order = VendorOrder(
                master_order_id=master_order.id,
                shop_id=shop_id,
                shop_subtotal=shop_subtotal,
                status=VendorOrderStatus.ACCEPTED,
                estimated_prep_time_mins=max_prep,
                created_at=now
            )
            db.add(vendor_order)
            await db.flush()

            for mi, qty in s_items:
                item_subtotal = Decimal(str(mi.price)) * Decimal(qty)
                order_item = OrderItem(
                    vendor_order_id=vendor_order.id,
                    menu_item_id=mi.id,
                    item_name=mi.name,
                    unit_price=Decimal(str(mi.price)),
                    quantity=qty,
                    subtotal=item_subtotal,
                    is_rejected=False
                )
                db.add(order_item)

            # Deduct prepaid ledger if PREPAID model
            if shop and shop.settlement_type == SettlementType.PREPAID:
                success = await FinanceService.debit_prepaid_for_order(db, shop_id, shop_subtotal, vendor_order.id)
                if not success:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Shop '{shop.name}' prepaid balance became insufficient during checkout."
                    )

        # 8. Record Payment
        payment = Payment(
            master_order_id=master_order.id,
            gateway_order_id=f"order_mock_{master_order.id}",
            gateway_payment_id=f"pay_mock_{master_order.id}",
            payment_method=payment_method,
            amount=grand_total,
            status=PaymentStatus.PAID,
            idempotency_key=idempotency_key,
            created_at=now
        )
        db.add(payment)

        # 9. Compute Dynamic ETA
        eta_info = DynamicEtaService.calculate_eta(
            shop_prep_times=shop_prep_times,
            num_shops=len(shop_items_map),
            tower=tower,
            floor=floor
        )
        eta_snapshot = EtaSnapshot(
            master_order_id=master_order.id,
            calculated_min_mins=eta_info["min_eta_mins"],
            calculated_max_mins=eta_info["max_eta_mins"],
            estimated_delivery_time=eta_info["estimated_delivery_time"],
            factors_breakdown=str(eta_info["factors"]),
            created_at=now
        )
        db.add(eta_snapshot)

        # 10. Assign Delivery Partner (Fleet runner)
        runner_res = await db.execute(select(DeliveryPartner).where(DeliveryPartner.is_active == True))
        runner = runner_res.scalars().first()
        if runner:
            assignment = DeliveryAssignment(
                master_order_id=master_order.id,
                delivery_partner_id=runner.id,
                status="ASSIGNED",
                assigned_at=now
            )
            db.add(assignment)

        # 11. Audit Log
        audit = AuditLog(
            user_id=str(user_id),
            role="EMPLOYEE",
            action="ORDER_CREATED",
            target_entity="master_orders",
            target_id=str(master_order.id),
            details=f"Order #{master_order.order_number} created with {len(shop_items_map)} shops. Total: ₹{grand_total}"
        )
        db.add(audit)

        # Record initial unit economics
        await FinanceService.calculate_and_record_unit_economics(db, master_order.id)

        await db.commit()
        return await OrderService.get_order_by_id(db, master_order.id)

    @staticmethod
    async def get_order_by_id(db: AsyncSession, order_id: int, lock: bool = False) -> Optional[MasterOrder]:
        stmt = (
            select(MasterOrder)
            .where(MasterOrder.id == order_id)
            .options(
                selectinload(MasterOrder.vendor_orders).selectinload(VendorOrder.order_items),
                selectinload(MasterOrder.vendor_orders).selectinload(VendorOrder.shop),
                selectinload(MasterOrder.user).selectinload(User.employee_profile),
                selectinload(MasterOrder.eta_snapshots),
                selectinload(MasterOrder.refunds),
                selectinload(MasterOrder.payments),
                selectinload(MasterOrder.assignment),
                selectinload(MasterOrder.proofs),
                selectinload(MasterOrder.unit_economics)
            )
        )
        if lock:
            bind = db.get_bind()
            if bind and bind.dialect.name != "sqlite":
                stmt = stmt.with_for_update()

        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def cancel_order_within_two_minutes(
        db: AsyncSession,
        order_id: int,
        user_id: int,
        reason: str = "Customer requested cancellation within 2 minutes"
    ) -> Dict[str, Any]:
        """
        Enforces server-authoritative 2-minute cancellation rule:
        - If now <= cancellation_deadline: full refund processed immediately to original payment method.
        - If now > cancellation_deadline: raises 400.
        - Uses row-level lock and idempotency to prevent duplicate refunds / concurrent cancellation.
        """
        order = await OrderService.get_order_by_id(db, order_id, lock=True)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to cancel this order")

        if order.status == MasterOrderStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Order is already cancelled")

        if order.status == MasterOrderStatus.DELIVERED:
            raise HTTPException(status_code=400, detail="Delivered orders cannot be cancelled")

        now = datetime.now(timezone.utc)
        deadline = order.cancellation_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        if now > deadline:
            raise HTTPException(
                status_code=400, 
                detail="Cancellation window of 2 minutes has expired. Delivery coordination is already in progress."
            )

        # Check existing refund to prevent duplicate refund records
        existing_refund = await db.execute(
            select(Refund).where(
                and_(
                    Refund.master_order_id == order.id,
                    Refund.status.in_([RefundStatus.PROCESSED, RefundStatus.APPROVED])
                )
            )
        )
        if existing_refund.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Refund has already been processed for this order")

        # Process full cancellation
        order.status = MasterOrderStatus.CANCELLED
        order.payment_status = PaymentStatus.REFUNDED
        order.updated_at = now

        for vo in order.vendor_orders:
            vo.status = VendorOrderStatus.CANCELLED
            # Restore prepaid balance if shop was PREPAID
            shop = await db.get(Shop, vo.shop_id)
            if shop and shop.settlement_type == SettlementType.PREPAID:
                await FinanceService.restore_prepaid_balance(
                    db, vo.shop_id, vo.shop_subtotal, f"CANCEL-{order.id}", "2-minute cancellation balance restoration"
                )

        # Create refund entry
        refund_amount = order.grand_total
        refund = Refund(
            master_order_id=order.id,
            amount=refund_amount,
            reason=reason,
            status=RefundStatus.PROCESSED,
            approved_by="System (2-Min Policy)",
            gateway_refund_id=f"rfnd_{order.id}_{int(now.timestamp())}",
            created_at=now
        )
        db.add(refund)

        audit = AuditLog(
            user_id=str(user_id),
            role="EMPLOYEE",
            action="ORDER_CANCELLED_2MIN",
            target_entity="master_orders",
            target_id=str(order.id),
            details=f"Master order {order.order_number} cancelled within 2 minutes. Full refund: ₹{refund_amount}"
        )
        db.add(audit)

        # Recalculate unit economics after cancellation & full refund
        await FinanceService.calculate_and_record_unit_economics(db, order.id)

        await db.commit()
        return {
            "success": True,
            "message": "Order cancelled successfully within 2 minutes. Full refund has been initiated to your original payment method.",
            "refund_amount": float(refund_amount),
            "refund_id": refund.gateway_refund_id
        }

    @staticmethod
    async def reject_single_item(
        db: AsyncSession,
        order_item_id: int,
        admin_user: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Partial rejection workflow:
        If one shop is out of stock of an item, refund only that item and continue fulfilling the rest!
        Prevents duplicate refunds.
        """
        stmt = (
            select(OrderItem)
            .where(OrderItem.id == order_item_id)
            .options(
                selectinload(OrderItem.vendor_order).selectinload(VendorOrder.master_order),
                selectinload(OrderItem.vendor_order).selectinload(VendorOrder.shop),
                selectinload(OrderItem.vendor_order).selectinload(VendorOrder.order_items)
            )
        )
        res = await db.execute(stmt)
        item = res.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Order item not found")

        if item.is_rejected:
            raise HTTPException(status_code=400, detail="Item already marked as rejected")

        item.is_rejected = True
        item.rejection_reason = reason
        item_refund_amount = item.subtotal

        vendor_order = item.vendor_order
        master_order = vendor_order.master_order
        shop = vendor_order.shop

        # Reduce vendor order subtotal
        vendor_order.shop_subtotal -= item_refund_amount
        # Reduce master order totals
        master_order.items_subtotal -= item_refund_amount
        master_order.grand_total -= item_refund_amount
        master_order.status = MasterOrderStatus.PARTIALLY_REFUNDED

        # If all items in this shop are rejected, mark vendor order REJECTED
        all_rejected = all(oi.is_rejected for oi in vendor_order.order_items)
        if all_rejected:
            vendor_order.status = VendorOrderStatus.REJECTED

        now = datetime.now(timezone.utc)

        # Restore prepaid balance if PREPAID
        if shop.settlement_type == SettlementType.PREPAID:
            await FinanceService.restore_prepaid_balance(
                db, shop.id, item_refund_amount, f"REJECT-ITEM-{item.id}", f"Partial rejection: {reason}"
            )

        # Create refund
        refund = Refund(
            master_order_id=master_order.id,
            vendor_order_id=vendor_order.id,
            amount=item_refund_amount,
            reason=f"Partial item rejection: {item.item_name} ({reason})",
            status=RefundStatus.PROCESSED,
            approved_by=admin_user,
            gateway_refund_id=f"rfnd_part_{item.id}_{int(now.timestamp())}",
            created_at=now
        )
        db.add(refund)

        audit = AuditLog(
            user_id=admin_user,
            role="ADMIN",
            action="ITEM_PARTIAL_REJECTION",
            target_entity="order_items",
            target_id=str(item.id),
            details=f"Item {item.item_name} rejected in Order #{master_order.order_number}. Refunded ₹{item_refund_amount}"
        )
        db.add(audit)

        # Recalculate unit economics after item rejection
        await FinanceService.calculate_and_record_unit_economics(db, master_order.id)

        await db.commit()
        return {
            "success": True,
            "refunded_amount": float(item_refund_amount),
            "refund_id": refund.gateway_refund_id,
            "master_order_id": master_order.id
        }

    @staticmethod
    async def verify_delivery_completion(
        db: AsyncSession,
        master_order_id: int,
        partner_id: int,
        entered_otp: str,
        photo_url_or_data: str,
        latitude: float = 28.4162,
        longitude: float = 77.0425
    ) -> Dict[str, Any]:
        """
        Enforces PART 7 & PART 8 delivery verification:
        1. Validates that partner_id matches the assigned delivery runner.
        2. Validates order is not already DELIVERED or CANCELLED.
        3. Validates mandatory desk photograph (in-app capture).
        4. Validates mandatory employee 6-digit master OTP against server-stored value.
        5. Validates all required packages from shops were picked up.
        """
        order = await OrderService.get_order_by_id(db, master_order_id, lock=True)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status == MasterOrderStatus.DELIVERED:
            raise HTTPException(status_code=400, detail="Order is already completed and delivered")
        if order.status == MasterOrderStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Cannot complete a cancelled order")

        # 1. Partner assignment verification
        assign_res = await db.execute(
            select(DeliveryAssignment).where(DeliveryAssignment.master_order_id == order.id)
        )
        assignment = assign_res.scalar_one_or_none()
        if not assignment:
            raise HTTPException(status_code=400, detail="No delivery assignment found for this order")
        if assignment.delivery_partner_id != partner_id:
            raise HTTPException(status_code=403, detail="Unauthorized: This order is assigned to another delivery runner")

        # 2. Package pickup reconciliation: All active vendor orders must be picked up
        unpicked_shops = [
            vo.shop.name if vo.shop else f"Shop {vo.shop_id}"
            for vo in order.vendor_orders 
            if vo.status not in [VendorOrderStatus.PICKED_UP, VendorOrderStatus.CANCELLED, VendorOrderStatus.REJECTED]
        ]
        if unpicked_shops:
            raise HTTPException(
                status_code=400, 
                detail=f"Incomplete pickups: Please confirm pickup from {', '.join(unpicked_shops)} before attempting desk delivery completion."
            )

        # 3. Mandatory Photo Check
        if not photo_url_or_data or len(photo_url_or_data.strip()) < 20:
            raise HTTPException(status_code=400, detail="Mandatory desk delivery photograph is missing")

        # 4. Mandatory OTP Verification
        otp_clean = entered_otp.strip()
        if otp_clean != order.master_otp:
            # Check past failed attempts
            otp_fail_count_res = await db.execute(
                select(DeliveryOtpRecord).where(
                    and_(
                        DeliveryOtpRecord.master_order_id == order.id,
                        DeliveryOtpRecord.is_verified == False
                    )
                )
            )
            failed_attempts = len(otp_fail_count_res.scalars().all()) + 1

            otp_record = DeliveryOtpRecord(
                master_order_id=order.id,
                entered_otp=otp_clean,
                is_verified=False,
                attempts_count=failed_attempts,
                verified_at=datetime.now(timezone.utc)
            )
            db.add(otp_record)
            await db.commit()
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid OTP (Attempt {failed_attempts}). Please ask the employee at desk {order.desk_location} for the 6-digit delivery OTP shown in their AtDesk app."
            )

        now = datetime.now(timezone.utc)

        # 5. Save Delivery Proof
        proof = DeliveryProof(
            master_order_id=order.id,
            delivery_partner_id=partner_id,
            photo_url=photo_url_or_data,
            latitude=latitude,
            longitude=longitude,
            captured_at=now
        )
        db.add(proof)

        # 6. Save Successful OTP Record
        otp_record = DeliveryOtpRecord(
            master_order_id=order.id,
            entered_otp=otp_clean,
            is_verified=True,
            attempts_count=1,
            verified_at=now
        )
        db.add(otp_record)

        # 7. Complete Order and Delivery Assignment
        order.status = MasterOrderStatus.DELIVERED
        order.updated_at = now

        assignment.status = "DELIVERED"
        assignment.completed_at = now

        audit = AuditLog(
            user_id=str(partner_id),
            role="DELIVERY_PARTNER",
            action="DELIVERY_COMPLETED",
            target_entity="master_orders",
            target_id=str(order.id),
            details=f"Order #{order.order_number} verified with photo proof & OTP at Tower {order.tower}, Floor {order.floor}, Desk {order.desk_location}"
        )
        db.add(audit)

        # Recalculate unit economics after cancellation & full refund
        await FinanceService.calculate_and_record_unit_economics(db, order.id)

        await db.commit()
        return {
            "success": True,
            "message": f"Delivery completed successfully for Desk {order.desk_location}!",
            "order_number": order.order_number,
            "delivered_at": now.isoformat()
        }
