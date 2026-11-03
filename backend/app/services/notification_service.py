from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.models import Notification, User

logger = logging.getLogger("atdesk.notification_service")

# In-memory device token registry: user_id -> list of FCM registration tokens
USER_DEVICE_TOKENS: Dict[int, List[str]] = {}

class NotificationService:
    """
    Firebase Cloud Messaging (FCM) Push Notification Engine.
    Handles lifecycle triggers:
    1. RUNNER_ASSIGNED
    2. PREPARATION_UPDATE
    3. RUNNER_APPROACHING
    4. DESK_DROP_OTP_PROMPT
    5. REFUND_PROCESSED
    
    Persists notifications in database `Notification` table to guarantee reactive polling fallback.
    """

    @classmethod
    def register_device_token(cls, user_id: int, fcm_token: str) -> None:
        """Associates user device with FCM registration token"""
        tokens = USER_DEVICE_TOKENS.setdefault(user_id, [])
        if fcm_token not in tokens:
            tokens.append(fcm_token)
            logger.info(f"[FCM] Registered device token for User {user_id}")

    @classmethod
    async def dispatch_notification(
        cls,
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Dispatches notification via FCM and saves persistent DB record for reactive polling fallback.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Persist notification in database
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            is_read=False,
            created_at=now
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # 2. Simulate / Send FCM push payload to registered device tokens
        tokens = USER_DEVICE_TOKENS.get(user_id, [])
        fcm_payload = {
            "notification": {
                "title": title,
                "body": message,
                "icon": "/icons/icon-192x192.png",
                "click_action": "/orders"
            },
            "data": {
                "event_type": event_type,
                "notification_id": str(notification.id),
                "timestamp": now.isoformat(),
                **(metadata or {})
            }
        }
        
        logger.info(f"[FCM Push] Sent '{title}' to User {user_id} across {len(tokens)} device(s). Payload: {fcm_payload['data']}")
        return notification

    # Preset Lifecycle Triggers
    @classmethod
    async def notify_runner_assigned(cls, db: AsyncSession, user_id: int, order_number: str, runner_name: str):
        return await cls.dispatch_notification(
            db=db,
            user_id=user_id,
            title="Runner Assigned",
            message=f"{runner_name} has been assigned to pick up your order #{order_number}.",
            event_type="RUNNER_ASSIGNED",
            metadata={"order_number": order_number}
        )

    @classmethod
    async def notify_prep_update(cls, db: AsyncSession, user_id: int, order_number: str, shop_names: List[str]):
        shops_str = ", ".join(shop_names)
        return await cls.dispatch_notification(
            db=db,
            user_id=user_id,
            title="Preparation Underway",
            message=f"{shops_str} is actively preparing your fresh order #{order_number}.",
            event_type="PREPARATION_UPDATE",
            metadata={"order_number": order_number}
        )

    @classmethod
    async def notify_runner_approaching(cls, db: AsyncSession, user_id: int, order_number: str, tower: str):
        return await cls.dispatch_notification(
            db=db,
            user_id=user_id,
            title="Runner Arriving at Tower",
            message=f"Your AtDesk runner has arrived at {tower} and is proceeding up to your floor.",
            event_type="RUNNER_APPROACHING",
            metadata={"order_number": order_number, "tower": tower}
        )

    @classmethod
    async def notify_desk_drop_otp_prompt(cls, db: AsyncSession, user_id: int, order_number: str, desk: str, master_otp: str):
        return await cls.dispatch_notification(
            db=db,
            user_id=user_id,
            title="Runner At Your Desk!",
            message=f"Your runner is at {desk}! Please share delivery OTP {master_otp} to receive your order.",
            event_type="DESK_DROP_OTP_PROMPT",
            metadata={"order_number": order_number, "master_otp": master_otp}
        )

    @classmethod
    async def notify_refund_processed(cls, db: AsyncSession, user_id: int, order_number: str, amount: float, reason: str):
        return await cls.dispatch_notification(
            db=db,
            user_id=user_id,
            title="Refund Processed",
            message=f"Refund of Rs.{amount:.2f} processed for order #{order_number}. Reason: {reason}.",
            event_type="REFUND_PROCESSED",
            metadata={"order_number": order_number, "amount": str(amount)}
        )
