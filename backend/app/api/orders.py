from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.security import get_current_user_optional
from backend.app.models.models import MasterOrder, MenuItem, Shop, MasterOrderStatus, User, UserRole
from backend.app.schemas.schemas import (
    MasterOrderCreate, MasterOrderOut, VendorOrderOut, 
    OrderItemOut, CancelOrderRequest, CancelOrderResponse, DynamicEtaOut
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
        grand_total=float(order.grand_total),
        payment_status=order.payment_status,
        master_otp=order.master_otp,
        cancellation_deadline=order.cancellation_deadline,
        can_cancel=can_cancel,
        cancellation_seconds_remaining=seconds_remaining,
        scheduled_window=order.scheduled_window,
        created_at=order.created_at,
        vendor_orders=vendor_orders_out,
        estimated_arrival_window=eta_text
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
    target_user_id = current_user.id if current_user else (user_id or 1)
    
    cart_items = [{"menu_item_id": item.menu_item_id, "quantity": item.quantity} for item in payload.items]
    order = await OrderService.create_multi_shop_order(
        db=db,
        user_id=target_user_id,
        cart_items=cart_items,
        tower=payload.tower,
        floor=payload.floor,
        desk_location=payload.desk_location,
        delivery_instructions=payload.delivery_instructions,
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

    # Access control: if user is authenticated as an employee, verify they own the order
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
    """Get all past and active orders for an employee"""
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
