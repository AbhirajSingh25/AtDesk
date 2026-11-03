from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.models import User, Notification
from backend.app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications & FCM"])

@router.get("/my-notifications")
async def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reactive polling fallback: retrieves in-app notifications for employee/runner.
    """
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.id.desc())
        .limit(30)
    )
    res = await db.execute(stmt)
    notifications = res.scalars().all()

    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notifications
    ]

@router.post("/register-token")
async def register_device_fcm_token(
    payload: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    """Register device FCM push token for current user"""
    token = payload.get("fcm_token")
    if not token:
        raise HTTPException(status_code=400, detail="fcm_token is required")
    
    NotificationService.register_device_token(current_user.id, token)
    return {"success": True, "message": "FCM device token registered"}

@router.post("/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read"""
    notif = await db.get(Notification, notification_id)
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    await db.commit()
    return {"success": True}

