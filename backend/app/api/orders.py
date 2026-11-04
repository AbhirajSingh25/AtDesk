from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.security import get_current_user_optional, get_current_user
from backend.app.models.models import (
    MasterOrder, MenuItem, Shop, MasterOrderStatus, User, UserRole,
    Coupon, DiscountType, PromoBanner
)
from backend.app.schemas.schemas import (
    MasterOrderCreate, MasterOrderOut, VendorOrderOut, 
    OrderItemOut, CancelOrderRequest, CancelOrderResponse, DynamicEtaOut,
    CouponOut, CouponApplyRequest, CouponApplyResponse, PromoBannerOut
)
from backend.app.services.order_service import OrderService
from backend.app.services.eta_service import DynamicEtaService

router = APIRouter(prefix="/orders", tags=["Orders"])

def serialize_master_order(order: MasterOrder, viewing_user: Optional[User] = None) -> MasterOrderOut:
    now = datetime.now(timezone.utc)
    deadline = order.cancellation_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    seconds_remaining = max(0, int((deadline - now).total_seconds()))
    can_cancel = (order.status not in [MasterOrderStatus.CANCELLED, MasterOrderStatus.DELIVERED]) and (seconds_remaining > 0)

    vendor_orders_out = []
    for vo in order.vendor_orders:
        items_out = [
            OrderItemOut(
                id=oi.id,
                menu_item_id=oi.menu_item_id,
                item_name=oi.item_name,
                unit_price=float(oi.unit_price),
                quantity=oi.quantity,
                subtotal=float(oi.subtotal),
                is_rejected=oi.is_rejected,
                rejection_reason=oi.rejection_reason
            ) for oi in vo.order_items
        ]
        vendor_orders_out.append(
            VendorOrderOut(
                id=vo.id,
                shop_id=vo.shop_id,
                shop_name=vo.shop.name if vo.shop else None,
                shop_subtotal=float(vo.shop_subtotal),
                status=vo.status,
                estimated_prep_time_mins=vo.estimated_prep_time_mins,
                pickup_confirmed_at=vo.pickup_confirmed_at,
                order_items=items_out
            )
        )

    eta_text = "25 - 35 mins"
    if order.eta_snapshots:
        latest = order.eta_snapshots[-1]
        eta_text = f"{latest.calculated_min_mins} - {latest.calculated_max_mins} mins"

    # Privacy protection: If delivery partner views a delivered or cancelled order, mask customer contact
    user_name = order.user.full_name if order.user else None
    user_phone = order.user.phone if order.user else None

    if viewing_user and viewing_user.role == UserRole.DELIVERY_PARTNER:
        if order.status in [MasterOrderStatus.DELIVERED, MasterOrderStatus.CANCELLED]:
            user_phone = "••••••" + str(user_phone)[-4:] if user_phone else None

    # Secure OTP exposure:
    # Customer who placed the order sees their 6-digit OTP.
    # Runners must NOT see the OTP in advance — they ask the customer at desk drop.
    # Admins see masked OTP unless supervisor override is triggered.
    if viewing_user and viewing_user.role == UserRole.DELIVERY_PARTNER:
        effective_otp = "••••••"
    elif viewing_user and viewing_user.id == order.user_id:
        effective_otp = order.master_otp
    elif viewing_user and viewing_user.role in [UserRole.ADMIN, UserRole.FINANCE]:
        effective_otp = "••••••"
    else:
        effective_otp = order.master_otp

    # Runner assignment info
    runner_name = None
    runner_phone = None
    if order.assignment and order.assignment.partner and order.assignment.partner.user:
        runner_name = order.assignment.partner.user.full_name
        runner_phone = order.assignment.partner.user.phone

    return MasterOrderOut(
        id=order.id,
        order_number=order.order_number,
        user_id=order.user_id,
        user_name=user_name,
        user_phone=user_phone,
        status=order.status,
        tower=order.tower,
        floor=order.floor,
        desk_location=order.desk_location,
        delivery_instructions=order.delivery_instructions,
        items_subtotal=float(order.items_subtotal),
        flat_delivery_fee=float(order.flat_delivery_fee),
        discount_amount=float(order.discount_amount),
        coupon_code=order.coupon_code,
        grand_total=float(order.grand_total),
        payment_status=order.payment_status,
        master_otp=effective_otp,
        cancellation_deadline=order.cancellation_deadline,
        can_cancel=can_cancel,
        cancellation_seconds_remaining=seconds_remaining,
        scheduled_window=order.scheduled_window,
        created_at=order.created_at,
        vendor_orders=vendor_orders_out,
        estimated_arrival_window=eta_text,
        runner_name=runner_name,
        runner_phone=runner_phone
    )

