import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, 
    Text, Enum, Index, Numeric
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class UserRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    DELIVERY_PARTNER = "DELIVERY_PARTNER"
    ADMIN = "ADMIN"
    FINANCE = "FINANCE"

class MasterOrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    PICKING_UP = "PICKING_UP"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"

class VendorOrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    PICKED_UP = "PICKED_UP"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"

class SettlementType(str, enum.Enum):
    DAILY = "DAILY"
    PREPAID = "PREPAID"

class SettlementStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    PAID = "PAID"

class RefundStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PROCESSED = "PROCESSED"
    REJECTED = "REJECTED"

class ShopOnboardingStatus(str, enum.Enum):
    SEED = "SEED"
    CONFIGURED = "CONFIGURED"
    CONTACTED = "CONTACTED"
    CONTRACTED = "CONTRACTED"
    OPERATIONALLY_VERIFIED = "OPERATIONALLY_VERIFIED"

# 1. Users
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    employee_profile = relationship("EmployeeProfile", back_populates="user", uselist=False)
    delivery_profile = relationship("DeliveryPartner", back_populates="user", uselist=False)
    master_orders = relationship("MasterOrder", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

# 2. Employee Profile
class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    company_name = Column(String(100), nullable=False)
    tower = Column(String(50), nullable=False)  # Tower A, B, C, D at JMD Megapolis
    floor = Column(Integer, nullable=False)
    desk_location = Column(String(100), nullable=False)
    official_id_verified = Column(Boolean, default=True)

    user = relationship("User", back_populates="employee_profile")

# 3. Delivery Partner Profile
class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    vehicle_number = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    battery_percentage = Column(Integer, default=95)
    last_active_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="delivery_profile")
    assignments = relationship("DeliveryAssignment", back_populates="partner")

# 4. Shops
class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    image_url = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False)  # Food, Beverages, Snacks, Essentials
    location_details = Column(String(100), default="Ground Floor, Central Plaza, JMD Megapolis")
    phone = Column(String(20), nullable=False)
    is_open = Column(Boolean, default=True)
    prep_lead_time_mins = Column(Integer, default=12)
    settlement_type = Column(Enum(SettlementType), default=SettlementType.DAILY, nullable=False)
    
    # Commercial Onboarding & Partnership Verification
    onboarding_status = Column(Enum(ShopOnboardingStatus), default=ShopOnboardingStatus.CONFIGURED, nullable=False)
    owner_permission_verified = Column(Boolean, default=False)
    contract_signed = Column(Boolean, default=False)
    kitchen_prep_audited = Column(Boolean, default=False)
    packaging_standard_verified = Column(Boolean, default=False)
    official_business_partner = Column(Boolean, default=False)
    onboarding_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utcnow)

    categories = relationship("MenuCategory", back_populates="shop")
    items = relationship("MenuItem", back_populates="shop")
    prepaid_account = relationship("ShopPrepaidAccount", back_populates="shop", uselist=False)
    vendor_orders = relationship("VendorOrder", back_populates="shop")
    settlements = relationship("ShopSettlement", back_populates="shop")
    menu_versions = relationship("MenuVersion", back_populates="shop")

# 5. Shop Operating Hours
class ShopOperatingHour(Base):
    __tablename__ = "shop_operating_hours"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    open_time = Column(String(10), default="09:00")
    close_time = Column(String(10), default="21:00")
    is_closed = Column(Boolean, default=False)

# 6. Menu Categories
class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=0)

    shop = relationship("Shop", back_populates="categories")
    items = relationship("MenuItem", back_populates="category")

