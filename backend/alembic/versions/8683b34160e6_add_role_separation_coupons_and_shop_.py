"""add_role_separation_coupons_and_shop_staff

Revision ID: 8683b34160e6
Revises: 41f16ba5e44d
Create Date: 2026-11-04 21:29:29.040832

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8683b34160e6'
down_revision: Union[str, Sequence[str], None] = '41f16ba5e44d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include coupons, promo banners, shop staff and role separation."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # Add SHOP_STAFF to userrole enum in Postgres
    if is_postgres:
        try:
            op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SHOP_STAFF';")
        except Exception:
            pass

    # Create coupons table if not exists
    if 'coupons' not in existing_tables:
        op.create_table(
            'coupons',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('title', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('discount_type', sa.String(length=20), nullable=False, server_default='PERCENTAGE'),
            sa.Column('discount_value', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('min_order_value', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
            sa.Column('max_discount', sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
            sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code')
        )
        op.create_index(op.f('ix_coupons_code'), 'coupons', ['code'], unique=True)
        op.create_index(op.f('ix_coupons_id'), 'coupons', ['id'], unique=False)

    # Create promo_banners table if not exists
    if 'promo_banners' not in existing_tables:
        op.create_table(
            'promo_banners',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=120), nullable=False),
            sa.Column('subtitle', sa.String(length=200), nullable=True),
            sa.Column('badge', sa.String(length=50), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=False),
            sa.Column('action_type', sa.String(length=50), nullable=False, server_default='NONE'),
            sa.Column('action_target', sa.String(length=200), nullable=True),
            sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_promo_banners_id'), 'promo_banners', ['id'], unique=False)

    # Create shop_staff_profiles table if not exists
    if 'shop_staff_profiles' not in existing_tables:
        op.create_table(
            'shop_staff_profiles',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('shop_id', sa.Integer(), nullable=False),
            sa.Column('is_manager', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('can_manage_menu', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['shop_id'], ['shops.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id')
        )
        op.create_index(op.f('ix_shop_staff_profiles_id'), 'shop_staff_profiles', ['id'], unique=False)

    # Check and add columns to master_orders
    if 'master_orders' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('master_orders')]
        if 'coupon_code' not in columns:
            op.add_column('master_orders', sa.Column('coupon_code', sa.String(length=50), nullable=True))
        if 'discount_amount' not in columns:
            op.add_column('master_orders', sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'master_orders' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('master_orders')]
        if 'coupon_code' in columns:
            op.drop_column('master_orders', 'coupon_code')
        if 'discount_amount' in columns:
            op.drop_column('master_orders', 'discount_amount')

    if 'shop_staff_profiles' in existing_tables:
        op.drop_index(op.f('ix_shop_staff_profiles_id'), table_name='shop_staff_profiles')
        op.drop_table('shop_staff_profiles')

    if 'promo_banners' in existing_tables:
        op.drop_index(op.f('ix_promo_banners_id'), table_name='promo_banners')
        op.drop_table('promo_banners')

    if 'coupons' in existing_tables:
        op.drop_index(op.f('ix_coupons_id'), table_name='coupons')
        op.drop_index(op.f('ix_coupons_code'), table_name='coupons')
        op.drop_table('coupons')