@router.get("/banners", response_model=List[PromoBannerOut])
async def get_active_banners(db: AsyncSession = Depends(get_db)):
    """Fetch promotional hero discovery banners for employee app homepage"""
    stmt = (
        select(PromoBanner)
        .where(PromoBanner.is_active == True)
        .order_by(PromoBanner.sort_order, PromoBanner.id)
    )
    res = await db.execute(stmt)
    banners = res.scalars().all()
    if not banners:
        # Fallback default real banners for JMD Megapolis pilot
        return [
            PromoBannerOut(
                id=1,
                title="Office Lunch Made Easy",
                subtitle="Chai, Subs, Meals & Chargers to your desk in 25 mins",
                badge_text="FLAT ₹25 DELIVERY",
                coupon_code="WELCOME50",
                image_url="https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=800&auto=format&fit=crop&q=80",
                bg_gradient="from-[#103D32] to-[#1B4332]",
                action_link="/",
                sort_order=1,
                is_active=True
            ),
            PromoBannerOut(
                id=2,
                title="Chai & Bun Maska Break",
                subtitle="Order freshly brewed ginger cardamom chai from Chaayos",
                badge_text="₹10 OFF CHAI",
                coupon_code="CHAI10",
                image_url="https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=800&auto=format&fit=crop&q=80",
                bg_gradient="from-[#8D4B32] to-[#602D1A]",
                action_link="/shops/chaayos-jmd",
                sort_order=2,
                is_active=True
            ),
            PromoBannerOut(
                id=3,
                title="Specialty Coffee by Blue Tokai",
                subtitle="Cold Brews, Flat Whites & Croissants directly to your desk",
                badge_text="BESTSELLER",
                coupon_code=None,
                image_url="https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=800&auto=format&fit=crop&q=80",
                bg_gradient="from-[#1C2D42] to-[#0E1E30]",
                action_link="/shops/blue-tokai-jmd",
                sort_order=3,
                is_active=True
            )
        ]
    return banners

@router.get("/coupons/available", response_model=List[CouponOut])
async def get_available_coupons(db: AsyncSession = Depends(get_db)):
    """List valid active promotional coupons"""
    stmt = (
        select(Coupon)
        .where(Coupon.is_active == True)
        .order_by(Coupon.id)
    )
    res = await db.execute(stmt)
    coupons = res.scalars().all()
    if not coupons:
        # Return standard pilot promotional coupons if none seeded
        return [
            CouponOut(
                id=1,
                code="WELCOME50",
                description="Flat ₹50 off on orders above ₹199 for new employees",
                discount_type=DiscountType.FLAT,
                discount_value=50.0,
                min_order_amount=199.0,
                max_discount=50.0,
                is_active=True,
                usage_count=42,
                valid_until=None
            ),
            CouponOut(
                id=2,
                code="CHAI10",
                description="Flat ₹10 off on morning and afternoon Chai orders",
                discount_type=DiscountType.FLAT,
                discount_value=10.0,
                min_order_amount=79.0,
                max_discount=10.0,
                is_active=True,
                usage_count=118,
                valid_until=None
            ),
            CouponOut(
                id=3,
                code="MEGAPOLIS20",
                description="20% off up to ₹60 on team snack orders above ₹250",
                discount_type=DiscountType.PERCENTAGE,
                discount_value=20.0,
                min_order_amount=250.0,
                max_discount=60.0,
                is_active=True,
                usage_count=65,
                valid_until=None
            )
        ]
    return coupons

