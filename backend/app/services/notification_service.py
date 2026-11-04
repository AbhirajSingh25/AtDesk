from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
import httpx
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
    def get_registered_tokens(cls, user_id: int) -> List[str]:
        return USER_DEVICE_TOKENS.get(user_id, [])

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

        # 2. Deliver FCM push payload to registered device tokens
        tokens = USER_DEVICE_TOKENS.get(user_id, [])
        
        if tokens and settings.FCM_SERVER_KEY:
            try:
                headers = {
                    "Authorization": f"key={settings.FCM_SERVER_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "registration_ids": tokens,
                    "notification": {
                        "title": title,
                        "body": message,
                        "sound": "default"
                    },
                    "data": {
                        "event_type": event_type,
                        "notification_id": str(notification.id),
                        "timestamp": now.isoformat(),
                        **(metadata or {})
                    },
                    "priority": "high"
                }
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post("https://fcm.googleapis.com/fcm/send", json=payload, headers=headers)
                    logger.info(f"[FCM Push Delivery] Status {resp.status_code} for user {user_id}")
            except Exception as e:
                logger.warning(f"[FCM Push Warning] Push request exception: {e}")
        else:
            logger.info(f"[Notification Persisted] '{title}' for User {user_id} ({len(tokens)} token(s) registered)")

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
            title="Order in Preparation",
            message=f"{shops_str} started preparing your order #{order_number}.",
            event_type="PREPARATION_UPDATE",
            metadata={"order_number": order_number}
        )

    @classmethod
    async def notify_runner_approaching(cls, db: AsyncSession, user_id: int, order_number: str, tower: str, floor: int):
        return await cls.dispatch_notification(
            db=db,
            user_id=user_id,
            title="Runner Arriving",
            message=f"Your runner is arriving at {tower}, Floor {floor} with order #{order_number}.",
            event_type="RUNNER_APPROACHING",
            metadata={"order_number": order_number, "tower": tower, "floor": str(floor)}
        )

    @classmethod
    async def notify_desk_drop_prompt(cls, db: AsyncSession, user_id: int, order_number: str, master_otp: str, desk_location: str = "your desk"):
        return await cls.dispatch_notification(
            db=db,
            user_id=user_id,
            title="Desk Drop Ready",
            message=f"Runner is at {desk_location} for order #{order_number}. Provide OTP {master_otp} to receive your order.",
            event_type="DESK_DROP_OTP_PROMPT",
            metadata={"order_number": order_number, "master_otp": master_otp, "desk_location": desk_location}
        )

    @classmethod
    async def notify_desk_drop_otp_prompt(cls, db: AsyncSession, user_id: int, order_number: str, desk_location: str, master_otp: str):
        return await cls.notify_desk_drop_prompt(
            db=db,
            user_id=user_id,
            order_number=order_number,
            master_otp=master_otp,
            desk_location=desk_location
        )

    @classmethod
    async def notify_refund_processed(cls, db: AsyncSession, user_id: int, order_number: str, amount: float, reason: str):
        return await cls.dispatch_notification(
            db=db,
            user_id=user_id,
            title="Refund Processed",
            message=f"Refund of ₹{amount:.2f} processed for order #{order_number}. Reason: {reason}.",
            event_type="REFUND_PROCESSED",
            metadata={"order_number": order_number, "amount": str(amount)}
        )
