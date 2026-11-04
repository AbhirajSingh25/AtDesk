# AtDesk Database Provisioning & Management Guide

AtDesk utilizes **PostgreSQL** with an asynchronous SQLAlchemy 2.0 object-relational layer (`asyncpg`), Alembic for versioned schema migrations, and **strict row-level locking (`FOR UPDATE`)** to prevent race conditions during order placement, runner assignment, and prepaid balance deductions.

---

## 1. Managed PostgreSQL Providers

For production hosting:
1. **Neon Serverless PostgreSQL:** Automatic scaling, built-in PgBouncer pooling, zero cold-start latency.
2. **AWS RDS PostgreSQL (ap-south-1 Mumbai):** Lowest network latency to Gurgaon/NCR office campuses (~15ms).
3. **Render Managed PostgreSQL:** Direct internal network communication if FastAPI is deployed on Render.

---

## 2. Tested Migration Commands

Alembic is configured at both repository root (`alembic.ini`) and `backend/alembic.ini`.

### To Run Migrations Up to HEAD (Creates all 34 tables):
```bash
export DATABASE_URL="postgresql+asyncpg://<username>:<password>@<host>:5432/<database>?ssl=require"
export PYTHONPATH="."

alembic upgrade head
```

### To Check Current Migration Version:
```bash
alembic current
```

### To Inspect Migration History:
```bash
alembic history --verbose
```

---

## 3. Database Schema Overview (34 Core Tables)

The versioned migration `8683b34160e6` provisions all production entities:

- **Users & Authentication:** `users`, `user_roles`, `employee_profiles`, `delivery_partners`, `shop_staff_profiles`, `delivery_otp_records`.
- **Catalogue & Promotions:** `shops`, `menu_categories`, `menu_items`, `menu_versions`, `menu_price_audit_logs`, `coupons`, `promo_banners`.
- **Order Orchestration:** `master_orders`, `vendor_orders`, `order_items`, `order_unit_economics`, `scheduled_orders`.
- **Logistics & Delivery:** `delivery_assignments`, `delivery_events`, `delivery_location_events`, `delivery_proofs`, `eta_snapshots`.
- **Financial Ledgers & Settlements:** `payments`, `payment_events`, `refunds`, `shop_settlements`, `settlement_items`, `shop_prepaid_accounts`, `shop_prepaid_ledger`.
- **Governance:** `notifications`, `support_tickets`, `audit_logs`, `shop_operating_hours`.

---

## 4. Automated Clean Database Provisioning Verification

We executed a full verification script (`scripts/test_clean_db_migration.py`) that provisions a pristine database, runs `alembic upgrade head`, verifies table counts, and cleans up:
- Total tables created: **34**
- Return code: **0** (All DDL statements executed without warnings)
