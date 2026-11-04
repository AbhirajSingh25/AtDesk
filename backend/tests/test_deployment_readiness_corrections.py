import json
import pytest
import pytest_asyncio
import hmac
import hashlib
from decimal import Decimal
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.seed.seed_data import seed_database
from backend.app.models.models import MasterOrder, Payment, PaymentStatus
from backend.app.services.sms_service import SmsService, StagingMockSmsProvider, GupshupSmsProvider
from backend.app.services.payment_gateway import RazorpayGatewayService

@pytest_asyncio.fixture(scope="function")
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        await seed_database(session)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield async_session
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_webhook_missing_signature_rejected():
    """Verify that Razorpay webhook endpoint rejects requests with missing X-Razorpay-Signature header"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {"event": "payment.captured", "payload": {}}
        response = await ac.post("/api/payments/razorpay/webhook", json=payload)
        assert response.status_code == 400
        assert "Missing required X-Razorpay-Signature" in response.json()["detail"]

@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected():
    """Verify that Razorpay webhook endpoint rejects invalid HMAC signatures"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {"event": "payment.captured", "payload": {}}
        headers = {"X-Razorpay-Signature": "invalid_forged_signature_123456"}
        response = await ac.post("/api/payments/razorpay/webhook", json=payload, headers=headers)
        assert response.status_code == 400
        assert "Invalid Razorpay webhook cryptographic signature" in response.json()["detail"]

@pytest.mark.asyncio
async def test_webhook_valid_signature_accepted_and_idempotent(test_db):
    """Verify that a cryptographically signed webhook is accepted, and duplicate events are handled idempotently"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create test order first
        item = (await ac.get("/api/shops/1")).json()["items"][0]
        create_res = await ac.post("/api/orders?user_id=1", json={
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "tower": "Tower B",
            "floor": 6,
            "desk_location": "Desk B-612"
        })
        order = create_res.json()
        gateway_order_id = f"order_mock_{order['id']}"

        payment_id = f"pay_test_{int(datetime.now(timezone.utc).timestamp())}_{order['id']}"
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": gateway_order_id,
                        "amount": int(order["grand_total"] * 100),
                        "currency": "INR",
                        "status": "captured"
                    }
                }
            }
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        valid_signature = RazorpayGatewayService.generate_webhook_signature(body_bytes)

        # 1. First event submission -> Accepted
        headers = {
            "X-Razorpay-Signature": valid_signature,
            "Content-Type": "application/json"
        }
        response1 = await ac.post("/api/payments/razorpay/webhook", content=body_bytes, headers=headers)
        assert response1.status_code == 200
        assert response1.json()["status"] == "ok"

        # 2. Duplicate event submission -> Handled idempotently without error
        response2 = await ac.post("/api/payments/razorpay/webhook", content=body_bytes, headers=headers)
        assert response2.status_code == 200
        assert "duplicate" in response2.json()["message"].lower() or "idempotent" in response2.json()["message"].lower()

@pytest.mark.asyncio
async def test_unauthenticated_protected_requests_rejected():
    """Verify that unauthenticated requests to protected endpoints are rejected with 401"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # User profile
        res_me = await ac.get("/api/auth/me")
        assert res_me.status_code == 401

        # My notifications
        res_notif = await ac.get("/api/notifications/my-notifications")
        assert res_notif.status_code == 401

        # Register FCM token
        res_fcm = await ac.post("/api/notifications/register-token", json={"fcm_token": "abc"})
        assert res_fcm.status_code == 401

@pytest.mark.asyncio
async def test_production_otp_never_leaked():
    """Verify that production OTPs are never returned in responses or exposed when ENVIRONMENT is production"""
    original_env = settings.ENVIRONMENT
    original_provider = settings.SMS_PROVIDER
    try:
        settings.ENVIRONMENT = "production"
        settings.SMS_PROVIDER = "GUPSHUP"
        phone = "+919999111222"
        # Reset state for this phone
        SmsService._otp_store.pop("9999111222", None)
        SmsService._request_history.pop("9999111222", None)
        SmsService._lockouts.pop("9999111222", None)
        
        # Test SmsService method directly
        res = SmsService.generate_and_send_otp(phone)
        assert "staging_test_otp" not in res
        
        # Test HTTP API
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            http_res = await ac.post("/api/auth/send-otp", json={"phone": "+919999111223"})
            # In production, if mock provider is active or no API key, it fails cleanly
            if http_res.status_code == 200:
                assert "staging_test_otp" not in http_res.json()
    finally:
        settings.ENVIRONMENT = original_env
        settings.SMS_PROVIDER = original_provider

def test_mock_sms_strictly_forbidden_in_production():
    """Verify that StagingMockSmsProvider rejects SMS delivery in production mode"""
    original_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        provider = StagingMockSmsProvider()
        result = provider.send_sms("9876543210", "123456")
        assert result.success is False
        assert result.status == "FAILED"
        assert "forbidden" in result.details.lower()
    finally:
        settings.ENVIRONMENT = original_env

def test_production_security_guardrail_enforcement():
    """Verify validate_production_secrets fails fast when production secrets are absent or predictable"""
    original_env = settings.ENVIRONMENT
    original_key = settings.SECRET_KEY
    try:
        settings.ENVIRONMENT = "production"
        settings.SECRET_KEY = "atdesk_dev_insecure_secret_key_change_in_production_2026"
        with pytest.raises(RuntimeError, match="predictable SECRET_KEY"):
            settings.validate_production_secrets()
    finally:
        settings.ENVIRONMENT = original_env
        settings.SECRET_KEY = original_key
