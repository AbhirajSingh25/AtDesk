export type UserRole = "EMPLOYEE" | "DELIVERY_PARTNER" | "ADMIN" | "FINANCE";

export type MasterOrderStatus =
  | "CREATED"
  | "CONFIRMED"
  | "PREPARING"
  | "PICKING_UP"
  | "OUT_FOR_DELIVERY"
  | "DELIVERED"
  | "CANCELLED"
  | "PARTIALLY_REFUNDED";

export type VendorOrderStatus =
  | "PENDING"
  | "ACCEPTED"
  | "PREPARING"
  | "READY_FOR_PICKUP"
  | "PICKED_UP"
  | "REJECTED"
  | "CANCELLED";

export type SettlementType = "DAILY" | "PREPAID";

export interface MenuItem {
  id: number;
  shop_id: number;
  category_id?: number;
  name: string;
  description?: string;
  price: number;
  portion_size?: string;
  image_url?: string;
  is_food: boolean;
  dietary: "VEG" | "NON_VEG" | "EGG" | "NONE";
  prep_time_mins: number;
  is_available: boolean;
}

export interface MenuCategory {
  id: number;
  name: string;
  sort_order: number;
  items: MenuItem[];
}

export interface Shop {
  id: number;
  name: string;
  slug: string;
  image_url?: string;
  category: string;
  location_details: string;
  phone: string;
  is_open: boolean;
  prep_lead_time_mins: number;
  settlement_type: SettlementType;
  categories?: MenuCategory[];
  items?: MenuItem[];
  current_prepaid_balance?: number;
}

export interface CartItem {
  menuItem: MenuItem;
  shop: Shop;
  quantity: number;
}

export interface OrderItem {
  id: number;
  menu_item_id?: number;
  item_name: string;
  unit_price: number;
  quantity: number;
  subtotal: number;
  is_rejected: boolean;
  rejection_reason?: string;
}

export interface VendorOrder {
  id: number;
  shop_id: number;
  shop_name?: string;
  shop_subtotal: number;
  status: VendorOrderStatus;
  estimated_prep_time_mins: number;
  pickup_confirmed_at?: string;
  order_items: OrderItem[];
}

export interface MasterOrder {
  id: number;
  order_number: string;
  user_id: number;
  user_name?: string;
  user_phone?: string;
  status: MasterOrderStatus;
  tower: string;
  floor: number;
  desk_location: string;
  delivery_instructions?: string;
  items_subtotal: number;
  flat_delivery_fee: number;
  discount_amount: number;
  grand_total: number;
  payment_status: string;
  master_otp: string;
  cancellation_deadline: string;
  can_cancel: boolean;
  cancellation_seconds_remaining: number;
  scheduled_window?: string;
  created_at: string;
  vendor_orders: VendorOrder[];
  estimated_arrival_window?: string;
}

export interface DashboardStats {
  today_orders_count: number;
  gross_order_value: number;
  delivery_fee_revenue: number;
  active_deliveries_count: number;
  on_time_delivery_pct: number;
  avg_delivery_time_mins: number;
  pending_settlements_count: number;
  low_prepaid_shops_count: number;
  total_refunds_today: number;
  repeat_customer_rate_pct: number;
}

export interface DailySettlement {
  id: number;
  settlement_reference: string;
  shop_id: number;
  shop_name?: string;
  settlement_date: string;
  total_payable: number;
  order_count: number;
  status: "DRAFT" | "VERIFIED" | "PAID";
  finance_approved_by?: string;
  payout_utr_ref?: string;
  paid_at?: string;
  created_at: string;
}

export interface PrepaidAccount {
  shop_id: number;
  shop_name: string;
  current_balance: number;
  min_threshold_alert: number;
  is_low_balance_alerted: boolean;
  last_topped_up_at?: string;
}

export interface PrepaidLedgerEntry {
  id: number;
  transaction_type: string;
  amount: number;
  balance_after: number;
  reference_id: string;
  notes?: string;
  created_at: string;
}

export interface AuditLogItem {
  id: number;
  user_id?: string;
  role: string;
  action: string;
  target_entity: string;
  target_id?: string;
  details?: string;
  ip_address: string;
  created_at: string;
}

