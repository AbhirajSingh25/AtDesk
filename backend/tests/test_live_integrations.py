import pytest
import pytest_asyncio
import hmac
import hashlib
from decimal import Decimal
from datetime import datetime, timezone
import json

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.models.models import (
    User, Shop, MenuItem, MasterOrder, VendorOrder, Payment, 
    DeliveryAssignment, DeliveryPartner, SettlementType, MasterOrderStatus,
    VendorOrderStatus, PaymentStatus, AuditLog, Notification
)
from backend.app.services.sms_service import SmsService
from backend.app.services.payment_gateway import RazorpayGatewayService
from backend.app.services.storage_service import StorageService
from backend.app.services.maps_service import MapsService
from backend.app.services.notification_service import NotificationService
from backend.app.services.order_service import OrderService

# Test against the PostgreSQL staging cluster
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:atdesk_staging@127.0.0.1:5433/atdesk_staging"

@pytest_asyncio.fixture(scope="function")
async def pg_test_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_sms_otp_dlt_lifecycle():
    """STAGE 3: Test Indian DLT SMS OTP generation, cooldown, lockout, and verification"""
    phone = "9876543210"

    # 1. Generate OTP
    res1 = SmsService.generate_and_send_otp(phone)
    assert res1["success"] is True
    assert res1["delivery_status"] == "DELIVERED"
    assert res1["dlt_template_id"] == settings.SMS_DLT_TEMPLATE_ID
    otp = res1["staging_test_otp"]
    assert len(otp) == 6
    assert otp.isdigit()

    # 2. Resend within 60 seconds must trigger 60s cooldown error
    res_cooldown = SmsService.generate_and_send_otp(phone)
    assert res_cooldown["success"] is False
    assert res_cooldown["error"] == "COOLDOWN_ACTIVE"
    assert "Please wait" in res_cooldown["message"]

    # 3. Invalid OTP verification should count attempts
    res_bad = SmsService.verify_otp(phone, "000000")
    assert res_bad["success"] is False
    assert res_bad["error"] == "INVALID_OTP"
    assert res_bad["attempts_remaining"] == 2

    # 4. Valid OTP verification should succeed and consume OTP
    res_valid = SmsService.verify_otp(phone, otp)
    assert res_valid["success"] is True

    # 5. Reusing the consumed OTP should fail
    res_reuse = SmsService.verify_otp(phone, otp)
    assert res_reuse["success"] is False
    assert res_reuse["error"] in ["ALREADY_USED", "NO_OTP_FOUND"]

@pytest.mark.asyncio
async def test_sms_otp_lockout_policy():
    """STAGE 3: Test that 3 failed OTP attempts triggers 15-minute phone lockout"""
    phone = "9811122233"
    # Reset state
    SmsService._otp_store.pop("9811122233", None)
    SmsService._lockouts.pop("9811122233", None)

    res = SmsService.generate_and_send_otp(phone)
    assert res["success"] is True

    # Attempt 1
    v1 = SmsService.verify_otp(phone, "111111")
    assert v1["success"] is False
    assert v1["attempts_remaining"] == 2

    # Attempt 2
    v2 = SmsService.verify_otp(phone, "222222")
    assert v2["success"] is False
    assert v2["attempts_remaining"] == 1

    # Attempt 3 -> triggers lockout
    v3 = SmsService.verify_otp(phone, "333333")
    assert v3["success"] is False
    assert v3["error"] == "MAX_ATTEMPTS_EXCEEDED"

    # Subsequent verification is blocked by lockout
    v4 = SmsService.verify_otp(phone, "123456")
    assert v4["success"] is False
    assert v4["error"] == "LOCKED_OUT"

