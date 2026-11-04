import asyncio
import asyncpg
import os
import subprocess

async def test_clean_migration():
    sys_conn = await asyncpg.connect('postgresql://postgres:atdesk_staging@127.0.0.1:5433/postgres')
    await sys_conn.execute('DROP DATABASE IF EXISTS atdesk_migration_test;')
    await sys_conn.execute('CREATE DATABASE atdesk_migration_test;')
    await sys_conn.close()
    
    env = os.environ.copy()
    env['DATABASE_URL'] = 'postgresql+asyncpg://postgres:atdesk_staging@127.0.0.1:5433/atdesk_migration_test'
    env['PYTHONPATH'] = '.'
    
    # Run alembic upgrade head
    res = subprocess.run(['py', '-3.11', '-m', 'alembic', 'upgrade', 'head'], env=env, capture_output=True, text=True)
    print('Alembic returncode:', res.returncode)
    print('Stdout:', res.stdout)
    if res.stderr:
        print('Stderr:', res.stderr)
    assert res.returncode == 0, "Alembic migration failed on clean database!"
        
    test_conn = await asyncpg.connect('postgresql://postgres:atdesk_staging@127.0.0.1:5433/atdesk_migration_test')
    tables = await test_conn.fetch("""
        SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' ORDER BY tablename;
    """)
    print(f'Migrated cleanly! Total tables created: {len(tables)}')
    table_names = [t['tablename'] for t in tables]
    print('Created tables:', table_names)
    assert 'coupons' in table_names, 'coupons missing'
    assert 'promo_banners' in table_names, 'promo_banners missing'
    assert 'shop_staff_profiles' in table_names, 'shop_staff_profiles missing'
    assert 'master_orders' in table_names, 'master_orders missing'
    assert 'alembic_version' in table_names, 'alembic_version missing'
    await test_conn.close()
    
    # Clean up
    sys_conn = await asyncpg.connect('postgresql://postgres:atdesk_staging@127.0.0.1:5433/postgres')
    await sys_conn.execute('DROP DATABASE atdesk_migration_test;')
    await sys_conn.close()
    print('SUCCESS: Clean database migration test verified and cleaned up.')

if __name__ == '__main__':
    asyncio.run(test_clean_migration())

