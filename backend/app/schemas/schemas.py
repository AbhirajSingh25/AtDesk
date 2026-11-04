from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from backend.app.models.models import (
    UserRole, MasterOrderStatus, VendorOrderStatus, 
    PaymentStatus, SettlementType, SettlementStatus, RefundStatus,
    DiscountType
)

# ----------------- Auth Schemas -----------------
class OTPRequest(BaseModel):
    phone: str = Field(..., json_schema_extra={"example": "+919876543210"})

class OTPVerify(BaseModel):
    phone: str
    otp: str
    role: Optional[UserRole] = UserRole.EMPLOYEE

class EmployeeRegisterRequest(BaseModel):
    phone: str
    full_name: str
    email: Optional[str] = None
    company_name: str
    tower: str  # Tower A, B, C, D
    floor: int
    desk_location: str

class UserOut(BaseModel):
    id: int
    phone: str
    full_name: str
    email: Optional[str] = None
    role: UserRole
    company_name: Optional[str] = None
    tower: Optional[str] = None
    floor: Optional[int] = None
    desk_location: Optional[str] = None
    shop_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# ----------------- Menu & Shop Schemas -----------------
class MenuItemOut(BaseModel):
    id: int
    shop_id: int
    category_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    portion_size: Optional[str] = None
    image_url: Optional[str] = None
    is_food: bool
    dietary: str
    prep_time_mins: int
    is_available: bool
    model_config = ConfigDict(from_attributes=True)

class MenuItemCreate(BaseModel):
    shop_id: int
    category_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    portion_size: Optional[str] = "Regular"
    image_url: Optional[str] = None
    is_food: bool = True
    dietary: str = "VEG"
    prep_time_mins: int = 10
    is_available: bool = True

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    portion_size: Optional[str] = None
    image_url: Optional[str] = None
    is_food: Optional[bool] = None
    dietary: Optional[str] = None
    prep_time_mins: Optional[int] = None
    is_available: Optional[bool] = None
    reason: Optional[str] = "Menu update"

class MenuCategoryOut(BaseModel):
    id: int
    name: str
    sort_order: int
    items: List[MenuItemOut] = []
    model_config = ConfigDict(from_attributes=True)

class MenuCategoryCreate(BaseModel):
    shop_id: int
    name: str
    sort_order: int = 0

class ShopOut(BaseModel):
    id: int
    name: str
    slug: str
    image_url: Optional[str] = None
    category: str
    location_details: str
    phone: str
    is_open: bool
    prep_lead_time_mins: int
    settlement_type: SettlementType
    model_config = ConfigDict(from_attributes=True)

class ShopCreate(BaseModel):
    name: str
    slug: str
    image_url: Optional[str] = None
    category: str
    location_details: str
    phone: str
    is_open: bool = True
    prep_lead_time_mins: int = 12
    settlement_type: SettlementType = SettlementType.DAILY

class ShopUpdate(BaseModel):
    name: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    location_details: Optional[str] = None
    phone: Optional[str] = None
    is_open: Optional[bool] = None
    prep_lead_time_mins: Optional[int] = None
    settlement_type: Optional[SettlementType] = None

class ShopDetailOut(ShopOut):
    categories: List[MenuCategoryOut] = []
    items: List[MenuItemOut] = []
    current_prepaid_balance: Optional[float] = None

class MenuPriceUpdateRequest(BaseModel):
    new_price: float
    reason: str
    admin_id: str = "admin@thesortedclub.com"

# ----------------- Promotional Coupons & Banners -----------------
class CouponOut(BaseModel):
    id: int
    code: str
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: float
    min_order_amount: float
    max_discount: Optional[float] = None
    is_active: bool
    usage_count: int
    valid_until: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class CouponCreate(BaseModel):
    code: str
    description: Optional[str] = None
    discount_type: DiscountType = DiscountType.FLAT
    discount_value: float
    min_order_amount: float = 0.0
    max_discount: Optional[float] = None
    is_active: bool = True
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = None

class CouponApplyRequest(BaseModel):
    coupon_code: str
    items_subtotal: float

class CouponApplyResponse(BaseModel):
    is_valid: bool
    coupon_code: str
    discount_amount: float
    message: str
    new_grand_total: float

class PromoBannerOut(BaseModel):
    id: int
    title: str
    subtitle: Optional[str] = None
    badge_text: Optional[str] = None
    coupon_code: Optional[str] = None
    image_url: Optional[str] = None
    bg_gradient: Optional[str] = "from-[#103D32] to-[#1B4332]"
    action_link: Optional[str] = None
    sort_order: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class PromoBannerCreate(BaseModel):
    title: str
    subtitle: Optional[str] = None
    badge_text: Optional[str] = None
    coupon_code: Optional[str] = None
    image_url: Optional[str] = None
    bg_gradient: Optional[str] = "from-[#103D32] to-[#1B4332]"
    action_link: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

# ----------------- Cart & Order Schemas -----------------
class CartItemInput(BaseModel):
    menu_item_id: int
    quantity: int