@router.post("/coupons/apply", response_model=CouponApplyResponse)
async def apply_coupon(payload: CouponApplyRequest, db: AsyncSession = Depends(get_db)):
    """Validate and compute coupon discount for checkout"""
    code_clean = payload.coupon_code.strip().upper()
    stmt = select(Coupon).where(Coupon.code == code_clean, Coupon.is_active == True)
    res = await db.execute(stmt)
    coupon = res.scalar_one_or_none()

    subtotal = Decimal(str(payload.items_subtotal))
    flat_fee = Decimal(str(settings.FLAT_DELIVERY_FEE))

    # Built-in fallback check if coupons haven't been seeded into table yet
    if not coupon:
        if code_clean == "WELCOME50" and subtotal >= 199:
            discount = Decimal("50.00")
            new_total = (subtotal - discount) + flat_fee
            return CouponApplyResponse(
                is_valid=True,
                coupon_code="WELCOME50",
                discount_amount=float(discount),
                message="WELCOME50 applied: Flat ₹50 off!",
                new_grand_total=float(new_total)
            )
        elif code_clean == "CHAI10" and subtotal >= 79:
            discount = Decimal("10.00")
            new_total = (subtotal - discount) + flat_fee
            return CouponApplyResponse(
                is_valid=True,
                coupon_code="CHAI10",
                discount_amount=float(discount),
                message="CHAI10 applied: Flat ₹10 off!",
                new_grand_total=float(new_total)
            )
        elif code_clean == "MEGAPOLIS20" and subtotal >= 250:
            discount = min(Decimal("60.00"), (subtotal * Decimal("20")) / Decimal("100"))
            new_total = (subtotal - discount) + flat_fee
            return CouponApplyResponse(
                is_valid=True,
                coupon_code="MEGAPOLIS20",
                discount_amount=float(discount),
                message="MEGAPOLIS20 applied: 20% off!",
                new_grand_total=float(new_total)
            )
        raise HTTPException(status_code=400, detail="Invalid coupon code or minimum order condition not met")

    if subtotal < coupon.min_order_amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Coupon '{coupon.code}' requires a minimum items subtotal of ₹{coupon.min_order_amount}."
        )

    if coupon.discount_type == DiscountType.FLAT:
        discount_amount = min(Decimal(str(coupon.discount_value)), subtotal)
    else:
        calc = (subtotal * Decimal(str(coupon.discount_value))) / Decimal("100")
        if coupon.max_discount:
            discount_amount = min(calc, Decimal(str(coupon.max_discount)))
        else:
            discount_amount = calc

    new_total = (subtotal - discount_amount) + flat_fee
    return CouponApplyResponse(
        is_valid=True,
        coupon_code=coupon.code,
        discount_amount=float(discount_amount),
        message=f"Coupon '{coupon.code}' applied successfully!",
        new_grand_total=float(new_total)
    )

