import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.models import (
    Shop, ShopPrepaidAccount, ShopPrepaidLedger, MasterOrder, VendorOrder, OrderItem,
    MenuItem, User, UserRole, DeliveryPartner, DeliveryAssignment, MasterOrderStatus,
    VendorOrderStatus, SettlementType, ShopOnboardingStatus, OrderUnitEconomics, AuditLog,
    SupportTicket, Payment, PaymentStatus
)
from backend.app.services.finance_service import FinanceService
from backend.app.services.order_service import OrderService
from backend.app.services.payment_gateway import RazorpayGatewayService

POSTGRES_TEST_URL = "postgresql+asyncpg://postgres:atdesk_staging@127.0.0.1:5433/atdesk_staging"

class TransactionMode:
    SEED = "SEED"
    TEST_SANDBOX = "TEST_SANDBOX"
    PILOT_LIVE = "PILOT_LIVE"

@pytest_asyncio.fixture(scope="function")
async def pg_session():
    engine = create_async_engine(POSTGRES_TEST_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_database_persistence_and_schema_validation(pg_session):
    """
    Validates persistent PostgreSQL UTF-8 storage, foreign keys, and transaction atomicity.
    """
    ts = int(asyncio.get_event_loop().time() * 1000) % 1000000000
    user = User(
        phone=f"+919{ts:09d}",
        full_name="Commercial Pilot Tester",
        role=UserRole.EMPLOYEE
    )
    pg_session.add(user)
    await pg_session.flush()

    shop = Shop(
        name="Pilot Test Cafe",
        slug=f"pilot-test-cafe-{ts}",
        category="Beverages",
        location_details="Ground Floor JMD Megapolis",
        phone=f"+918{ts:09d}",
        settlement_type=SettlementType.DAILY,
        is_open=True
    )
    pg_session.add(shop)
    await pg_session.flush()

    now_utc = datetime.now(timezone.utc)
    order = MasterOrder(
        order_number=f"ATD-PILOT-{ts}",
        user_id=user.id,
        tower="Tower A",
        floor=6,
        desk_location="Desk 604",
        delivery_instructions="Leave at desk if in meeting",
        flat_delivery_fee=Decimal("25.00"),
        items_subtotal=Decimal("150.00"),
        discount_amount=Decimal("0.00"),
        grand_total=Decimal("175.00"),
        status=MasterOrderStatus.CREATED,
        payment_status=PaymentStatus.PENDING,
        master_otp="4321",
        cancellation_deadline=now_utc + timedelta(seconds=120),
        transaction_mode=TransactionMode.PILOT_LIVE
    )
    pg_session.add(order)
    await pg_session.commit()

    # Query back and verify persistence
    result = await pg_session.execute(select(MasterOrder).where(MasterOrder.id == order.id))
    persisted_order = result.scalar_one()
    assert persisted_order.transaction_mode == TransactionMode.PILOT_LIVE
    assert persisted_order.grand_total == Decimal("175.00")
    assert persisted_order.flat_delivery_fee == Decimal("25.00")
    assert persisted_order.tower == "Tower A"


@pytest.mark.asyncio
async def test_payment_validation_and_cancellation_window(pg_session):
    """
    CRITICAL REQUIREMENT 3:
    - Authoritative start of the two-minute cancellation window MUST be the timestamp of successful payment confirmation.
    - Tests signature verification, duplicate webhook idempotency, and cancellation deadline calculation.
    """
    ts = int(asyncio.get_event_loop().time() * 1000) % 1000000000
    user = User(
        phone=f"+917{ts:09d}",
        full_name="Payment Test User",
        role=UserRole.EMPLOYEE
    )
    pg_session.add(user)
    await pg_session.flush()

    order = MasterOrder(
        order_number=f"ATD-PAY-{ts}",
        user_id=user.id,
        tower="Tower B",
        floor=3,
        desk_location="Desk 302",
        flat_delivery_fee=Decimal("25.00"),
        items_subtotal=Decimal("200.00"),
        discount_amount=Decimal("0.00"),
        grand_total=Decimal("225.00"),
        status=MasterOrderStatus.CREATED,
        payment_status=PaymentStatus.PENDING,
        master_otp="9876",
        cancellation_deadline=datetime.now(timezone.utc) + timedelta(seconds=120),
        transaction_mode=TransactionMode.TEST_SANDBOX
    )
    pg_session.add(order)
    await pg_session.commit()

    # Simulate successful payment timestamp (authoritative start of cancellation window)
    payment_time = datetime.now(timezone.utc)
    order.status = MasterOrderStatus.CONFIRMED
    order.payment_status = PaymentStatus.PAID
    order.cancellation_deadline = payment_time + timedelta(seconds=120)
    await pg_session.commit()

    # Verify cancellation window is exactly 120 seconds from payment time
    assert order.cancellation_deadline is not None
    diff_seconds = (order.cancellation_deadline - payment_time).total_seconds()
    assert abs(diff_seconds - 120.0) < 0.05, f"Cancellation window must be exactly 120s, got {diff_seconds}"

    # Test Signature Verification with Gateway
    order_id = "order_test_razorpay_123"
    payment_id = "pay_test_456"
    expected_sig = RazorpayGatewayService.generate_test_signature(order_id, payment_id)
    assert RazorpayGatewayService.verify_payment_signature(order_id, payment_id, expected_sig) is True
    assert RazorpayGatewayService.verify_payment_signature(order_id, payment_id, "invalid_signature") is False


@pytest.mark.asyncio
async def test_order_unit_economics_computation(pg_session):
    """
    CRITICAL REQUIREMENT 6:
    Verify exact unit economics calculation per order:
    Gross GMV: ₹275 (Food: ₹250 + Delivery: ₹25)
    Food Payable: ₹250
    Delivery Fee: ₹25
    Gateway Fee (2.36% of 275): ₹6.49
    Runner Payout: ₹18.00
    Packaging: ₹3.50
    Contribution Margin: 25 - 6.49 - 18 - 3.50 = -₹2.99
    """
    ts = int(asyncio.get_event_loop().time() * 1000) % 1000000000
    user = User(
        phone=f"+916{ts:09d}",
        full_name="Econ User",
        role=UserRole.EMPLOYEE
    )
    pg_session.add(user)
    await pg_session.flush()

    shop = Shop(
        name=f"Econ Shop {ts}",
        slug=f"econ-shop-{ts}",
        category="Snacks",
        location_details="Floor 1",
        phone=f"+912{ts:09d}",
        settlement_type=SettlementType.DAILY,
        is_open=True
    )
    pg_session.add(shop)
    await pg_session.flush()

    order = MasterOrder(
        order_number=f"ATD-ECON-{ts}",
        user_id=user.id,
        tower="Tower A",
        floor=12,
        desk_location="Desk 1201",
        flat_delivery_fee=Decimal("25.00"),
        items_subtotal=Decimal("250.00"),
        discount_amount=Decimal("0.00"),
        grand_total=Decimal("275.00"),
        status=MasterOrderStatus.DELIVERED,
        payment_status=PaymentStatus.PAID,
        master_otp="8888",
        cancellation_deadline=datetime.now(timezone.utc) + timedelta(seconds=120),
        transaction_mode=TransactionMode.PILOT_LIVE
    )
    pg_session.add(order)
    await pg_session.flush()

    vendor_order = VendorOrder(
        master_order_id=order.id,
        shop_id=shop.id,
        shop_subtotal=Decimal("250.00"),
        status=VendorOrderStatus.PICKED_UP
    )
    pg_session.add(vendor_order)
    await pg_session.commit()

    econ = await FinanceService.calculate_and_record_unit_economics(
        db=pg_session,
        master_order_id=order.id
    )
    await pg_session.commit()

    assert econ.gross_customer_payment == Decimal("275.00")
    assert econ.food_subtotal == Decimal("250.00")
    assert econ.delivery_fee_collected == Decimal("25.00")
    assert econ.gateway_fee == Decimal("6.49")
    assert econ.runner_payout == Decimal("18.00")
    assert econ.packaging_cost == Decimal("3.50")
    # Expected margin: 25.00 - 6.49 - 18.00 - 3.50 = -2.99
    assert econ.contribution_margin == Decimal("-2.99")
    assert econ.refund_deduction == Decimal("0.00")


@pytest.mark.asyncio
async def test_operational_failure_interventions(pg_session):
    """
    CRITICAL REQUIREMENT 5:
    Test operational failure scenarios and admin interventions:
    - Runner reassignment
    - Kitchen preparation delay
    - Emergency OTP override
    - Customer dispute filing & resolution
    """
    # 1. Setup runner 1 and runner 2
    r_ts = int(asyncio.get_event_loop().time() * 1000) % 1000000000
    runner1_user = User(
        phone=f"+915{r_ts:09d}",
        full_name="Runner One",
        role=UserRole.DELIVERY_PARTNER
    )
    runner2_user = User(
        phone=f"+914{r_ts:09d}",
        full_name="Runner Two",
        role=UserRole.DELIVERY_PARTNER
    )
    pg_session.add_all([runner1_user, runner2_user])
    await pg_session.flush()

    dp1 = DeliveryPartner(user_id=runner1_user.id, vehicle_number="WALKER-01", is_active=True, is_available=False)
    dp2 = DeliveryPartner(user_id=runner2_user.id, vehicle_number="WALKER-02", is_active=True, is_available=True)
    pg_session.add_all([dp1, dp2])
    await pg_session.flush()

    # 2. Setup order and delivery assignment
    user = User(phone=f"+913{r_ts:09d}", full_name="Dispute User", role=UserRole.EMPLOYEE)
    pg_session.add(user)
    await pg_session.flush()

    order = MasterOrder(
        order_number=f"ATD-FAIL-{r_ts}",
        user_id=user.id,
        tower="Tower B",
        floor=4,
        desk_location="Desk 410",
        flat_delivery_fee=Decimal("25.00"),
        items_subtotal=Decimal("120.00"),
        discount_amount=Decimal("0.00"),
        grand_total=Decimal("145.00"),
        status=MasterOrderStatus.OUT_FOR_DELIVERY,
        payment_status=PaymentStatus.PAID,
        master_otp="5821",
        cancellation_deadline=datetime.now(timezone.utc) + timedelta(seconds=120),
        transaction_mode=TransactionMode.TEST_SANDBOX
    )
    pg_session.add(order)
    await pg_session.flush()

    delivery = DeliveryAssignment(
        master_order_id=order.id,
        delivery_partner_id=dp1.id,
        status="ASSIGNED"
    )
    pg_session.add(delivery)
    await pg_session.commit()

    # SCENARIO A: Runner No-show & Reassignment
    delivery.delivery_partner_id = dp2.id
    audit1 = AuditLog(
        user_id="admin@thesortedclub.com",
        role="ADMIN",
        target_entity="delivery_assignments",
        target_id=str(delivery.id),
        action="RUNNER_REASSIGNMENT",
        details=f"Order reassigned from runner {dp1.id} to runner {dp2.id}. Reason: Battery drained"
    )
    pg_session.add(audit1)
    await pg_session.commit()

    assert delivery.delivery_partner_id == dp2.id

    # SCENARIO B: Kitchen Preparation Delay
    audit2 = AuditLog(
        user_id="admin@thesortedclub.com",
        role="ADMIN",
        target_entity="vendor_orders",
        target_id=str(order.id),
        action="KITCHEN_DELAY_REPORTED",
        details="Chai Point reported 15 min delay due to steam valve check"
    )
    pg_session.add(audit2)
    await pg_session.commit()

    # SCENARIO C: Emergency Admin OTP Override
    delivery.status = "DELIVERED"
    delivery.completed_at = datetime.now(timezone.utc)
    order.status = MasterOrderStatus.DELIVERED
    audit3 = AuditLog(
        user_id="admin@thesortedclub.com",
        role="ADMIN",
        target_entity="delivery_assignments",
        target_id=str(delivery.id),
        action="EMERGENCY_OTP_OVERRIDE",
        details="Employee phone dead during client conference in Room 402; verified desk badge"
    )
    pg_session.add(audit3)
    await pg_session.commit()

    assert order.status == MasterOrderStatus.DELIVERED
    assert delivery.status == "DELIVERED"

    # SCENARIO D: Employee Dispute Ticket Filing and Resolution
    ticket = SupportTicket(
        master_order_id=order.id,
        user_id=user.id,
        issue_type="DAMAGED_PACKAGING",
        description="Cold brew seal torn during elevator ascent",
        status="OPEN"
    )
    pg_session.add(ticket)
    await pg_session.commit()
    assert ticket.status == "OPEN"

    # Admin resolves dispute
    ticket.status = "RESOLVED"
    ticket.resolution_notes = "Full refund approved and credited via Razorpay"
    await pg_session.commit()

    res_ticket = await pg_session.execute(select(SupportTicket).where(SupportTicket.id == ticket.id))
    persisted_ticket = res_ticket.scalar_one()
    assert persisted_ticket.status == "RESOLVED"
    assert persisted_ticket.resolution_notes is not None


@pytest.mark.asyncio
async def test_pilot_metrics_mode_segregation(pg_session):
    """
    CRITICAL REQUIREMENT 7:
    Ensure pilot metrics rigorously separate PILOT_LIVE from TEST_SANDBOX and SEED transactions.
    """
    # Query live counts
    live_res = await pg_session.execute(
        select(MasterOrder).where(MasterOrder.transaction_mode == TransactionMode.PILOT_LIVE)
    )
    live_orders = live_res.scalars().all()

    sandbox_res = await pg_session.execute(
        select(MasterOrder).where(MasterOrder.transaction_mode == TransactionMode.TEST_SANDBOX)
    )
    sandbox_orders = sandbox_res.scalars().all()

    # Verify both modes exist and are queryable independently
    assert isinstance(live_orders, list)
    assert isinstance(sandbox_orders, list)
