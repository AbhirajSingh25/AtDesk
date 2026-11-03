import pytest
import pytest_asyncio
import asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.models.models import (
    Shop, ShopPrepaidAccount, ShopPrepaidLedger, MasterOrder, VendorOrder,
    MasterOrderStatus, VendorOrderStatus, SettlementType
)
from backend.app.services.finance_service import FinanceService
from backend.app.services.order_service import OrderService

POSTGRES_TEST_URL = "postgresql+asyncpg://postgres:atdesk_staging@127.0.0.1:5433/atdesk_staging"

@pytest_asyncio.fixture(scope="function")
async def pg_session():
    engine = create_async_engine(POSTGRES_TEST_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_postgresql_row_locking_concurrency(pg_session):
    """
    CRITICAL AUDIT TEST:
    Verifies PostgreSQL row-level locking (SELECT ... FOR UPDATE) during simultaneous prepaid deductions.
    Launches 5 concurrent tasks attempting to debit ₹300 each from a shop with ₹800 balance.
    Exactly 2 must succeed (2 * 300 = 600 <= 800), and the remaining 3 must fail due to insufficient funds.
    Balance after must be exactly ₹200. Overdrafting below 0 is physically prevented by PostgreSQL row locking!
    """
    # 1. Setup isolated test shop with prepaid account of ₹800
    shop = Shop(
        name="Concurrency Test Kitchen",
        slug=f"concurrency-test-{int(asyncio.get_event_loop().time() * 1000)}",
        category="Food",
        location_details="JMD Megapolis Plaza",
        phone="+919800000000",
        is_open=True,
        prep_lead_time_mins=10,
        settlement_type=SettlementType.PREPAID
    )
    pg_session.add(shop)
    await pg_session.flush()

    account = ShopPrepaidAccount(
        shop_id=shop.id,
        current_balance=Decimal("800.00"),
        min_threshold_alert=Decimal("200.00"),
        is_low_balance_alerted=False
    )
    pg_session.add(account)
    await pg_session.commit()

    shop_id = shop.id
    debit_amount = Decimal("300.00")

    # 2. Worker function creating its own independent async database session
    engine = create_async_engine(POSTGRES_TEST_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def concurrent_debit_worker(worker_id: int):
        async with session_factory() as worker_session:
            async with worker_session.begin():
                success = await FinanceService.debit_prepaid_for_order(
                    db=worker_session,
                    shop_id=shop_id,
                    amount=debit_amount,
                    vendor_order_id=worker_id + 10000
                )
                return success

    # 3. Launch 5 simultaneous concurrent debit operations
    tasks = [concurrent_debit_worker(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    # 4. Verify results
    successful_debits = [r for r in results if r is True]
    rejected_debits = [r for r in results if r is False]

    assert len(successful_debits) == 2, f"Expected exactly 2 debits to succeed, got {len(successful_debits)}"
    assert len(rejected_debits) == 3, f"Expected 3 debits to fail due to insufficient funds, got {len(rejected_debits)}"

    # 5. Check final balance in PostgreSQL database
    async with session_factory() as verify_session:
        acc = await verify_session.execute(
            select(ShopPrepaidAccount).where(ShopPrepaidAccount.shop_id == shop_id)
        )
        final_account = acc.scalar_one()
        assert final_account.current_balance == Decimal("200.00"), f"Balance must be exactly 200, got {final_account.current_balance}"

        # Check ledger rows
        ledger_res = await verify_session.execute(
            select(ShopPrepaidLedger).where(ShopPrepaidLedger.shop_id == shop_id)
        )
        entries = ledger_res.scalars().all()
        assert len(entries) == 2, f"Expected exactly 2 ledger debit entries, got {len(entries)}"

    await engine.dispose()

@pytest.mark.asyncio
async def test_postgresql_transaction_rollback_on_error(pg_session):
    """
    Verifies that when an error occurs halfway through multi-shop order creation,
    PostgreSQL transaction rollback leaves zero orphan child vendor orders or dirty records.
    """
    # Create invalid order with non-existent menu item to trigger rollback
    with pytest.raises(Exception):
        await OrderService.create_multi_shop_order(
            db=pg_session,
            user_id=1,
            cart_items=[{"menu_item_id": 999999, "quantity": 1}],
            tower="Tower A",
            floor=5,
            desk_location="Desk A-505"
        )

    # Verify no master orders were left in dirty state
    res = await pg_session.execute(
        select(MasterOrder).where(MasterOrder.desk_location == "Desk A-505")
    )
    assert res.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_postgresql_daily_settlement_reconciliation(pg_session):
    """
    Verifies PostgreSQL daily settlement generation and exclusion of already settled vendor orders.
    """
    shop_res = await pg_session.execute(
        select(Shop).where(Shop.settlement_type == SettlementType.DAILY)
    )
    daily_shop = shop_res.scalars().first()
    assert daily_shop is not None

    # Clear any previous test settlement for idempotency
    from sqlalchemy import delete
    from backend.app.models.models import ShopSettlement
    await pg_session.execute(
        delete(ShopSettlement).where(
            ShopSettlement.shop_id == daily_shop.id,
            ShopSettlement.settlement_date == "2026-11-03"
        )
    )
    await pg_session.commit()

    settlement = await FinanceService.generate_daily_settlement(
        db=pg_session,
        shop_id=daily_shop.id,
        settlement_date="2026-11-03"
    )
    await pg_session.commit()
    assert settlement is not None
    assert settlement.status.value == "DRAFT"
    assert settlement.total_payable >= Decimal("0.00")

    # Duplicate settlement generation on same date should return None
    dup_settlement = await FinanceService.generate_daily_settlement(
        db=pg_session,
        shop_id=daily_shop.id,
        settlement_date="2026-11-03"
    )
    assert dup_settlement is None