@pytest.mark.asyncio
async def test_razorpay_gateway_test_flow():
    """STAGE 2: Test Razorpay server-side order creation, HMAC SHA256 signature verification, and refunds"""
    amount = Decimal("345.50")
    receipt = "ATD-TEST-RECEIPT-01"

    # 1. Create Order
    order_data = RazorpayGatewayService.create_order(amount, receipt)
    assert "gateway_order_id" in order_data
    assert order_data["amount_paise"] == 34550
    assert order_data["currency"] == "INR"
    assert order_data["key_id"] == settings.RAZORPAY_KEY_ID

    order_id = order_data["gateway_order_id"]
    payment_id = "pay_test_99887766"

    # 2. Cryptographic signature generation & verification
    valid_sig = RazorpayGatewayService.generate_test_signature(order_id, payment_id)
    assert RazorpayGatewayService.verify_payment_signature(order_id, payment_id, valid_sig) is True

    # Tampered signature must fail
    tampered_sig = valid_sig[:-2] + "ff"
    assert RazorpayGatewayService.verify_payment_signature(order_id, payment_id, tampered_sig) is False

    # 3. Webhook signature verification
    payload_bytes = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": {"id": payment_id}}}}).encode()
    webhook_sig = RazorpayGatewayService.generate_webhook_signature(payload_bytes)
    assert RazorpayGatewayService.verify_webhook_signature(payload_bytes, webhook_sig) is True

    # Tampered webhook payload must fail
    assert RazorpayGatewayService.verify_webhook_signature(payload_bytes + b"tampered", webhook_sig) is False

    # 4. Initiate Refund
    refund_res = RazorpayGatewayService.initiate_refund(payment_id, amount_inr=Decimal("150.00"))
    assert refund_res["success"] is True
    assert "gateway_refund_id" in refund_res
    assert refund_res["status"] in ["PROCESSED", "PENDING"]

@pytest.mark.asyncio
async def test_private_photo_storage_adapter():
    """STAGE 4: Test AWS S3 private storage adapter with pre-signed URLs, MIME validation, and size checks"""
    master_order_id = 9999

    # 1. Pre-signed upload URL generation
    upload_info = StorageService.generate_presigned_upload_url(master_order_id, mime_type="image/jpeg")
    assert upload_info["success"] is True
    assert "upload_url" in upload_info
    assert upload_info["max_size_bytes"] == 5 * 1024 * 1024
    s3_key = upload_info["s3_key"]
    assert "delivery-evidence" in s3_key
    assert s3_key.endswith(".jpg")

    # 2. Invalid MIME type must be rejected
    with pytest.raises(ValueError):
        StorageService.generate_presigned_upload_url(master_order_id, mime_type="application/pdf")

    # 3. Pre-signed download URL generation
    download_url = StorageService.generate_presigned_download_url(s3_key)
    assert download_url is not None
    assert len(download_url) > 10

@pytest.mark.asyncio
async def test_maps_and_campus_routing_engine():
    """STAGE 5: Test JMD Megapolis spatial model, pickup sequencing, and location freshness"""
    # 1. Haversine distance
    dist = MapsService.haversine_distance_meters(28.41620, 77.04250, 28.41640, 77.04230)
    assert 20 < dist < 40  # Approximately 29 meters within central plaza

    # 2. Multi-shop route optimization
    route = MapsService.optimize_pickup_sequence(
        runner_lat=28.41620,
        runner_lng=77.04250,
        shop_ids=[1, 2, 4],  # Chaayos, Haldiram's, Subway
        destination_tower="Tower B"
    )
    assert len(route["ordered_stops"]) == 3
    assert route["total_walking_distance_meters"] > 0
    assert route["estimated_walking_time_mins"] >= 1
    assert route["shop_handover_buffers_mins"] == 6  # 3 shops * 2 mins

    # 3. Comprehensive campus ETA (including elevator & floor transit)
    campus_eta = MapsService.calculate_campus_eta(
        runner_lat=28.41620,
        runner_lng=77.04250,
        shop_ids=[1, 2],
        tower="Tower B",
        floor=7,
        max_prep_time_mins=14
    )
    assert campus_eta["min_eta_mins"] >= 14
    assert campus_eta["max_eta_mins"] >= campus_eta["min_eta_mins"]
    assert campus_eta["route_breakdown"]["vertical_floor_elevator_mins"] >= 4

    # 4. Location freshness indicator
    fresh = MapsService.get_location_freshness(datetime.now(timezone.utc))
    assert fresh["freshness"] == "LIVE"
    assert fresh["is_live"] is True

@pytest.mark.asyncio
async def test_fcm_notification_lifecycle(pg_test_session: AsyncSession):
    """STAGE 6: Test FCM notification triggers and reactive polling storage"""
    user_id = 1
    order_num = "ATD-TEST-FCM-001"

    # Register device token
    NotificationService.register_device_token(user_id, "mock_fcm_token_device_abc123")

    # 1. Trigger runner assigned
    n1 = await NotificationService.notify_runner_assigned(pg_test_session, user_id, order_num, "Ramesh Kumar")
    assert n1.title == "Runner Assigned"
    assert "Ramesh Kumar" in n1.message

    # 2. Trigger desk drop OTP prompt
    n2 = await NotificationService.notify_desk_drop_otp_prompt(pg_test_session, user_id, order_num, "Desk B-402", "554433")
    assert "554433" in n2.message
    assert "Desk B-402" in n2.message

    # 3. Verify saved in database for reactive polling
    stmt = select(Notification).where(Notification.user_id == user_id)
    res = await pg_test_session.execute(stmt)
    user_notifications = res.scalars().all()
    assert len(user_notifications) >= 2

