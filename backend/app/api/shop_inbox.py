from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, get_current_user_optional, require_roles
from backend.app.models.models import (
    Shop, VendorOrder, OrderItem, MenuItem, MasterOrder, User, UserRole,
    VendorOrderStatus, MasterOrderStatus, AuditLog, Refund, RefundStatus,
    SettlementType
)
from backend.app.schemas.schemas import (
    VendorOrderOut, OrderItemOut, MenuItemOut, ShopOrderActionRequest, ItemAvailabilityToggle
)
from backend.app.services.order_service import OrderService
from backend.app.services.eta_service import DynamicEtaService
from backend.app.services.finance_service import FinanceService

router = APIRouter(prefix="/shop-inbox", tags=["Shop Order Inbox (Vendor Staff)"])

def serialize_vendor_order(vo: VendorOrder) -> Dict[str, Any]:
    items_out = []
    for oi in vo.order_items:
        items_out.append({
            "id": oi.id,
            "menu_item_id": oi.menu_item_id,
            "item_name": oi.item_name,
            "unit_price": float(oi.unit_price),
            "quantity": oi.quantity,
            "subtotal": float(oi.subtotal),
            "is_rejected": oi.is_rejected,
            "rejection_reason": oi.rejection_reason
        })

    master = vo.master_order
    return {
        "id": vo.id,
        "master_order_id": vo.master_order_id,
        "order_number": master.order_number if master else f"ORD-{vo.master_order_id}",
        "shop_id": vo.shop_id,
        "shop_name": vo.shop.name if vo.shop else None,
        "shop_subtotal": float(vo.shop_subtotal),
        "status": vo.status.value,
        "estimated_prep_time_mins": vo.estimated_prep_time_mins,
        "pickup_confirmed_at": vo.pickup_confirmed_at.isoformat() if vo.pickup_confirmed_at else None,
        "created_at": vo.created_at.isoformat(),
        "tower": master.tower if master else "Tower B",
        "floor": master.floor if master else 4,
        "desk_location": master.desk_location if master else "Desk Drop",
        "customer_instructions": master.delivery_instructions if master else None,
        "order_items": items_out
    }

async def resolve_shop_id(
    shop_id: Optional[int],
    current_user: Optional[User],
    db: AsyncSession
) -> int:
    """Resolve shop_id from user's shop_staff_profile or explicitly passed shop_id (admin/demo)"""
    if current_user:
        if current_user.role == UserRole.SHOP_STAFF and current_user.shop_staff_profile:
            return current_user.shop_staff_profile.shop_id
        if current_user.role in [UserRole.ADMIN, UserRole.FINANCE] and shop_id:
            return shop_id
    if shop_id:
        return shop_id
    # Default to first available shop for convenience if no ID given
    first_shop = await db.execute(select(Shop.id).order_by(Shop.id))
    sid = first_shop.scalar_one_or_none()
    if sid:
        return sid
    raise HTTPException(status_code=400, detail="Shop ID required")

