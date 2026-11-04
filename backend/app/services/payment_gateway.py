import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
import razorpay

from backend.app.core.config import settings

logger = logging.getLogger("atdesk.payment_gateway")

class RazorpayGatewayService:
    """
    Production-grade Razorpay Payment Gateway Service.
    Enforces:
    1. Server-side order creation (amount in paise, currency INR).
    2. HMAC SHA-256 signature verification for client payment callbacks.
    3. Mandatory cryptographic HMAC SHA-256 signature verification for webhooks.
    4. Full and partial refund tracking with real gateway refund IDs.
    5. Clean separation between test mode and live production environments.
    """

    @staticmethod
    def get_client() -> razorpay.Client:
        """Returns initialized Razorpay client using configured credentials"""
        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    @staticmethod
    def create_order(amount_inr: Decimal, receipt: str, notes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Creates an order on Razorpay server-side.
        Amount must be provided in INR and is converted to Paise (1 INR = 100 paise).
        """
        amount_paise = int(amount_inr * 100)
        data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": notes or {
                "platform": "AtDesk",
                "parent_brand": "The Sorted Club",
                "location": "JMD Megapolis, Gurugram"
            },
            "payment_capture": 1
        }

        is_prod = settings.ENVIRONMENT.lower() in ["production", "prod"]

        # If live/production credentials or non-mock test key, call Razorpay API
        if not settings.RAZORPAY_KEY_ID.startswith("rzp_test_AtDeskDemo"):
            try:
                client = RazorpayGatewayService.get_client()
                order = client.order.create(data=data)
                logger.info(f"[Razorpay] Successfully created server-side order {order['id']} for ₹{amount_inr}")
                return {
                    "gateway_order_id": order["id"],
                    "amount": amount_inr,
                    "amount_paise": amount_paise,
                    "currency": "INR",
                    "receipt": receipt,
                    "status": order.get("status", "created"),
                    "key_id": settings.RAZORPAY_KEY_ID
                }
            except Exception as e:
                logger.error(f"[Razorpay API Error] Order creation failed: {e}")
                if is_prod:
                    raise RuntimeError(f"Razorpay order creation failed: {e}")
                # In non-production testing, fallback to test mode order
                logger.warning(f"Falling back to test mode order for offline dev: {e}")

        # Deterministic test mode order strictly for local dev/testing
        if is_prod:
            raise RuntimeError("Production environment requires real Razorpay credentials, not mock demo keys.")

        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_order_id = f"order_rzp_test_{timestamp_ms}_{receipt.replace('-', '_')}"
        return {
            "gateway_order_id": mock_order_id,
            "amount": amount_inr,
            "amount_paise": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "status": "created",
            "key_id": settings.RAZORPAY_KEY_ID
        }

    @staticmethod
    def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        """
        Cryptographic verification of Razorpay client payment signature:
        HMAC SHA-256 of `order_id + "|" + payment_id` with `RAZORPAY_KEY_SECRET`.
        """
        if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
            return False

        message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        
        expected_signature = hmac.new(
            secret,
            message,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, razorpay_signature)

    @staticmethod
    def generate_test_signature(razorpay_order_id: str, razorpay_payment_id: str) -> str:
        """Helper to generate valid signature for integration testing with test secret"""
        message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    @staticmethod
    def verify_webhook_signature(body_bytes: bytes, received_signature: str) -> bool:
        """
        Validates mandatory HMAC SHA-256 signature on raw webhook payload using RAZORPAY_WEBHOOK_SECRET.
        """
        if not received_signature or not settings.RAZORPAY_WEBHOOK_SECRET:
            return False
        
        secret = settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8")
        expected_signature = hmac.new(
            secret,
            body_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, received_signature)

    @staticmethod
    def generate_webhook_signature(body_bytes: bytes) -> str:
        """Helper to generate webhook signature for test verification"""
        secret = settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8")
        return hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()

    @staticmethod
    def initiate_refund(
        payment_id: str,
        amount_inr: Optional[Decimal] = None,
        notes: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Initiates a full or partial refund via Razorpay.
        If amount is None, a full refund is processed.
        Tracks status: PROCESSED | PENDING | FAILED.
        """
        data: Dict[str, Any] = {
            "notes": notes or {"reason": "AtDesk Order Cancellation/Rejection"}
        }
        if amount_inr is not None:
            data["amount"] = int(amount_inr * 100)  # in paise

        is_prod = settings.ENVIRONMENT.lower() in ["production", "prod"]

        if not settings.RAZORPAY_KEY_ID.startswith("rzp_test_AtDeskDemo"):
            try:
                client = RazorpayGatewayService.get_client()
                refund = client.payment.refund(payment_id, data)
                logger.info(f"[Razorpay Refund] Success for payment {payment_id}. Refund ID: {refund['id']}")
                return {
                    "success": True,
                    "gateway_refund_id": refund["id"],
                    "payment_id": payment_id,
                    "amount": Decimal(str(refund["amount"] / 100.0)),
                    "status": refund.get("status", "processed").upper()
                }
            except Exception as e:
                logger.error(f"[Razorpay Refund Error] Payment {payment_id} refund failed: {e}")
                if is_prod:
                    return {
                        "success": False,
                        "error": str(e),
                        "gateway_refund_id": "",
                        "payment_id": payment_id,
                        "amount": amount_inr if amount_inr is not None else Decimal("0.00"),
                        "status": "FAILED"
                    }

        if is_prod:
            return {
                "success": False,
                "error": "Production mode requires real Razorpay credentials for refunds.",
                "status": "FAILED",
                "payment_id": payment_id
            }

        # Staging test mode refund simulation strictly for automated tests
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        mock_refund_id = f"rfnd_rzp_test_{timestamp_ms}_{payment_id[-8:]}"
        return {
            "success": True,
            "gateway_refund_id": mock_refund_id,
            "payment_id": payment_id,
            "amount": amount_inr if amount_inr is not None else Decimal("0.00"),
            "status": "PROCESSED"
        }
