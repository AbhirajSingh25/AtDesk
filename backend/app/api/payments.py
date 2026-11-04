from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
import json
import logging

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.security import get_current_user_optional, require_roles
from backend.app.models.models import (
    Payment, PaymentEvent, MasterOrder, Refund, PaymentStatus, 
    MasterOrderStatus, RefundStatus, AuditLog, User, UserRole
)
from backend.app.services.payment_gateway import RazorpayGatewayService

logger = logging.getLogger("atdesk.payments_api")
router = APIRouter(prefix="/payments", tags=["Payment Gateway"])

@router.post("/razorpay/create-order")
async def create_razorpay_order_endpoint(
    payload: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a Razorpay server-side payment order.
    Never exposes the Razorpay key secret.
    Returns gateway_order_id, amount in paise, currency, and public key_id.
    """
    master_order_id = payload.get("master_order_id")
    amount = payload.get("amount")

    if master_order_id:
        order = await db.get(MasterOrder, int(master_order_id))
        if not order:
            raise HTTPException(status_code=404, detail="Master order not found")
        order_amount = Decimal(str(order.grand_total))
        receipt = order.order_number
    elif amount is not None:
        order_amount = Decimal(str(amount))
        receipt = f"ATD-PRE-{int(datetime.now(timezone.utc).timestamp())}"
    else:
        raise HTTPException(status_code=400, detail="master_order_id or amount is required")

    result = RazorpayGatewayService.create_order(
        amount_inr=order_amount,
        receipt=receipt,
        notes={"created_for_user": str(current_user.id) if current_user else "guest"}
    )

    # If master order exists, update or create pending Payment record with gateway_order_id
    if master_order_id:
        payment_stmt = select(Payment).where(Payment.master_order_id == int(master_order_id))
        pay_res = await db.execute(payment_stmt)
        payment = pay_res.scalars().first()
        if payment:
            payment.gateway_order_id = result["gateway_order_id"]
        else:
            payment = Payment(
                master_order_id=int(master_order_id),
                gateway_order_id=result["gateway_order_id"],
                amount=order_amount,
                payment_method="RAZORPAY_TEST",
                status=PaymentStatus.PENDING,
                created_at=datetime.now(timezone.utc)
            )
            db.add(payment)
        await db.commit()

    return result

@router.post("/razorpay/verify-payment")
async def verify_razorpay_payment_endpoint(
    payload: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Verifies Razorpay payment signature and updates payment/order status.
    Requires: razorpay_order_id, razorpay_payment_id, razorpay_signature.
    """
    razorpay_order_id = payload.get("razorpay_order_id")
    razorpay_payment_id = payload.get("razorpay_payment_id")
    razorpay_signature = payload.get("razorpay_signature")
    master_order_id = payload.get("master_order_id")

    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing required payment verification fields")

    # Cryptographically verify signature
    is_valid = RazorpayGatewayService.verify_payment_signature(
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Razorpay cryptographic payment signature")

    now = datetime.now(timezone.utc)

    # Locate payment record
    stmt = select(Payment).where(Payment.gateway_order_id == razorpay_order_id)
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment and master_order_id:
        payment = await db.get(Payment, int(master_order_id))

    if payment:
        payment.status = PaymentStatus.PAID
        payment.gateway_payment_id = razorpay_payment_id
        
        # Record payment event
        event = PaymentEvent(
            payment_id=payment.id,
            event_type="PAYMENT_CAPTURED",
            payload=json.dumps({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "verified_at": now.isoformat()
            }),
            created_at=now
        )
        db.add(event)

        # Update MasterOrder: Authoritative start of the 2-minute cancellation window is upon successful payment
        master = await db.get(MasterOrder, payment.master_order_id)
        if master:
            if master.status == MasterOrderStatus.CREATED:
                master.status = MasterOrderStatus.CONFIRMED
            master.payment_status = PaymentStatus.PAID
            master.cancellation_deadline = now + timedelta(seconds=settings.CANCELLATION_WINDOW_SECONDS)
            master.updated_at = now

        audit = AuditLog(
            user_id=str(current_user.id) if current_user else "GATEWAY",
            role="SYSTEM",
            action="PAYMENT_VERIFIED",
            target_entity="payments",
            target_id=str(payment.id),
            details=f"Payment verified successfully: {razorpay_payment_id} for order {razorpay_order_id}"
        )
        db.add(audit)
        await db.commit()

    return {
        "success": True,
        "message": "Payment signature verified successfully",
        "gateway_order_id": razorpay_order_id,
        "gateway_payment_id": razorpay_payment_id
    }

@router.post("/razorpay/refund")
async def initiate_gateway_refund_endpoint(
    payload: Dict[str, Any],
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.FINANCE])),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiates a full or partial refund via Razorpay test gateway.
    Requires ADMIN or FINANCE role.
    """
    master_order_id = payload.get("master_order_id")
    amount = payload.get("amount")
    reason = payload.get("reason", "Admin-initiated refund")

    if not master_order_id:
        raise HTTPException(status_code=400, detail="master_order_id is required")

    order = await db.get(MasterOrder, int(master_order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Find paid payment
    stmt = select(Payment).where(
        Payment.master_order_id == order.id,
        Payment.status == PaymentStatus.PAID
    )
    res = await db.execute(stmt)
    payment = res.scalars().first()

    if not payment:
        raise HTTPException(status_code=400, detail="No successful payment record found to refund")

    refund_amount = Decimal(str(amount)) if amount else Decimal(str(order.grand_total))
    if refund_amount > order.grand_total:
        raise HTTPException(status_code=400, detail="Refund amount exceeds total order amount")

    # Call gateway service
    refund_result = RazorpayGatewayService.initiate_refund(
        payment_id=payment.gateway_payment_id or f"pay_mock_{order.id}",
        amount_inr=refund_amount,
        notes={"reason": reason, "order_number": order.order_number}
    )

    now = datetime.now(timezone.utc)
    refund = Refund(
        master_order_id=order.id,
        amount=refund_amount,
        reason=reason,
        status=RefundStatus.PROCESSED if refund_result.get("status") == "PROCESSED" else RefundStatus.PENDING_APPROVAL,
        approved_by=current_user.full_name,
        gateway_refund_id=refund_result.get("gateway_refund_id"),
        created_at=now
    )
    db.add(refund)

    if refund_amount == order.grand_total:
        order.payment_status = PaymentStatus.REFUNDED
    else:
        order.payment_status = PaymentStatus.PARTIALLY_REFUNDED

    audit = AuditLog(
        user_id=str(current_user.id),
        role=current_user.role.value,
        action="GATEWAY_REFUND_INITIATED",
        target_entity="refunds",
        target_id=refund.gateway_refund_id,
        details=f"Refund of ₹{refund_amount} initiated via gateway for order #{order.order_number}. Reason: {reason}"
    )
    db.add(audit)
    await db.commit()

    return {
        "success": True,
        "message": f"Refund of ₹{refund_amount} processed via Razorpay test gateway",
        "gateway_refund_id": refund.gateway_refund_id,
        "status": refund.status.value
    }

@router.post("/razorpay/webhook")
@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Cryptographically verified Razorpay Webhook endpoint.
    Enforces:
    1. Mandatory X-Razorpay-Signature validation using HMAC SHA-256 and RAZORPAY_WEBHOOK_SECRET.
    2. Currency (INR) and payment amount verification against database records.
    3. Idempotent processing of order.paid and payment.captured events.
    4. Authoritative start of 2-minute cancellation grace window.
    """
    if not x_razorpay_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required X-Razorpay-Signature header"
        )

    body_bytes = await request.body()
    is_valid = RazorpayGatewayService.verify_webhook_signature(body_bytes, x_razorpay_signature)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Razorpay webhook cryptographic signature"
        )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    event_type = payload.get("event", "payment.captured")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    gateway_payment_id = payment_entity.get("id")
    gateway_order_id = payment_entity.get("order_id")

    # Verify Currency is INR
    currency = payment_entity.get("currency")
    if currency and currency.upper() != "INR":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported currency: {currency}")

    # Idempotency check: check if this event has already been recorded
    if gateway_payment_id:
        existing_event = await db.execute(
            select(PaymentEvent).where(
                PaymentEvent.event_type == event_type,
                PaymentEvent.payload.like(f"%{gateway_payment_id}%")
            )
        )
        if existing_event.scalar_one_or_none():
            return {"status": "ok", "message": "Duplicate event ignored (idempotent)"}

    # Find payment record
    stmt = select(Payment).where(Payment.gateway_order_id == gateway_order_id)
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if payment:
        # Validate amount if provided in payload (paise to INR)
        payload_amount_paise = payment_entity.get("amount")
        if payload_amount_paise is not None:
            payload_amount_inr = Decimal(str(payload_amount_paise / 100.0))
            if abs(payment.amount - payload_amount_inr) > Decimal("0.05"):
                logger.error(f"[Webhook Security] Amount mismatch: DB={payment.amount}, Payload={payload_amount_inr}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount mismatch detected")

        payment.status = PaymentStatus.PAID
        if gateway_payment_id:
            payment.gateway_payment_id = gateway_payment_id

        event = PaymentEvent(
            payment_id=payment.id,
            event_type=event_type,
            payload=json.dumps(payload),
            created_at=datetime.now(timezone.utc)
        )
        db.add(event)

        # Update MasterOrder: Authoritative start of 2-minute cancellation countdown upon webhook payment confirmation
        order = await db.get(MasterOrder, payment.master_order_id)
        if order:
            if order.status == MasterOrderStatus.CREATED:
                order.status = MasterOrderStatus.CONFIRMED
            order.payment_status = PaymentStatus.PAID
            order.cancellation_deadline = datetime.now(timezone.utc) + timedelta(seconds=settings.CANCELLATION_WINDOW_SECONDS)
            order.updated_at = datetime.now(timezone.utc)

        await db.commit()

    return {"status": "ok", "event": event_type, "message": "Webhook processed successfully"}