@router.post("/calculate-preview", response_model=DynamicEtaOut)
async def calculate_cart_preview(payload: MasterOrderCreate, db: AsyncSession = Depends(get_db)):
    """Calculate pre-checkout subtotal, dynamic ETA, and preparation breakdown"""
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    item_ids = [item.menu_item_id for item in payload.items]
    res = await db.execute(select(MenuItem).where(MenuItem.id.in_(item_ids)))
    items = res.scalars().all()
    item_map = {i.id: i for i in items}

    shop_prep_map = {}
    for item in payload.items:
        mi = item_map.get(item.menu_item_id)
        if mi:
            shop_prep_map.setdefault(mi.shop_id, []).append(mi.prep_time_mins)

    shop_max_preps = [max(times) for times in shop_prep_map.values()] if shop_prep_map else [10]

    eta_result = DynamicEtaService.calculate_eta(
        shop_prep_times=shop_max_preps,
        num_shops=len(shop_prep_map),
        tower=payload.tower,
        floor=payload.floor
    )

    return DynamicEtaOut(
        min_eta_mins=eta_result["min_eta_mins"],
        max_eta_mins=eta_result["max_eta_mins"],
        estimated_arrival_window=eta_result["estimated_arrival_window"],
        preparation_overlap_mins=eta_result["preparation_overlap_mins"],
        travel_between_shops_mins=eta_result["travel_between_shops_mins"],
        runner_building_access_mins=eta_result["runner_building_access_mins"],
        floor_and_desk_handover_mins=eta_result["floor_and_desk_handover_mins"],
        total_estimated_mins=eta_result["total_estimated_mins"],
        factors=eta_result["factors"]
    )

@router.post("", response_model=MasterOrderOut)
async def create_order(
    payload: MasterOrderCreate,
    user_id: Optional[int] = Query(None, description="Employee user ID (optional if Bearer provided)"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Create multi-shop master order with single flat delivery fee and 2-min cancellation rule"""
    if current_user:
        target_user_id = current_user.id
    elif user_id:
        u = await db.get(User, user_id)
        if not u:
            raise HTTPException(status_code=401, detail="User not found")
        target_user_id = u.id
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to place an order. Please sign in via phone OTP."
        )
    
    cart_items = [{"menu_item_id": item.menu_item_id, "quantity": item.quantity} for item in payload.items]
    order = await OrderService.create_multi_shop_order(
        db=db,
        user_id=target_user_id,
        cart_items=cart_items,
        tower=payload.tower,
        floor=payload.floor,
        desk_location=payload.desk_location,
        delivery_instructions=payload.delivery_instructions,
        coupon_code=payload.coupon_code,
        scheduled_window=payload.scheduled_window,
        payment_method=payload.payment_method,
        idempotency_key=payload.idempotency_key
    )
    return serialize_master_order(order, viewing_user=current_user)

@router.get("/{order_id}", response_model=MasterOrderOut)
async def get_order(
    order_id: int, 
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed master order with live status and cancellation countdown"""
    order = await OrderService.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Scoped ownership check: if employee, cannot view orders of another employee
    if current_user and current_user.role == UserRole.EMPLOYEE and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You can only view your own orders")

    return serialize_master_order(order, viewing_user=current_user)

@router.post("/{order_id}/cancel", response_model=CancelOrderResponse)
async def cancel_order(
    order_id: int, 
    payload: CancelOrderRequest,
    user_id: Optional[int] = Query(None, description="Employee user ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Cancel order within strict 2-minute server-authoritative window with full refund"""
    target_user_id = current_user.id if current_user else (user_id or 1)
    return await OrderService.cancel_order_within_two_minutes(
        db=db,
        order_id=order_id,
        user_id=target_user_id,
        reason=payload.reason or "Customer cancellation within 2 minutes"
    )

@router.get("/user/{user_id}", response_model=List[MasterOrderOut])
async def get_user_orders(
    user_id: int, 
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Get all past and active orders for an employee with scoped ownership check"""
    if current_user and current_user.role == UserRole.EMPLOYEE and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot view order history of other employees")

    stmt = (
        select(MasterOrder)
        .where(MasterOrder.user_id == user_id)
        .order_by(MasterOrder.id.desc())
    )
    res = await db.execute(stmt)
    orders = res.scalars().all()
    detailed_orders = []
    for o in orders:
        full_o = await OrderService.get_order_by_id(db, o.id)
        if full_o:
            detailed_orders.append(serialize_master_order(full_o, viewing_user=current_user))
    return detailed_orders
