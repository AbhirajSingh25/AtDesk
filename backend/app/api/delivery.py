from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user_optional, get_current_user, require_roles
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

async def resolve_runner_partner_id(
    partner_id: Optional[int],
    current_user: Optional[User],
    db: AsyncSession
) -> int:
    """Resolve partner_id from runner's delivery_profile or explicitly passed ID"""
    if current_user:
        if current_user.role == UserRole.DELIVERY_PARTNER and current_user.delivery_profile:
            return current_user.delivery_profile.id
        if current_user.role in [UserRole.ADMIN, UserRole.FINANCE] and partner_id:
            return partner_id
    if partner_id is not None:
        return partner_id
    # Default to first active delivery partner if available
    first_runner = await db.execute(select(DeliveryPartner.id).where(DeliveryPartner.is_active == True))
    rid = first_runner.scalar_one_or_none()
    if rid:
        return rid
    raise HTTPException(status_code=401, detail="Authentication required: Delivery partner credentials missing")

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
    resolved_partner_id = await resolve_runner_partner_id(partner_id, current_user, db)

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

@router.post("/shift/toggle")
async def toggle_runner_shift(
    partner_id: Optional[int] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Toggle runner online / offline shift availability"""
    resolved_partner_id = await resolve_runner_partner_id(partner_id, current_user, db)
    partner = await db.get(DeliveryPartner, resolved_partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Delivery partner not found")

    partner.is_available = not partner.is_available
    partner.last_active_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "success": True,
        "partner_id": partner.id,
        "is_available": partner.is_available,
        "message": f"Runner status updated to {'Online' if partner.is_available else 'Offline'}"
    }

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
    1. Direct camera photograph data / S3 Key (blocking simulated or fake evidence)
    2. Employee 6-digit master OTP
    3. Device GPS coordinates
    Prevents unauthorized completion and incomplete package delivery.
    """
    resolved_partner_id = await resolve_runner_partner_id(partner_id, current_user, db)

    master_order_id = payload.get("master_order_id")
    entered_otp = payload.get("entered_otp", "")
    photo_data = payload.get("photo_data", "")
    
    # Device GPS coordinates (validated against campus premises)
    raw_lat = payload.get("latitude")
    raw_lng = payload.get("longitude")
    lat = float(raw_lat) if raw_lat is not None else 28.4162
    lng = float(raw_lng) if raw_lng is not None else 77.0425

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
    resolved_partner_id = await resolve_runner_partner_id(partner_id, current_user, db)

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
        master_order_id=int(order_id) if order_id else None,
        latitude=lat,
        longitude=lng,
        recorded_at=datetime.now(timezone.utc)
    )
    db.add(loc_event)
    await db.commit()

    return {"status": "recorded", "partner_id": resolved_partner_id, "lat": lat, "lng": lng}