# 7. Menu Items
class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("menu_categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    portion_size = Column(String(50), nullable=True)  # e.g., "Regular (250ml)", "Serves 1"
    image_url = Column(String(255), nullable=True)
    is_food = Column(Boolean, default=True)  # True for food, False for compact essentials
    dietary = Column(String(20), default="VEG")  # VEG, NON_VEG, EGG, NONE
    prep_time_mins = Column(Integer, default=10)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    shop = relationship("Shop", back_populates="items")
    category = relationship("MenuCategory", back_populates="items")
    audit_logs = relationship("MenuPriceAuditLog", back_populates="menu_item")

# 8. Menu Versions
class MenuVersion(Base):
    __tablename__ = "menu_versions"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    version_num = Column(Integer, nullable=False)
    notes = Column(String(255), nullable=True)
    created_by = Column(String(100), default="Admin")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    shop = relationship("Shop", back_populates="menu_versions")

# 9. Menu Price Audit Log
class MenuPriceAuditLog(Base):
    __tablename__ = "menu_price_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False)
    old_price = Column(Numeric(10, 2), nullable=False)
    new_price = Column(Numeric(10, 2), nullable=False)
    admin_id = Column(String(100), nullable=False)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    menu_item = relationship("MenuItem", back_populates="audit_logs")

# 10. Master Orders
class MasterOrder(Base):
    __tablename__ = "master_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(30), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status = Column(Enum(MasterOrderStatus), default=MasterOrderStatus.CREATED, nullable=False)
    
    # Destination in JMD Megapolis
    tower = Column(String(50), nullable=False)
    floor = Column(Integer, nullable=False)
    desk_location = Column(String(100), nullable=False)
    delivery_instructions = Column(String(255), nullable=True)
    
    # Pricing
    items_subtotal = Column(Numeric(10, 2), nullable=False)
    flat_delivery_fee = Column(Numeric(10, 2), default=25.00, nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    grand_total = Column(Numeric(10, 2), nullable=False)
    
    # Payment & Fraud Security
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    master_otp = Column(String(10), nullable=False)  # 6-digit OTP given to customer
    cancellation_deadline = Column(DateTime(timezone=True), nullable=False)  # now + 120 sec
    scheduled_window = Column(String(100), nullable=True)  # e.g., "13:00 - 13:30"
    
    # Environment & Audit Classification
    transaction_mode = Column(String(20), default="TEST_SANDBOX", nullable=False)  # SEED, TEST_SANDBOX, PILOT_LIVE
    
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="master_orders")
    vendor_orders = relationship("VendorOrder", back_populates="master_order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="master_order")
    refunds = relationship("Refund", back_populates="master_order")
    assignment = relationship("DeliveryAssignment", back_populates="master_order", uselist=False)
    proofs = relationship("DeliveryProof", back_populates="master_order")
    eta_snapshots = relationship("EtaSnapshot", back_populates="master_order")
    unit_economics = relationship("OrderUnitEconomics", back_populates="master_order", uselist=False, cascade="all, delete-orphan")

# 11. Vendor (Child) Orders
class VendorOrder(Base):
    __tablename__ = "vendor_orders"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), nullable=False)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="RESTRICT"), nullable=False)
    shop_subtotal = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(VendorOrderStatus), default=VendorOrderStatus.PENDING, nullable=False)
    estimated_prep_time_mins = Column(Integer, default=12)
    pickup_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    master_order = relationship("MasterOrder", back_populates="vendor_orders")
    shop = relationship("Shop", back_populates="vendor_orders")
    order_items = relationship("OrderItem", back_populates="vendor_order", cascade="all, delete-orphan")

# 12. Order Items
class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    vendor_order_id = Column(Integer, ForeignKey("vendor_orders.id", ondelete="CASCADE"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True)
    item_name = Column(String(150), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    is_rejected = Column(Boolean, default=False)
    rejection_reason = Column(String(255), nullable=True)

    vendor_order = relationship("VendorOrder", back_populates="order_items")

# 13. Payments
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), nullable=False)
    gateway_order_id = Column(String(100), nullable=True)
    gateway_payment_id = Column(String(100), nullable=True)
    payment_method = Column(String(50), default="UPI")
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PAID, nullable=False)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    master_order = relationship("MasterOrder", back_populates="payments")
    events = relationship("PaymentEvent", back_populates="payment")

# 14. Payment Events
class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)  # e.g., "PAYMENT_CAPTURED", "PAYMENT_FAILED"
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    payment = relationship("Payment", back_populates="events")

