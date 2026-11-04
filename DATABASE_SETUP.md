# AtDesk Database Provisioning & Management Guide

AtDesk utilizes **PostgreSQL** with an asynchronous SQLAlchemy 2.0 object-relational layer (`asyncpg`) and **strict row-level locking (`FOR UPDATE`)** to prevent race conditions during order placement, runner assignment, and prepaid balance deductions.

---

## 1. Managed PostgreSQL Options

For production hosting, we recommend:
1. **Neon Serverless PostgreSQL:** Automatic scaling, connection pooling (PgBouncer built-in), zero cold-start latency.
2. **AWS RDS PostgreSQL (ap-south-1 Mumbai):** Lowest network latency to Gurgaon/NCR users (~15ms).
3. **Render Managed PostgreSQL:** Simple single-dashboard management if FastAPI is hosted on Render.

---

## 2. Database Schema & Tables

The database schema manages 28+ core tables:

- **Authentication & Roles:** `users`, `user_roles`, `runner_profiles`, `shop_staff_profiles`, `otps`.
- **Catalogue & Stores:** `shops`, `categories`, `menu_items`, `coupons`, `promo_banners`.
- **Order Processing:** `master_orders`, `child_orders`, `order_items`, `order_status_history`.
- **Settlement & Finance:** `daily_settlements`, `prepaid_accounts`, `prepaid_ledger_entries`, `refunds`.
- **Runner Logistics:** `runner_locations`, `delivery_assignments`, `delivery_proofs`.
- **Governance:** `audit_logs`, `supervisor_actions`.

---

## 3. Migration Procedure

Run migrations using Alembic:

```bash
# Set database URL
export DATABASE_URL="postgresql+asyncpg://user:password@host:5432/atdesk?ssl=require"

# Check migration status
alembic current

# Run all migrations up to head
alembic upgrade head
```

To create a new migration after model updates:
```bash
alembic revision --autogenerate -m "Add new column or table description"
alembic upgrade head
```

---

## 4. Connection Pooling Configuration

In `backend/app/db/session.py`, connection pool settings are tuned for high concurrency:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_recycle=300,
    pool_pre_ping=True
)
```

---

## 5. Automated Backups & Disaster Recovery

1. **Daily Snapshots:** Enable automated daily snapshots with 30-day retention on your managed provider (Neon or AWS RDS).
2. **Point-In-Time Recovery (PITR):** Neon and AWS RDS support continuous WAL archiving for point-in-time recovery up to 7 days.
3. **Manual Backup Dump:**
   ```bash
   pg_dump -h host -U user -d atdesk -F c -b -v -f atdesk_backup_$(date +%Y%m%d).dump
   ```
4. **Restore:**
   ```bash
   pg_restore -h host -U user -d atdesk -v atdesk_backup_YYYYMMDD.dump
   ```