class MasterOrderCreate(BaseModel):
    items: List[CartItemInput]
    tower: str
    floor: int
    desk_location: str
    delivery_instructions: Optional[str] = None
    payment_method: str = "UPI"
    coupon_code: Optional[str] = None
    scheduled_window: Optional[str] = None
    idempotency_key: Optional[str] = None

class OrderItemOut(BaseModel):
    id: int
    menu_item_id: Optional[int] = None
    item_name: str
    unit_price: float
    quantity: int
    subtotal: float
    is_rejected: bool
    rejection_reason: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class VendorOrderOut(BaseModel):
    id: int
    shop_id: int
    shop_name: Optional[str] = None
    shop_subtotal: float
    status: VendorOrderStatus
    estimated_prep_time_mins: int
    pickup_confirmed_at: Optional[datetime] = None
    order_items: List[OrderItemOut] = []
    model_config = ConfigDict(from_attributes=True)

class MasterOrderOut(BaseModel):
    id: int
    order_number: str
    user_id: int
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    status: MasterOrderStatus
    tower: str
    floor: int
    desk_location: str
    delivery_instructions: Optional[str] = None
    items_subtotal: float
    flat_delivery_fee: float
    discount_amount: float
    coupon_code: Optional[str] = None
    grand_total: float
    payment_status: PaymentStatus
    master_otp: str
    cancellation_deadline: datetime
    can_cancel: bool = False
    cancellation_seconds_remaining: int = 0
    scheduled_window: Optional[str] = None
    created_at: datetime
    vendor_orders: List[VendorOrderOut] = []
    estimated_arrival_window: Optional[str] = None
    runner_name: Optional[str] = None
    runner_phone: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# ----------------- Cancellation & Refund -----------------
class CancelOrderRequest(BaseModel):
    reason: Optional[str] = "Customer requested cancellation within 2 minutes"

class CancelOrderResponse(BaseModel):
    success: bool
    message: str
    refund_amount: float
    refund_id: Optional[str] = None

class ItemRejectionRequest(BaseModel):
    order_item_id: int
    reason: str

# ----------------- Shop Staff / Inbox Schemas -----------------
class ShopStaffRegisterRequest(BaseModel):
    phone: str
    full_name: str
    shop_id: int
    role_title: str = "Counter Staff"

class ShopOrderActionRequest(BaseModel):
    action: str  # ACCEPT | REJECT | PREPARING | READY
    estimated_prep_time_mins: Optional[int] = None
    rejection_reason: Optional[str] = None

class ItemAvailabilityToggle(BaseModel):
    menu_item_id: int
    is_available: bool

# ----------------- Delivery Schemas -----------------
class DeliveryAssignmentOut(BaseModel):
    id: int
    master_order_id: int
    status: str
    order: Optional[MasterOrderOut] = None
    assigned_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PickupConfirmRequest(BaseModel):
    vendor_order_id: int
    notes: Optional[str] = None

class DeliveryProofSubmit(BaseModel):
    master_order_id: int
    photo_data_base64: str  # Direct camera capture data
    latitude: float  # Real device coordinate required
    longitude: float

class DeliveryOTPVerifyRequest(BaseModel):
    master_order_id: int
    entered_otp: str

# ----------------- Financial Schemas -----------------
class DailySettlementCreate(BaseModel):
    shop_id: int
    settlement_date: str  # YYYY-MM-DD

class DailySettlementOut(BaseModel):
    id: int
    settlement_reference: str
    shop_id: int
    shop_name: Optional[str] = None
    settlement_date: str
    total_payable: float
    order_count: int
    status: SettlementStatus
    finance_approved_by: Optional[str] = None
    payout_utr_ref: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PrepaidTopupRequest(BaseModel):
    shop_id: int
    amount: float
    reference_id: str
    notes: Optional[str] = None

class PrepaidAccountOut(BaseModel):
    shop_id: int
    shop_name: str
    current_balance: float
    min_threshold_alert: float
    is_low_balance_alerted: bool
    last_topped_up_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class PrepaidLedgerOut(BaseModel):
    id: int
    transaction_type: str
    amount: float
    balance_after: float
    reference_id: str
    notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ----------------- Dynamic ETA -----------------
class DynamicEtaOut(BaseModel):
    min_eta_mins: int
    max_eta_mins: int
    estimated_arrival_window: str
    preparation_overlap_mins: int
    travel_between_shops_mins: int
    runner_building_access_mins: int
    floor_and_desk_handover_mins: int
    total_estimated_mins: int
    factors: Dict[str, Any]

# ----------------- Admin Dashboard Stats -----------------
class DashboardOverviewStats(BaseModel):
    today_orders_count: int
    gross_order_value: float
    delivery_fee_revenue: float
    active_deliveries_count: int
    on_time_delivery_pct: float
    avg_delivery_time_mins: int
    pending_settlements_count: int
    low_prepaid_shops_count: int
    total_refunds_today: float
    repeat_customer_rate_pct: float