# 15. Refunds
class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), nullable=False)
    vendor_order_id = Column(Integer, ForeignKey("vendor_orders.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(String(255), nullable=False)
    status = Column(Enum(RefundStatus), default=RefundStatus.APPROVED, nullable=False)
    approved_by = Column(String(100), default="System")
    gateway_refund_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    master_order = relationship("MasterOrder", back_populates="refunds")

# 16. Shop Settlements (Daily Model)
class ShopSettlement(Base):
    __tablename__ = "shop_settlements"

    id = Column(Integer, primary_key=True, index=True)
    settlement_reference = Column(String(50), unique=True, index=True, nullable=False)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="RESTRICT"), nullable=False)
    settlement_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    total_payable = Column(Numeric(10, 2), nullable=False)
    order_count = Column(Integer, default=1)
    status = Column(Enum(SettlementStatus), default=SettlementStatus.DRAFT, nullable=False)
    finance_approved_by = Column(String(100), nullable=True)
    payout_utr_ref = Column(String(100), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    shop = relationship("Shop", back_populates="settlements")
    items = relationship("SettlementItem", back_populates="settlement")

# 17. Settlement Items
class SettlementItem(Base):
    __tablename__ = "settlement_items"

    id = Column(Integer, primary_key=True, index=True)
    settlement_id = Column(Integer, ForeignKey("shop_settlements.id", ondelete="CASCADE"), nullable=False)
    vendor_order_id = Column(Integer, ForeignKey("vendor_orders.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)

    settlement = relationship("ShopSettlement", back_populates="items")

# 18. Shop Prepaid Accounts (Prepaid Balance Model)
class ShopPrepaidAccount(Base):
    __tablename__ = "shop_prepaid_accounts"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), unique=True, nullable=False)
    current_balance = Column(Numeric(10, 2), default=0.00, nullable=False)
    min_threshold_alert = Column(Numeric(10, 2), default=1500.00, nullable=False)
    is_low_balance_alerted = Column(Boolean, default=False)
    last_topped_up_at = Column(DateTime(timezone=True), default=utcnow)

    shop = relationship("Shop", back_populates="prepaid_account")
    ledger_entries = relationship("ShopPrepaidLedger", back_populates="account")

# 19. Shop Prepaid Ledger (Immutable transactions)
class ShopPrepaidLedger(Base):
    __tablename__ = "shop_prepaid_ledger"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("shop_prepaid_accounts.id", ondelete="CASCADE"), nullable=False)
    transaction_type = Column(String(30), nullable=False)  # CREDIT_TOPUP, DEBIT_ORDER, REVERSAL_REFUND
    amount = Column(Numeric(10, 2), nullable=False)
    balance_after = Column(Numeric(10, 2), nullable=False)
    reference_id = Column(String(100), nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    account = relationship("ShopPrepaidAccount", back_populates="ledger_entries")

# 20. Delivery Assignments
class DeliveryAssignment(Base):
    __tablename__ = "delivery_assignments"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    delivery_partner_id = Column(Integer, ForeignKey("delivery_partners.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(30), default="ASSIGNED")  # ASSIGNED, EN_ROUTE_PICKUP, PICKED_ALL, ARRIVED_TOWER, DELIVERED
    assigned_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    master_order = relationship("MasterOrder", back_populates="assignment")
    partner = relationship("DeliveryPartner", back_populates="assignments")

# 21. Delivery Events
class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), nullable=False)
    delivery_partner_id = Column(Integer, ForeignKey("delivery_partners.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

# 22. Delivery Proofs (Desk Photo + GPS)
class DeliveryProof(Base):
    __tablename__ = "delivery_proofs"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), nullable=False)
    delivery_partner_id = Column(Integer, ForeignKey("delivery_partners.id", ondelete="CASCADE"), nullable=False)
    photo_url = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    captured_at = Column(DateTime(timezone=True), default=utcnow)

    master_order = relationship("MasterOrder", back_populates="proofs")

# 23. Delivery OTP Records
class DeliveryOtpRecord(Base):
    __tablename__ = "delivery_otp_records"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), nullable=False)
    entered_otp = Column(String(10), nullable=False)
    is_verified = Column(Boolean, default=False)
    attempts_count = Column(Integer, default=1)
    verified_at = Column(DateTime(timezone=True), default=utcnow)

# 24. Delivery Location Events (Live runner tracking during active assignment)
class DeliveryLocationEvent(Base):
    __tablename__ = "delivery_location_events"

    id = Column(Integer, primary_key=True, index=True)
    delivery_partner_id = Column(Integer, ForeignKey("delivery_partners.id", ondelete="CASCADE"), nullable=False)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=utcnow)

# 25. Notifications
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="notifications")

# 26. Support Tickets (Customer & Delivery Disputes)
class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    issue_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(30), default="OPEN")  # OPEN, RESOLVED, CLOSED
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

# 27. Security & Audit Logs
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True)
    role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)  # e.g., "PRICE_UPDATE", "SETTLEMENT_PAYOUT", "ORDER_CANCELLED"
    target_entity = Column(String(50), nullable=False)
    target_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), default="127.0.0.1")
    created_at = Column(DateTime(timezone=True), default=utcnow)

# 28. Dynamic ETA Snapshots
class EtaSnapshot(Base):
    __tablename__ = "eta_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), nullable=False)
    calculated_min_mins = Column(Integer, nullable=False)
    calculated_max_mins = Column(Integer, nullable=False)
    estimated_delivery_time = Column(DateTime(timezone=True), nullable=False)
    factors_breakdown = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    master_order = relationship("MasterOrder", back_populates="eta_snapshots")

# 29. Scheduled Orders
class ScheduledOrder(Base):
    __tablename__ = "scheduled_orders"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), nullable=False)
    scheduled_date = Column(String(20), nullable=False)
    time_slot = Column(String(50), nullable=False)  # e.g., "13:00 - 13:30"
    capacity_reserved = Column(Integer, default=1)
    is_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

# 30. Order Unit Economics (Commercial Pilot Margin Tracking)
class OrderUnitEconomics(Base):
    __tablename__ = "order_unit_economics"

    id = Column(Integer, primary_key=True, index=True)
    master_order_id = Column(Integer, ForeignKey("master_orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    gross_customer_payment = Column(Numeric(10, 2), nullable=False)
    food_subtotal = Column(Numeric(10, 2), nullable=False)
    delivery_fee_collected = Column(Numeric(10, 2), default=25.00, nullable=False)
    shop_payable = Column(Numeric(10, 2), nullable=False)
    gateway_fee = Column(Numeric(10, 2), nullable=False)  # 2.36% (Razorpay 2% + 18% GST)
    runner_payout = Column(Numeric(10, 2), default=18.00, nullable=False)  # Targeted ₹18/drop
    packaging_cost = Column(Numeric(10, 2), default=3.50, nullable=False)  # Branded bag & security seal
    refund_deduction = Column(Numeric(10, 2), default=0.00, nullable=False)
    contribution_margin = Column(Numeric(10, 2), nullable=False)
    contribution_margin_pct = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    master_order = relationship("MasterOrder", back_populates="unit_economics")