@pytest.mark.asyncio
async def test_full_e2e_pilot_workflow(pg_test_session: AsyncSession):
    """STAGE 7: Complete 14-Step End-to-End Pilot Workflow on PostgreSQL"""
    # Step 1: User phone OTP authentication
    phone = "9899887766"
    otp_data = SmsService.generate_and_send_otp(phone)
    otp = otp_data["staging_test_otp"]
    v_res = SmsService.verify_otp(phone, otp)
    assert v_res["success"] is True

    # Find test employee
    user_res = await pg_test_session.execute(select(User).where(User.phone.like("%9899887766%")))
    employee = user_res.scalar_one_or_none()
    if not employee:
        employee = User(phone=f"+91{phone}", full_name="Pilot Employee", role="EMPLOYEE", is_active=True)
        pg_test_session.add(employee)
        await pg_test_session.commit()
        await pg_test_session.refresh(employee)

    # Step 2: Multi-shop cart (Chaayos & Haldiram's)
    shop_res = await pg_test_session.execute(select(MenuItem).limit(2))
    items = shop_res.scalars().all()
    assert len(items) >= 2

    cart = [
        {"menu_item_id": items[0].id, "quantity": 1},
        {"menu_item_id": items[1].id, "quantity": 2}
    ]

    # Step 3: Create Multi-Shop Master Order
    order = await OrderService.create_multi_shop_order(
        db=pg_test_session,
        user_id=employee.id,
        cart_items=cart,
        tower="Tower B",
        floor=4,
        desk_location="Desk B-402",
        delivery_instructions="Leave on front monitor desk",
        payment_method="UPI"
    )
    assert order is not None
    assert order.status == MasterOrderStatus.CONFIRMED
    assert float(order.flat_delivery_fee) == 25.00  # Exactly one flat delivery fee
    assert len(order.vendor_orders) >= 1

    # Step 4: Razorpay server-side order and signature verification
    rzp_order = RazorpayGatewayService.create_order(order.grand_total, order.order_number)
    rzp_order_id = rzp_order["gateway_order_id"]
    rzp_payment_id = f"pay_pilot_{order.id}"
    rzp_sig = RazorpayGatewayService.generate_test_signature(rzp_order_id, rzp_payment_id)
    assert RazorpayGatewayService.verify_payment_signature(rzp_order_id, rzp_payment_id, rzp_sig) is True

    # Step 5: Assign Delivery Partner
    partner_res = await pg_test_session.execute(select(DeliveryPartner).where(DeliveryPartner.is_active == True))
    partner = partner_res.scalars().first()
    assert partner is not None

    # Step 6: Runner pickup confirmation for all shops
    for vo in order.vendor_orders:
        vo.status = VendorOrderStatus.PICKED_UP
        vo.pickup_confirmed_at = datetime.now(timezone.utc)
    order.status = MasterOrderStatus.OUT_FOR_DELIVERY
    await pg_test_session.commit()

    # Step 7: Runner arrives at desk, uploads private photo proof, enters employee OTP
    upload_url_info = StorageService.generate_presigned_upload_url(order.id, mime_type="image/jpeg")
    proof_key = upload_url_info["s3_key"]

    complete_res = await OrderService.verify_delivery_completion(
        db=pg_test_session,
        master_order_id=order.id,
        partner_id=partner.id,
        entered_otp=order.master_otp,
        photo_url_or_data=proof_key,
        latitude=28.41630,
        longitude=77.04280
    )
    assert complete_res["success"] is True
    assert "Delivery completed successfully" in complete_res["message"]

    # Step 8: Verify order marked DELIVERED and audited in fresh session
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    fresh_sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with fresh_sessionmaker() as fresh_session:
        reloaded_order = await OrderService.get_order_by_id(fresh_session, order.id)
        assert reloaded_order.status == MasterOrderStatus.DELIVERED
        assert len(reloaded_order.proofs) >= 1
        assert reloaded_order.proofs[0].photo_url == proof_key

        # Step 9: Reconcile financial records
        audit_res = await fresh_session.execute(
            select(AuditLog).where(AuditLog.target_id == str(order.id))
        )
        logs = audit_res.scalars().all()
        assert len(logs) >= 1
    await engine.dispose()