@router.get("/orders")
async def get_shop_orders(
    shop_id: Optional[int] = Query(None, description="Shop ID"),
    status_filter: Optional[str] = Query(None, description="Filter: PENDING | ACCEPTED | PREPARING | READY_FOR_PICKUP | PICKED_UP | ALL"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """List orders for shop staff inbox with real-time status grouping"""
    target_shop_id = await resolve_shop_id(shop_id, current_user, db)
    shop = await db.get(Shop, target_shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    stmt = (
        select(VendorOrder)
        .options(
            selectinload(VendorOrder.order_items),
            selectinload(VendorOrder.master_order),
            selectinload(VendorOrder.shop)
        )
        .where(VendorOrder.shop_id == target_shop_id)
        .order_by(VendorOrder.id.desc())
    )

    if status_filter and status_filter != "ALL":
        try:
            enum_status = VendorOrderStatus(status_filter)
            stmt = stmt.where(VendorOrder.status == enum_status)
        except ValueError:
            pass

    res = await db.execute(stmt)
    vendor_orders = res.scalars().all()
    return [serialize_vendor_order(vo) for vo in vendor_orders]

@router.post("/orders/{vendor_order_id}/accept")
async def accept_shop_order(
    vendor_order_id: int,
    payload: ShopOrderActionRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Shop staff accepts incoming order and sets estimated kitchen prep time"""
    vo = await db.get(VendorOrder, vendor_order_id)
    if not vo:
        raise HTTPException(status_code=404, detail="Vendor order not found")

    vo.status = VendorOrderStatus.ACCEPTED
    if payload.estimated_prep_time_mins:
        vo.estimated_prep_time_mins = max(2, payload.estimated_prep_time_mins)

    # Update master order dynamic ETA
    master = await OrderService.get_order_by_id(db, vo.master_order_id)
    if master and master.status == MasterOrderStatus.CONFIRMED:
        master.status = MasterOrderStatus.PREPARING

    audit = AuditLog(
        user_id=str(current_user.id) if current_user else f"SHOP_STAFF_SHOP_{vo.shop_id}",
        role="SHOP_STAFF",
        action="SHOP_ORDER_ACCEPTED",
        target_entity="vendor_orders",
        target_id=str(vo.id),
        details=f"Vendor order #{vo.id} accepted. Kitchen prep time: {vo.estimated_prep_time_mins} mins."
    )
    db.add(audit)
    await db.commit()

    return {"success": True, "vendor_order_id": vo.id, "status": vo.status.value, "prep_time_mins": vo.estimated_prep_time_mins}

@router.post("/orders/{vendor_order_id}/mark-preparing")
async def mark_order_preparing(
    vendor_order_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Mark order as actively cooking / preparing in kitchen"""
    vo = await db.get(VendorOrder, vendor_order_id)
    if not vo:
        raise HTTPException(status_code=404, detail="Vendor order not found")

    vo.status = VendorOrderStatus.PREPARING
    master = await db.get(MasterOrder, vo.master_order_id)
    if master and master.status in [MasterOrderStatus.CONFIRMED, MasterOrderStatus.CREATED]:
        master.status = MasterOrderStatus.PREPARING

    await db.commit()
    return {"success": True, "vendor_order_id": vo.id, "status": vo.status.value}

@router.post("/orders/{vendor_order_id}/mark-ready")
async def mark_order_ready_for_pickup(
    vendor_order_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Mark package packed and ready for runner pickup"""
    vo = await db.get(VendorOrder, vendor_order_id)
    if not vo:
        raise HTTPException(status_code=404, detail="Vendor order not found")

    vo.status = VendorOrderStatus.READY_FOR_PICKUP
    master = await db.get(MasterOrder, vo.master_order_id)
    if master and master.status == MasterOrderStatus.PREPARING:
        master.status = MasterOrderStatus.PICKING_UP

    audit = AuditLog(
        user_id=str(current_user.id) if current_user else f"SHOP_STAFF_SHOP_{vo.shop_id}",
        role="SHOP_STAFF",
        action="PACKAGE_READY_FOR_PICKUP",
        target_entity="vendor_orders",
        target_id=str(vo.id),
        details=f"Vendor order #{vo.id} packed and waiting at counter for runner."
    )
    db.add(audit)
    await db.commit()

    return {"success": True, "vendor_order_id": vo.id, "status": vo.status.value}

@router.post("/orders/{vendor_order_id}/reject")
async def reject_shop_order(
    vendor_order_id: int,
    payload: ShopOrderActionRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Shop staff rejects order when out of stock or kitchen closed with automatic item refund"""
    vo = await db.get(VendorOrder, vendor_order_id)
    if not vo:
        raise HTTPException(status_code=404, detail="Vendor order not found")

    reason = payload.rejection_reason or "Kitchen at capacity or item unavailable"
    vo.status = VendorOrderStatus.REJECTED

    # Reject child items and process refunds
    items_res = await db.execute(select(OrderItem).where(OrderItem.vendor_order_id == vo.id))
    order_items = items_res.scalars().all()
    for oi in order_items:
        oi.is_rejected = True
        oi.rejection_reason = reason

    now = datetime.now(timezone.utc)
    master = await db.get(MasterOrder, vo.master_order_id)
    if master:
        # Check if all child vendor orders are rejected
        all_vos_res = await db.execute(select(VendorOrder).where(VendorOrder.master_order_id == master.id))
        all_vos = all_vos_res.scalars().all()
        all_rejected = all(v.status == VendorOrderStatus.REJECTED or v.id == vo.id for v in all_vos)

        if all_rejected:
            master.status = MasterOrderStatus.CANCELLED
            refund_amount = master.grand_total
        else:
            master.status = MasterOrderStatus.PARTIALLY_REFUNDED
            refund_amount = vo.shop_subtotal
            master.items_subtotal -= vo.shop_subtotal
            master.grand_total -= vo.shop_subtotal

        # Create refund record
        refund = Refund(
            master_order_id=master.id,
            vendor_order_id=vo.id,
            amount=refund_amount,
            reason=f"Shop rejection: {reason}",
            status=RefundStatus.PROCESSED,
            approved_by="ShopStaff",
            gateway_refund_id=f"rfnd_shop_reject_{vo.id}_{int(now.timestamp())}",
            created_at=now
        )
        db.add(refund)

    # Restore prepaid balance if shop is on prepaid model
    shop = await db.get(Shop, vo.shop_id)
    if shop and shop.settlement_type == SettlementType.PREPAID:
        await FinanceService.restore_prepaid_balance(
            db, shop.id, vo.shop_subtotal, f"REJECT-VO-{vo.id}", f"Shop rejection refund: {reason}"
        )

    audit = AuditLog(
        user_id=str(current_user.id) if current_user else f"SHOP_STAFF_SHOP_{vo.shop_id}",
        role="SHOP_STAFF",
        action="SHOP_ORDER_REJECTED",
        target_entity="vendor_orders",
        target_id=str(vo.id),
        details=f"Vendor order #{vo.id} rejected. Reason: {reason}"
    )
    db.add(audit)
    await db.commit()

    return {"success": True, "vendor_order_id": vo.id, "status": vo.status.value, "reason": reason}

@router.get("/menu")
async def get_shop_menu_items(
    shop_id: Optional[int] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """List all menu items for the shop with live availability toggles"""
    target_shop_id = await resolve_shop_id(shop_id, current_user, db)
    stmt = (
        select(MenuItem)
        .where(MenuItem.shop_id == target_shop_id)
        .order_by(MenuItem.category_id, MenuItem.id)
    )
    res = await db.execute(stmt)
    items = res.scalars().all()
    return [MenuItemOut.model_validate(it) for it in items]

@router.post("/menu/{item_id}/toggle-availability")
async def toggle_menu_item_availability(
    item_id: int,
    payload: ItemAvailabilityToggle,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Toggle item stock / availability live in real-time (86 an item)"""
    item = await db.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    item.is_available = payload.is_available

    audit = AuditLog(
        user_id=str(current_user.id) if current_user else f"SHOP_STAFF_SHOP_{item.shop_id}",
        role="SHOP_STAFF",
        action="ITEM_AVAILABILITY_TOGGLED",
        target_entity="menu_items",
        target_id=str(item.id),
        details=f"Item '{item.name}' availability set to {payload.is_available}"
    )
    db.add(audit)
    await db.commit()

    return {"success": True, "item_id": item.id, "name": item.name, "is_available": item.is_available}

@router.get("/stats")
async def get_shop_stats(
    shop_id: Optional[int] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Shop overview KPIs for shop staff inbox"""
    target_shop_id = await resolve_shop_id(shop_id, current_user, db)
    shop = await db.get(Shop, target_shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    orders_res = await db.execute(
        select(VendorOrder).where(VendorOrder.shop_id == target_shop_id)
    )
    all_orders = orders_res.scalars().all()

    pending_count = len([o for o in all_orders if o.status == VendorOrderStatus.PENDING])
    preparing_count = len([o for o in all_orders if o.status in [VendorOrderStatus.ACCEPTED, VendorOrderStatus.PREPARING]])
    ready_count = len([o for o in all_orders if o.status == VendorOrderStatus.READY_FOR_PICKUP])
    completed_today = len([o for o in all_orders if o.status == VendorOrderStatus.PICKED_UP])

    today_payable = sum(
        (float(o.shop_subtotal) for o in all_orders if o.status not in [VendorOrderStatus.REJECTED, VendorOrderStatus.CANCELLED]),
        0.0
    )

    return {
        "shop_id": shop.id,
        "shop_name": shop.name,
        "is_open": shop.is_open,
        "pending_orders": pending_count,
        "preparing_orders": preparing_count,
        "ready_for_pickup": ready_count,
        "completed_today": completed_today,
        "today_revenue_inr": round(today_payable, 2),
        "settlement_type": shop.settlement_type.value
    }

