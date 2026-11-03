import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import hmac
import hashlib
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token
from backend.app.seed.seed_data import seed_database
from backend.app.models.models import (
    Shop, MenuItem, MasterOrder, VendorOrder, MasterOrderStatus, 
    PaymentStatus, Refund, DeliveryAssignment, DeliveryPartner, User,
    ShopPrepaidAccount, ShopPrepaidLedger, SettlementType
)
from backend.app.services.order_service import OrderService
from backend.app.services.finance_service import FinanceService

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def async_test_db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
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
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["product"] == "AtDesk"
        assert "The Sorted Club" in data["brand"]
        assert "JMD Megapolis" in data["location"]

@pytest.mark.asyncio
async def test_shops_listing(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/shops")
        assert resp.status_code == 200
        shops = resp.json()
        assert len(shops) >= 5
        shop_names = [s["name"] for s in shops]
        assert any("Chaayos" in name for name in shop_names)
        assert any("Subway" in name for name in shop_names)

@pytest.mark.asyncio
async def test_multi_shop_order_and_flat_delivery_fee(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        shops_res = await client.get("/api/shops")
        shops = shops_res.json()
        shop1_id = shops[0]["id"]
        shop2_id = shops[1]["id"]

        detail1 = (await client.get(f"/api/shops/{shop1_id}")).json()
        detail2 = (await client.get(f"/api/shops/{shop2_id}")).json()

        item1 = detail1["items"][0]
        item2 = detail2["items"][0]

        payload = {
            "items": [
                {"menu_item_id": item1["id"], "quantity": 2},
                {"menu_item_id": item2["id"], "quantity": 1}
            ],
            "tower": "Tower B",
            "floor": 6,
            "desk_location": "Desk B-612",
            "delivery_instructions": "Leave on desk near monitor",
            "payment_method": "UPI"
        }

        # 1. Preview calculation
        preview_res = await client.post("/api/orders/calculate-preview", json=payload)
        assert preview_res.status_code == 200
        preview = preview_res.json()
        assert preview["min_eta_mins"] > 0
        assert preview["max_eta_mins"] >= preview["min_eta_mins"]

        # 2. Create Order
        create_res = await client.post("/api/orders?user_id=1", json=payload)
        assert create_res.status_code == 200
        order = create_res.json()

        assert order["status"] == "CONFIRMED"
        assert order["items_subtotal"] == (item1["price"] * 2) + item2["price"]
        assert order["flat_delivery_fee"] == 25.0
        assert order["grand_total"] == order["items_subtotal"] + 25.0
        assert len(order["vendor_orders"]) == 2
        assert len(order["master_otp"]) == 6
        assert order["can_cancel"] is True

@pytest.mark.asyncio
async def test_two_minute_cancellation_and_immediate_refund(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        shops_res = await client.get("/api/shops")
        item = (await client.get(f"/api/shops/{shops_res.json()[0]['id']}")).json()["items"][0]

        payload = {
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "tower": "Tower A",
            "floor": 3,
            "desk_location": "Desk A-301"
        }
        create_res = await client.post("/api/orders?user_id=1", json=payload)
        order = create_res.json()
        order_id = order["id"]

        # Cancel immediately within 2 minutes
        cancel_res = await client.post(
            f"/api/orders/{order_id}/cancel?user_id=1",
            json={"reason": "Ordered wrong item by mistake"}
        )
        assert cancel_res.status_code == 200
        data = cancel_res.json()
        assert data["success"] is True
        assert data["refund_amount"] == order["grand_total"]

        # Duplicate cancellation attempt -> must be rejected
        dup_cancel_res = await client.post(
            f"/api/orders/{order_id}/cancel?user_id=1",
            json={"reason": "Second attempt"}
        )
        assert dup_cancel_res.status_code == 400
        assert "already cancelled" in dup_cancel_res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_cancellation_expired_after_two_minutes(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        item = (await client.get("/api/shops/1")).json()["items"][0]
        create_res = await client.post("/api/orders?user_id=1", json={
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "tower": "Tower B",
            "floor": 6,
            "desk_location": "Desk B-612"
        })
        order = create_res.json()
        order_id = order["id"]

        # Simulate time travel: set cancellation_deadline to 5 minutes ago in database
        async with async_test_db() as session:
            db_order = await session.get(MasterOrder, order_id)
            db_order.cancellation_deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
            await session.commit()

        # Cancellation attempt past 2 minutes -> must be rejected by server
        late_cancel_res = await client.post(
            f"/api/orders/{order_id}/cancel?user_id=1",
            json={"reason": "Late cancellation"}
        )
        assert late_cancel_res.status_code == 400
        assert "expired" in late_cancel_res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_partial_shop_rejection_and_item_refund(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create multi-item order
        shops_res = await client.get("/api/shops")
        detail = (await client.get(f"/api/shops/{shops_res.json()[0]['id']}")).json()
        item1 = detail["items"][0]
        item2 = detail["items"][1]

        create_res = await client.post("/api/orders?user_id=1", json={
            "items": [
                {"menu_item_id": item1["id"], "quantity": 1},
                {"menu_item_id": item2["id"], "quantity": 1}
            ],
            "tower": "Tower B",
            "floor": 6,
            "desk_location": "Desk B-612"
        })
        order = create_res.json()
        initial_grand_total = order["grand_total"]
        order_item_id = order["vendor_orders"][0]["order_items"][0]["id"]
        rejected_subtotal = order["vendor_orders"][0]["order_items"][0]["subtotal"]

        # Admin partial item rejection (e.g., bun maska out of bread)
        reject_res = await client.post(
            f"/api/admin/orders/items/{order_item_id}/reject",
            json={"reason": "Fresh bread out of stock at shop"}
        )
        assert reject_res.status_code == 200
        data = reject_res.json()
        assert data["refunded_amount"] == rejected_subtotal

        # Check master order is now PARTIALLY_REFUNDED with revised grand total
        updated_order = (await client.get(f"/api/orders/{order['id']}")).json()
        assert updated_order["status"] == "PARTIALLY_REFUNDED"
        assert updated_order["grand_total"] == initial_grand_total - rejected_subtotal

        # Duplicate rejection of the same item -> must fail
        dup_reject_res = await client.post(
            f"/api/admin/orders/items/{order_item_id}/reject",
            json={"reason": "Second rejection"}
        )
        assert dup_reject_res.status_code == 400
        assert "already marked as rejected" in dup_reject_res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_prepaid_balance_exhaustion_blocks_order(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Find a prepaid shop (e.g. Subway, id=2)
        shops_res = (await client.get("/api/shops")).json()
        prepaid_shop = next(s for s in shops_res if s["settlement_type"] == "PREPAID")
        item = (await client.get(f"/api/shops/{prepaid_shop['id']}")).json()["items"][0]

        # Drain prepaid balance down to ₹10 in database
        async with async_test_db() as session:
            account = await session.execute(
                select(ShopPrepaidAccount).where(ShopPrepaidAccount.shop_id == prepaid_shop["id"])
            )
            acc = account.scalar_one()
            acc.current_balance = Decimal("10.00")
            acc.is_low_balance_alerted = True
            await session.commit()

        # Attempt to place order worth > ₹10 (item price ~₹200) -> must be rejected
        fail_res = await client.post("/api/orders?user_id=1", json={
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "tower": "Tower B",
            "floor": 6,
            "desk_location": "Desk B-612"
        })
        assert fail_res.status_code == 400
        assert "prepaid balance requirement" in fail_res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_mandatory_photo_and_otp_delivery_verification(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        item = (await client.get("/api/shops/1")).json()["items"][0]
        create_res = await client.post("/api/orders?user_id=1", json={
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "tower": "Tower B",
            "floor": 6,
            "desk_location": "Desk B-612"
        })
        order = create_res.json()
        order_id = order["id"]
        correct_otp = order["master_otp"]
        vo_id = order["vendor_orders"][0]["id"]

        # 1. Attempt delivery BEFORE picking up package at shop -> must fail
        premature_res = await client.post("/api/delivery/complete?partner_id=1", json={
            "master_order_id": order_id,
            "entered_otp": correct_otp,
            "photo_data": "data:image/jpeg;base64,camera_desk_capture_sample_test"
        })
        assert premature_res.status_code == 400
        assert "incomplete pickups" in premature_res.json()["detail"].lower()

        # 2. Pick up package at shop
        pickup_res = await client.post("/api/delivery/pickup-confirm", json={"vendor_order_id": vo_id})
        assert pickup_res.status_code == 200

        # 3. Unauthorized runner attempt (partner_id=99) -> must fail
        unauth_runner_res = await client.post("/api/delivery/complete?partner_id=99", json={
            "master_order_id": order_id,
            "entered_otp": correct_otp,
            "photo_data": "data:image/jpeg;base64,camera_desk_capture_sample_test"
        })
        assert unauth_runner_res.status_code == 403

        # 4. Attempt completion with WRONG OTP -> must fail and increment attempt count
        fail_otp_res = await client.post("/api/delivery/complete?partner_id=1", json={
            "master_order_id": order_id,
            "entered_otp": "999999",
            "photo_data": "data:image/jpeg;base64,camera_desk_capture_sample_test"
        })
        assert fail_otp_res.status_code == 400
        assert "Invalid OTP" in fail_otp_res.json()["detail"]

        # 5. Attempt completion with MISSING PHOTO -> must fail
        fail_photo_res = await client.post("/api/delivery/complete?partner_id=1", json={
            "master_order_id": order_id,
            "entered_otp": correct_otp,
            "photo_data": ""
        })
        assert fail_photo_res.status_code == 400
        assert "Mandatory desk delivery photograph is missing" in fail_photo_res.json()["detail"]

        # 6. Successful completion with BOTH photo AND correct OTP
        success_res = await client.post("/api/delivery/complete?partner_id=1", json={
            "master_order_id": order_id,
            "entered_otp": correct_otp,
            "photo_data": "data:image/jpeg;base64,valid_desk_camera_photograph_stream_bytes_proof"
        })
        assert success_res.status_code == 200
        assert success_res.json()["success"] is True

        # Check order is marked DELIVERED
        order_check = (await client.get(f"/api/orders/{order_id}")).json()
        assert order_check["status"] == "DELIVERED"

@pytest.mark.asyncio
async def test_razorpay_webhook_hmac_and_idempotency(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create test order
        item = (await client.get("/api/shops/1")).json()["items"][0]
        create_res = await client.post("/api/orders?user_id=1", json={
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
            "tower": "Tower B",
            "floor": 6,
            "desk_location": "Desk B-612"
        })
        order = create_res.json()
        gateway_order_id = f"order_mock_{order['id']}"

        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_test_{order['id']}",
                        "order_id": gateway_order_id,
                        "amount": int(order["grand_total"] * 100),
                        "status": "captured"
                    }
                }
            }
        }
        raw_body = json.dumps(webhook_payload).encode("utf-8")
        secret = "atdesk_razorpay_webhook_secret_key_2026"
        valid_signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        # 1. Invalid signature -> rejected
        invalid_res = await client.post(
            "/api/payments/webhook",
            content=raw_body,
            headers={"X-Razorpay-Signature": "wrong_signature_12345", "Content-Type": "application/json"}
        )
        assert invalid_res.status_code == 400

        # 2. Valid signature -> accepted
        valid_res = await client.post(
            "/api/payments/webhook",
            content=raw_body,
            headers={"X-Razorpay-Signature": valid_signature, "Content-Type": "application/json"}
        )
        assert valid_res.status_code == 200
        assert valid_res.json()["status"] == "ok"

        # 3. Duplicate webhook -> idempotently ignored
        dup_res = await client.post(
            "/api/payments/webhook",
            content=raw_body,
            headers={"X-Razorpay-Signature": valid_signature, "Content-Type": "application/json"}
        )
        assert dup_res.status_code == 200
        assert "Duplicate event ignored" in dup_res.json()["message"]

@pytest.mark.asyncio
async def test_rbac_order_history_privacy(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register a second employee (User 2)
        reg_res = await client.post("/api/auth/register-employee", json={
            "phone": "+919999988888",
            "full_name": "Rohan Mehra",
            "email": "rohan@company.com",
            "company_name": "Acme Corp",
            "tower": "Tower C",
            "floor": 4,
            "desk_location": "Desk C-404"
        })
        assert reg_res.status_code == 200
        token_other = reg_res.json()["access_token"]

        token_aarav = create_access_token({"sub": "1", "phone": "+919876543210", "role": "EMPLOYEE"})

        # Rohan tries to access Aarav's orders -> rejected with 403 Forbidden
        unauth_res = await client.get(
            "/api/orders/user/1",
            headers={"Authorization": f"Bearer {token_other}"}
        )
        assert unauth_res.status_code == 403
        assert "Forbidden" in unauth_res.json()["detail"]

        # Aarav accesses his own orders -> allowed
        auth_res = await client.get(
            "/api/orders/user/1",
            headers={"Authorization": f"Bearer {token_aarav}"}
        )
        assert auth_res.status_code == 200

@pytest.mark.asyncio
async def test_admin_menu_price_audit_log(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "new_price": 125.0,
            "reason": "Wholesale raw ingredient cost adjustment",
            "admin_id": "operations@thesortedclub.com"
        }
        res = await client.post("/api/admin/menu/price-update?item_id=1", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["new_price"] == 125.0

        logs_res = await client.get("/api/admin/audit-logs")
        logs = logs_res.json()
        assert any(l["action"] == "MENU_PRICE_UPDATE" for l in logs)

@pytest.mark.asyncio
async def test_admin_settlement_and_prepaid_ledger(async_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        prepaid_res = await client.get("/api/admin/prepaid-accounts")
        assert prepaid_res.status_code == 200
        prepaid_list = prepaid_res.json()
        assert len(prepaid_list) > 0
        first_shop = prepaid_list[0]

        topup_res = await client.post("/api/admin/prepaid/topup", json={
            "shop_id": first_shop["shop_id"],
            "amount": 2500.0,
            "reference_id": "BANK-UTR-998877",
            "notes": "Weekly advance deposit"
        })
        assert topup_res.status_code == 200
        assert topup_res.json()["new_balance"] == first_shop["current_balance"] + 2500.0

        ledger_res = await client.get(f"/api/admin/prepaid-accounts/{first_shop['shop_id']}/ledger")
        entries = ledger_res.json()
        assert any(e["reference_id"] == "BANK-UTR-998877" for e in entries)
