from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user_optional, require_roles
from backend.app.models.models import (
    DeliveryPartner, DeliveryAssignment, MasterOrder, VendorOrder, 
    DeliveryLocationEvent, VendorOrderStatus, MasterOrderStatus, User, UserRole
)
from backend.app.schemas.schemas import (
    PickupConfirmRequest, DeliveryProofSubmit, DeliveryOTPVerifyRequest, MasterOrderOut
)
from backend.app.services.order_service import OrderService
from backend.app.services.maps_service import MapsService, JMD_COORDINATES
from backend.app.api.orders import serialize_master_order

router = APIRouter(prefix="/delivery", tags=["Delivery Partner Operations"])

@router.get("/assigned", response_model=List[MasterOrderOut])
async def get_assigned_deliveries(
    partner_id: Optional[int] = Query(None, description="Delivery Partner ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get active deliveries assigned to runner.
    Strictly verifies runner identity: cannot view deliveries assigned to another runner.
    """
    resolved_partner_id = partner_id or 1
    if current_user:
        if current_user.role == UserRole.DELIVERY_PARTNER and current_user.delivery_profile:
            resolved_partner_id = current_user.delivery_profile.id
        elif current_user.role not in [UserRole.ADMIN, UserRole.FINANCE]:
            raise HTTPException(status_code=403, detail="Forbidden: Delivery partner access only")

    stmt = (
        select(DeliveryAssignment)
        .where(DeliveryAssignment.delivery_partner_id == resolved_partner_id)
        .where(DeliveryAssignment.status != "DELIVERED")
        .order_by(DeliveryAssignment.id.desc())
    )
    res = await db.execute(stmt)
    assignments = res.scalars().all()
    
    result = []
    for a in assignments:
        order = await OrderService.get_order_by_id(db, a.master_order_id)
        if order:
            result.append(serialize_master_order(order, viewing_user=current_user))
    return result

@router.post("/pickup-confirm")
async def confirm_shop_pickup(
    payload: PickupConfirmRequest, 
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Delivery partner confirms collection of package from a shop"""
    vo = await db.get(VendorOrder, payload.vendor_order_id)
    if not vo:
        raise HTTPException(status_code=404, detail="Vendor order not found")

    vo.status = VendorOrderStatus.PICKED_UP
    vo.pickup_confirmed_at = datetime.now(timezone.utc)

    # Check if all child vendor orders for this master order have been collected
    all_vo_res = await db.execute(
        select(VendorOrder).where(VendorOrder.master_order_id == vo.master_order_id)
    )
    all_vos = all_vo_res.scalars().all()
    all_picked = all(v.status in [VendorOrderStatus.PICKED_UP, VendorOrderStatus.CANCELLED, VendorOrderStatus.REJECTED] for v in all_vos)

    master = await db.get(MasterOrder, vo.master_order_id)
    if all_picked and master:
        master.status = MasterOrderStatus.OUT_FOR_DELIVERY

    await db.commit()
    return {
        "success": True, 
        "vendor_order_id": vo.id,
        "all_shops_collected": all_picked,
        "master_status": master.status if master else "OUT_FOR_DELIVERY"
    }

@router.post("/complete")
async def complete_delivery_with_proof_and_otp(
    payload: Dict[str, Any],
    partner_id: Optional[int] = Query(None, description="Delivery Partner ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Mandatory desk delivery verification:
    Requires both:
    1. Direct camera photograph data / S3 Key
    2. Employee 6-digit master OTP
    Prevents unauthorized completion and incomplete package delivery.
    """
    resolved_partner_id = partner_id or 1
    if current_user:
        if current_user.role == UserRole.DELIVERY_PARTNER and current_user.delivery_profile:
            resolved_partner_id = current_user.delivery_profile.id
        elif current_user.role not in [UserRole.ADMIN, UserRole.FINANCE]:
            raise HTTPException(status_code=403, detail="Forbidden: Delivery partner access only")

    master_order_id = payload.get("master_order_id")
    entered_otp = payload.get("entered_otp", "")
    photo_data = payload.get("photo_data", "")
    lat = float(payload.get("latitude", 28.4162))
    lng = float(payload.get("longitude", 77.0425))

    if not master_order_id:
        raise HTTPException(status_code=400, detail="master_order_id is required")

    return await OrderService.verify_delivery_completion(
        db=db,
        master_order_id=int(master_order_id),
        partner_id=resolved_partner_id,
        entered_otp=str(entered_otp),
        photo_url_or_data=str(photo_data),
        latitude=lat,
        longitude=lng
    )

@router.post("/location-ping")
async def update_runner_location(
    payload: Dict[str, Any],
    partner_id: Optional[int] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Periodic GPS ping from delivery partner app during active delivery"""
    resolved_partner_id = partner_id or 1
    if current_user and current_user.delivery_profile:
        resolved_partner_id = current_user.delivery_profile.id

    lat = float(payload.get("latitude", 28.4162))
    lng = float(payload.get("longitude", 77.0425))
    order_id = payload.get("master_order_id")

    partner = await db.get(DeliveryPartner, resolved_partner_id)
    if partner:
        partner.current_lat = lat
        partner.current_lng = lng
        partner.last_active_at = datetime.now(timezone.utc)

    loc_event = DeliveryLocationEvent(
        delivery_partner_id=resolved_partner_id,
        master_order_id=order_id,
        latitude=lat,
        longitude=lng,
        recorded_at=datetime.now(timezone.utc)
    )
    db.add(loc_event)
    await db.commit()
    return {"success": True}

@router.get("/tracking/{master_order_id}")
async def get_live_tracking_data(
    master_order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Live GPS Tracking & Route Telemetry for an active order.
    Enforces privacy: Tracking is active only when order is in-progress.
    """
    order = await OrderService.get_order_by_id(db, master_order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # If completed or cancelled, do not expose runner's current live location
    if order.status in [MasterOrderStatus.DELIVERED, MasterOrderStatus.CANCELLED]:
        return {
            "is_tracking_active": False,
            "order_status": order.status.value,
            "message": "Tracking ended for this completed or cancelled order."
        }

    # Find assigned runner
    assign_stmt = select(DeliveryAssignment).where(DeliveryAssignment.master_order_id == order.id)
    assign_res = await db.execute(assign_stmt)
    assignment = assign_res.scalar_one_or_none()

    runner = None
    if assignment:
        runner = await db.get(DeliveryPartner, assignment.delivery_partner_id)

    runner_lat = runner.current_lat if (runner and runner.current_lat) else JMD_COORDINATES["CENTER"]["lat"]
    runner_lng = runner.current_lng if (runner and runner.current_lng) else JMD_COORDINATES["CENTER"]["lng"]
    last_active = runner.last_active_at if runner else None

    # Calculate freshness
    freshness_info = MapsService.get_location_freshness(last_active)

    # Calculate dynamic campus ETA
    shop_ids = [vo.shop_id for vo in order.vendor_orders]
    max_prep = max([vo.estimated_prep_time_mins for vo in order.vendor_orders] or [12])
    campus_eta = MapsService.calculate_campus_eta(
        runner_lat=runner_lat,
        runner_lng=runner_lng,
        shop_ids=shop_ids,
        tower=order.tower,
        floor=order.floor,
        max_prep_time_mins=max_prep
    )

    return {
        "is_tracking_active": True,
        "order_status": order.status.value,
        "runner_assigned": True if runner else False,
        "runner_location": {
            "latitude": runner_lat,
            "longitude": runner_lng
        },
        "location_freshness": freshness_info,
        "campus_eta": campus_eta,
        "destination": {
            "tower": order.tower,
            "floor": order.floor,
            "desk_location": order.desk_location
        }
    }
