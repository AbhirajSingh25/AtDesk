"use client";

import React, { useState, useEffect } from "react";
import { 
  MasterOrder, Shop, DashboardStats, DailySettlement, 
  PrepaidAccount, PrepaidLedgerEntry, AuditLogItem 
} from "@/types";
import { fetchApi } from "@/lib/api";
import { 
  LayoutDashboard, ShoppingCart, Store, UtensilsCrossed, 
  Bike, MapPin, Receipt, Wallet, RotateCcw, Users, 
  ShieldAlert, RefreshCw, CheckCircle2, AlertCircle, 
  Search, Filter, ArrowUpRight, Plus, ExternalLink, 
  ChevronRight, Building2, Check, Clock 
} from "lucide-react";

import { PilotDashboardView } from "./PilotDashboardView";

type AdminTab = 
  | "pilot"
  | "overview" 
  | "live-orders" 
  | "all-orders" 
  | "shops" 
  | "menu" 
  | "runners" 
  | "settlements" 
  | "prepaid" 
  | "refunds" 
  | "employees" 
  | "audit";

export function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<AdminTab>("pilot");
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [orders, setOrders] = useState<MasterOrder[]>([]);
  const [shops, setShops] = useState<any[]>([]);
  const [settlements, setSettlements] = useState<DailySettlement[]>([]);
  const [prepaidAccounts, setPrepaidAccounts] = useState<PrepaidAccount[]>([]);
  const [refunds, setRefunds] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [runners, setRunners] = useState<any[]>([]);

  // Interactive Modals
  const [selectedShopForLedger, setSelectedShopForLedger] = useState<number | null>(null);
  const [shopLedgerEntries, setShopLedgerEntries] = useState<PrepaidLedgerEntry[]>([]);
  const [isTopupModalOpen, setIsTopupModalOpen] = useState(false);
  const [topupShopId, setTopupShopId] = useState<number>(1);
  const [topupAmount, setTopupAmount] = useState<number>(2000);
  const [topupUtr, setTopupUtr] = useState<string>("BANK-ADVANCE-778899");

  // Price Modification Modal
  const [isPriceModalOpen, setIsPriceModalOpen] = useState(false);
  const [priceItemName, setPriceItemName] = useState("");
  const [priceItemId, setPriceItemId] = useState<number>(1);
  const [newPrice, setNewPrice] = useState<number>(150);
  const [priceReason, setPriceReason] = useState("");

  // Settlement UTR Verification Modal
  const [isSettleModalOpen, setIsSettleModalOpen] = useState(false);
  const [settleId, setSettleId] = useState<number | null>(null);
  const [settleUtr, setSettleUtr] = useState("");

  const [isLoading, setIsLoading] = useState(true);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      const [
        sStats, sOrders, sShops, sSettles, sPrepaid, sRefunds, sEmps, sAudits, sRunners
      ] = await Promise.all([
        fetchApi<DashboardStats>("/admin/dashboard-stats"),
        fetchApi<MasterOrder[]>("/admin/orders"),
        fetchApi<any[]>("/admin/shops"),
        fetchApi<DailySettlement[]>("/admin/settlements"),
        fetchApi<PrepaidAccount[]>("/admin/prepaid-accounts"),
        fetchApi<any[]>("/admin/refunds"),
        fetchApi<any[]>("/admin/employees"),
        fetchApi<AuditLogItem[]>("/admin/audit-logs"),
        fetchApi<any[]>("/admin/delivery-partners"),
      ]);

      setStats(sStats);
      setOrders(sOrders);
      setShops(sShops);
      setSettlements(sSettles);
      setPrepaidAccounts(sPrepaid);
      setRefunds(sRefunds);
      setEmployees(sEmps);
      setAuditLogs(sAudits);
      setRunners(sRunners);
    } catch (err) {
      console.error("Failed to load admin data", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleShop = async (shopId: number) => {
    try {
      await fetchApi(`/admin/shops/${shopId}/toggle-status`, { method: "POST" });
      await loadAllData();
    } catch (e: any) {
      alert(e.message || "Failed to toggle shop status");
    }
  };

  const handleAdvanceOrderStatus = async (orderId: number, nextStatus: string) => {
    try {
      await fetchApi(`/admin/orders/${orderId}/advance-status?next_status=${nextStatus}`, {
        method: "POST",
      });
      await loadAllData();
    } catch (e: any) {
      alert(e.message || "Failed to update status");
    }
  };

  const handlePriceUpdate = async () => {
    if (!priceReason) {
      alert("Please provide a reason for the menu price change.");
      return;
    }
    try {
      await fetchApi(`/admin/menu/price-update?item_id=${priceItemId}`, {
        method: "POST",
        body: JSON.stringify({
          new_price: newPrice,
          reason: priceReason,
          admin_id: "admin@thesortedclub.com",
        }),
      });
      setIsPriceModalOpen(false);
      setPriceReason("");
      await loadAllData();
      alert("Menu item price updated and logged to audit trail.");
    } catch (e: any) {
      alert(e.message || "Failed to update price");
    }
  };

  const handlePrepaidTopup = async () => {
    try {
      await fetchApi("/admin/prepaid/topup", {
        method: "POST",
        body: JSON.stringify({
          shop_id: topupShopId,
          amount: topupAmount,
          reference_id: topupUtr,
          notes: "Advance prepaid balance recharge via admin operations",
        }),
      });
      setIsTopupModalOpen(false);
      await loadAllData();
      alert("Prepaid account credited successfully.");
    } catch (e: any) {
      alert(e.message || "Failed to topup prepaid balance");
    }
  };

  const handleViewLedger = async (shopId: number) => {
    setSelectedShopForLedger(shopId);
    try {
      const ledger = await fetchApi<PrepaidLedgerEntry[]>(`/admin/prepaid-accounts/${shopId}/ledger`);
      setShopLedgerEntries(ledger);
    } catch (e) {
      console.error(e);
    }
  };

  const handleVerifySettle = async () => {
    if (!settleId || !settleUtr) {
      alert("Please enter banking transaction UTR reference");
      return;
    }
    try {
      await fetchApi(`/admin/settlements/${settleId}/verify-and-pay`, {
        method: "POST",
        body: JSON.stringify({ utr_reference: settleUtr }),
      });
      setIsSettleModalOpen(false);
      setSettleUtr("");
      await loadAllData();
      alert("Settlement marked PAID with UTR recorded.");
    } catch (e: any) {
      alert(e.message || "Failed to verify settlement");
    }
  };

  return (
    <div className="min-h-screen bg-brand-ivory text-brand-charcoal flex flex-col md:flex-row">
      {/* Desktop Sidebar Navigation */}
      <aside className="w-full md:w-64 bg-brand-forest text-brand-ivory shrink-0 border-r border-brand-forest-dark flex flex-col justify-between">
        <div className="p-4 space-y-6">
          {/* Brand header */}
          <div className="flex items-center gap-2.5 px-2">
            <div className="w-8 h-8 rounded-xl bg-brand-sage text-brand-forest flex items-center justify-center font-heading font-extrabold text-base">
              @
            </div>
            <div>
              <div className="font-heading font-bold text-sm text-white tracking-wide">
                AtDesk Command
              </div>
              <div className="text-[10px] text-brand-sage/80">
                The Sorted Club Operations
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1 text-xs">
            {[
              { id: "pilot", label: "Commercial Pilot (JMD)", icon: Building2 },
              { id: "overview", label: "Overview & KPIs", icon: LayoutDashboard },
              { id: "live-orders", label: "Live Order Stages", icon: ShoppingCart },
              { id: "all-orders", label: "All Orders Archive", icon: Receipt },
              { id: "shops", label: "Shops Management", icon: Store },
              { id: "menu", label: "Menu & Price Audits", icon: UtensilsCrossed },
              { id: "runners", label: "Delivery Fleet", icon: Bike },
              { id: "settlements", label: "Daily Settlements", icon: Receipt },
              { id: "prepaid", label: "Prepaid Shop Ledgers", icon: Wallet },
              { id: "refunds", label: "Refund Management", icon: RotateCcw },
              { id: "employees", label: "JMD Megapolis Users", icon: Users },
              { id: "audit", label: "Security & Audit Logs", icon: ShieldAlert },
            ].map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id as AdminTab)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl font-medium transition-all ${
                    isActive
                      ? "bg-brand-sage text-brand-forest font-bold shadow-sm"
                      : "text-brand-ivory/80 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Footer Info */}
        <div className="p-4 border-t border-brand-forest-dark text-[11px] text-brand-sage/70 space-y-1">
          <div className="flex items-center gap-1.5 font-medium text-white">
            <Building2 className="w-3.5 h-3.5 text-brand-tangerine" />
            <span>JMD Megapolis, Sector 48</span>
          </div>
          <div>No Vendor App Required</div>
          <div className="text-[9px] text-brand-sage/50">v1.0.0 Production Core</div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-4 md:p-8 overflow-y-auto space-y-6">
        {/* Top Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-brand-sage/60 pb-4">
          <div>
            <h1 className="font-heading font-extrabold text-2xl text-brand-charcoal capitalize">
              {activeTab.replace(/-/g, " ")}
            </h1>
            <p className="text-xs text-brand-charcoal-muted mt-0.5">
              Live source of truth: PostgreSQL normalized database & immutable financial ledgers.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadAllData}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-white text-brand-charcoal hover:bg-brand-sage-light border border-brand-sage rounded-xl text-xs font-semibold shadow-soft transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5 text-brand-forest" />
              <span>Sync Live State</span>
            </button>
          </div>
        </div>

        {/* TAB 0: CONTROLLED COMMERCIAL PILOT */}
        {activeTab === "pilot" && <PilotDashboardView />}

        {/* TAB 1: OVERVIEW & KPIS */}
        {activeTab === "overview" && stats && (
          <div className="space-y-6">
            {/* KPI Cards Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-3xl border border-brand-sage/80 shadow-soft">
                <span className="text-xs text-brand-charcoal-muted block">Gross Order Value</span>
                <span className="text-2xl font-mono font-bold text-brand-forest mt-1 block">
                  ₹{stats.gross_order_value}
                </span>
                <span className="text-[10px] text-emerald-600 font-semibold mt-1 block">
                  {stats.today_orders_count} orders placed today
                </span>
              </div>

              <div className="bg-white p-4 rounded-3xl border border-brand-sage/80 shadow-soft">
                <span className="text-xs text-brand-charcoal-muted block">Delivery Fee Revenue</span>
                <span className="text-2xl font-mono font-bold text-brand-forest mt-1 block">
                  ₹{stats.delivery_fee_revenue}
                </span>
                <span className="text-[10px] text-brand-charcoal-muted mt-1 block">
                  Flat ₹25 per desk drop
                </span>
              </div>

              <div className="bg-white p-4 rounded-3xl border border-brand-sage/80 shadow-soft">
                <span className="text-xs text-brand-charcoal-muted block">Active Operations</span>
                <span className="text-2xl font-mono font-bold text-brand-tangerine mt-1 block">
                  {stats.active_deliveries_count}
                </span>
                <span className="text-[10px] text-brand-charcoal-muted mt-1 block">
                  Avg Delivery: {stats.avg_delivery_time_mins} mins
                </span>
              </div>

              <div className="bg-white p-4 rounded-3xl border border-brand-sage/80 shadow-soft">
                <span className="text-xs text-brand-charcoal-muted block">Financial Alerts</span>
                <span className="text-2xl font-mono font-bold text-rose-600 mt-1 block">
                  {stats.low_prepaid_shops_count}
                </span>
                <span className="text-[10px] text-brand-charcoal-muted mt-1 block">
                  Shops below prepaid threshold
                </span>
              </div>
            </div>

            {/* Quick Live Orders Summary */}
            <div className="bg-white rounded-3xl p-6 border border-brand-sage/80 shadow-soft space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-heading font-bold text-base text-brand-charcoal">
                  Recent Master Orders in JMD Megapolis
                </h3>
                <button
                  onClick={() => setActiveTab("live-orders")}
                  className="text-xs font-semibold text-brand-forest underline hover:text-brand-tangerine"
                >
                  Open Operations Kanban
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-brand-sage/60 text-brand-charcoal-muted">
                      <th className="py-2.5 px-3">Order Number</th>
                      <th className="py-2.5 px-3">Customer Desk</th>
                      <th className="py-2.5 px-3">Shops</th>
                      <th className="py-2.5 px-3">Amount</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Master OTP</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-brand-sage/40">
                    {orders.slice(0, 5).map((ord) => (
                      <tr key={ord.id} className="hover:bg-brand-ivory/50">
                        <td className="py-3 px-3 font-mono font-semibold text-brand-forest">
                          {ord.order_number}
                        </td>
                        <td className="py-3 px-3">
                          <div className="font-semibold text-brand-charcoal">{ord.tower}</div>
                          <div className="text-[10px] text-brand-charcoal-muted">
                            Floor {ord.floor} • {ord.desk_location}
                          </div>
                        </td>
                        <td className="py-3 px-3">
                          {ord.vendor_orders.map((vo) => vo.shop_name).join(", ")}
                        </td>
                        <td className="py-3 px-3 font-mono font-bold">₹{ord.grand_total}</td>
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-sage text-brand-forest">
                            {ord.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-mono font-extrabold text-brand-tangerine">
                          {ord.master_otp}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() => handleAdvanceOrderStatus(ord.id, "OUT_FOR_DELIVERY")}
                            className="text-[11px] font-semibold text-brand-forest hover:text-brand-tangerine underline"
                          >
                            Advance
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: LIVE ORDER STAGES (KANBAN) */}
        {activeTab === "live-orders" && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { status: "CONFIRMED", title: "1. Confirmed / Coordinating", bg: "border-brand-sage" },
              { status: "PREPARING", title: "2. Shop Preparing", bg: "border-amber-300" },
              { status: "OUT_FOR_DELIVERY", title: "3. Out for Desk Drop", bg: "border-brand-forest" },
              { status: "DELIVERED", title: "4. Delivered & Verified", bg: "border-emerald-300" },
            ].map((col) => {
              const colOrders = orders.filter((o) => o.status === col.status);
              return (
                <div
                  key={col.status}
                  className={`bg-white rounded-3xl p-4 border-2 ${col.bg} shadow-soft flex flex-col space-y-3 min-h-[450px]`}
                >
                  <div className="flex items-center justify-between pb-2 border-b border-brand-sage/60">
                    <h4 className="font-heading font-bold text-xs text-brand-charcoal">
                      {col.title}
                    </h4>
                    <span className="text-xs font-mono font-bold bg-brand-sage-light text-brand-forest px-2 py-0.5 rounded-full">
                      {colOrders.length}
                    </span>
                  </div>

                  <div className="space-y-3 overflow-y-auto flex-1">
                    {colOrders.map((o) => (
                      <div
                        key={o.id}
                        className="p-3 bg-brand-ivory/50 rounded-2xl border border-brand-sage/80 space-y-2 text-xs"
                      >
                        <div className="flex justify-between items-start">
                          <span className="font-mono font-bold text-brand-forest">
                            #{o.order_number}
                          </span>
                          <span className="font-mono font-bold">₹{o.grand_total}</span>
                        </div>

                        <div className="text-[11px]">
                          <span className="font-semibold">{o.tower}, Floor {o.floor}</span>
                          <div className="text-brand-charcoal-muted font-mono">{o.desk_location}</div>
                        </div>

                        <div className="text-[10px] text-brand-charcoal-muted">
                          OTP: <span className="font-mono font-bold text-brand-tangerine">{o.master_otp}</span>
                        </div>

                        {/* Quick state transition */}
                        <div className="pt-2 border-t border-brand-sage/40 flex justify-end gap-1.5">
                          {col.status === "CONFIRMED" && (
                            <button
                              onClick={() => handleAdvanceOrderStatus(o.id, "PREPARING")}
                              className="px-2.5 py-1 bg-brand-forest text-brand-ivory rounded-lg text-[10px] font-semibold"
                            >
                              Move to Prep
                            </button>
                          )}
                          {col.status === "PREPARING" && (
                            <button
                              onClick={() => handleAdvanceOrderStatus(o.id, "OUT_FOR_DELIVERY")}
                              className="px-2.5 py-1 bg-brand-forest text-brand-ivory rounded-lg text-[10px] font-semibold"
                            >
                              Dispatch Runner
                            </button>
                          )}
                          {col.status === "OUT_FOR_DELIVERY" && (
                            <button
                              onClick={() => handleAdvanceOrderStatus(o.id, "DELIVERED")}
                              className="px-2.5 py-1 bg-emerald-600 text-white rounded-lg text-[10px] font-semibold"
                            >
                              Mark Delivered
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* TAB 4: SHOPS MANAGEMENT */}
        {activeTab === "shops" && (
          <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-heading font-bold text-base text-brand-charcoal">
                  Shop Partners & Operating Controls
                </h3>
                <p className="text-xs text-brand-charcoal-muted">
                  Control availability without vendor app. Admin approves all updates.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-brand-sage text-brand-charcoal-muted">
                    <th className="py-2.5 px-3">Shop</th>
                    <th className="py-2.5 px-3">Location in Megapolis</th>
                    <th className="py-2.5 px-3">Settlement Model</th>
                    <th className="py-2.5 px-3">Prepaid Balance</th>
                    <th className="py-2.5 px-3">Operating State</th>
                    <th className="py-2.5 px-3 text-right">Toggle State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-sage/40">
                  {shops.map((s) => (
                    <tr key={s.id} className="hover:bg-brand-ivory/50">
                      <td className="py-3 px-3 font-semibold text-brand-charcoal">
                        {s.name}
                      </td>
                      <td className="py-3 px-3 text-brand-charcoal-muted">
                        {s.location_details}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            s.settlement_type === "PREPAID"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-blue-100 text-blue-800"
                          }`}
                        >
                          {s.settlement_type}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono font-bold">
                        {s.settlement_type === "PREPAID" ? (
                          <span className={s.is_low_balance ? "text-rose-600" : "text-brand-forest"}>
                            ₹{s.prepaid_balance ?? 0}
                          </span>
                        ) : (
                          <span className="text-brand-charcoal-muted">Daily Batch</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            s.is_open ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                          }`}
                        >
                          {s.is_open ? "OPEN" : "CLOSED"}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => handleToggleShop(s.id)}
                          className={`px-3 py-1 rounded-xl text-xs font-semibold ${
                            s.is_open
                              ? "bg-rose-50 text-rose-700 hover:bg-rose-100"
                              : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                          }`}
                        >
                          {s.is_open ? "Close Shop" : "Open Shop"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: MENU MANAGEMENT & AUDITABLE PRICE UPDATES */}
        {activeTab === "menu" && (
          <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-heading font-bold text-base text-brand-charcoal">
                  Catalog & Price Modification Engine
                </h3>
                <p className="text-xs text-brand-charcoal-muted">
                  Every price update enforces reason recording and immutable audit trail.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {[
                { id: 1, name: "Desi Chai (Cardamom & Ginger)", shop: "Chaayos", price: 99 },
                { id: 2, name: "Kulhad Chai", shop: "Chaayos", price: 119 },
                { id: 3, name: "Classic Bun Maska", shop: "Chaayos", price: 79 },
                { id: 6, name: "Paneer Tikka Sub (6-Inch)", shop: "Subway", price: 239 },
                { id: 7, name: "Roasted Chicken Strip Sub", shop: "Subway", price: 269 },
                { id: 11, name: "Delhi Style Chole Bhature", shop: "Haldiram's", price: 180 },
                { id: 15, name: "Iced Vietnamese Latte", shop: "Blue Tokai", price: 220 },
                { id: 19, name: "Braided Type-C Fast Cable (1m)", shop: "Daily Essentials", price: 299 },
              ].map((item) => (
                <div
                  key={item.id}
                  className="p-3.5 bg-brand-ivory/40 rounded-2xl border border-brand-sage flex items-center justify-between"
                >
                  <div>
                    <div className="font-semibold text-xs text-brand-charcoal">{item.name}</div>
                    <div className="text-[10px] text-brand-charcoal-muted">{item.shop}</div>
                    <div className="font-mono font-bold text-brand-forest mt-1">₹{item.price}</div>
                  </div>
                  <button
                    onClick={() => {
                      setPriceItemId(item.id);
                      setPriceItemName(item.name);
                      setNewPrice(item.price);
                      setIsPriceModalOpen(true);
                    }}
                    className="px-3 py-1.5 bg-brand-forest text-brand-ivory text-xs font-semibold rounded-xl hover:bg-brand-forest-dark"
                  >
                    Edit Price
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 8: DAILY SETTLEMENTS */}
        {activeTab === "settlements" && (
          <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-heading font-bold text-base text-brand-charcoal">
                  Daily Settlement Statements
                </h3>
                <p className="text-xs text-brand-charcoal-muted">
                  Aggregates verified daily orders for shops on daily settlement model.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-brand-sage text-brand-charcoal-muted">
                    <th className="py-2.5 px-3">Statement Ref</th>
                    <th className="py-2.5 px-3">Shop</th>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Total Payable</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Bank UTR Reference</th>
                    <th className="py-2.5 px-3 text-right">Finance Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-sage/40">
                  {settlements.map((st) => (
                    <tr key={st.id} className="hover:bg-brand-ivory/50">
                      <td className="py-3 px-3 font-mono font-bold text-brand-forest">
                        {st.settlement_reference}
                      </td>
                      <td className="py-3 px-3 font-semibold">{st.shop_name}</td>
                      <td className="py-3 px-3 font-mono">{st.settlement_date}</td>
                      <td className="py-3 px-3 font-mono font-bold">₹{st.total_payable}</td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            st.status === "PAID"
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {st.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-brand-charcoal-muted">
                        {st.payout_utr_ref || "—"}
                      </td>
                      <td className="py-3 px-3 text-right">
                        {st.status !== "PAID" && (
                          <button
                            onClick={() => {
                              setSettleId(st.id);
                              setIsSettleModalOpen(true);
                            }}
                            className="px-3 py-1 bg-brand-forest text-brand-ivory rounded-xl text-xs font-semibold"
                          >
                            Verify & Pay
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 9: PREPAID BALANCES & IMMUTABLE LEDGER */}
        {activeTab === "prepaid" && (
          <div className="space-y-6">
            <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-heading font-bold text-base text-brand-charcoal">
                    Prepaid Shop Balances
                  </h3>
                  <p className="text-xs text-brand-charcoal-muted">
                    Advance balance model: new orders stop when balance is depleted.
                  </p>
                </div>
                <button
                  onClick={() => setIsTopupModalOpen(true)}
                  className="px-3.5 py-2 bg-brand-forest text-brand-ivory text-xs font-semibold rounded-xl shadow-xs flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Record Advance Top-Up</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {prepaidAccounts.map((acc) => (
                  <div
                    key={acc.shop_id}
                    className="p-4 bg-brand-ivory/40 rounded-2xl border border-brand-sage space-y-2"
                  >
                    <div className="flex justify-between items-start">
                      <span className="font-heading font-bold text-xs text-brand-charcoal">
                        {acc.shop_name}
                      </span>
                      {acc.is_low_balance_alerted && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800">
                          LOW BALANCE
                        </span>
                      )}
                    </div>

                    <div className="text-xl font-mono font-extrabold text-brand-forest">
                      ₹{acc.current_balance}
                    </div>

                    <div className="text-[10px] text-brand-charcoal-muted flex justify-between">
                      <span>Threshold: ₹{acc.min_threshold_alert}</span>
                      <button
                        onClick={() => handleViewLedger(acc.shop_id)}
                        className="text-brand-forest font-semibold underline"
                      >
                        View Immutable Ledger
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Selected Shop Ledger Entries */}
            {selectedShopForLedger && (
              <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="font-heading font-bold text-sm text-brand-charcoal">
                    Immutable Ledger Stream for Shop #{selectedShopForLedger}
                  </h4>
                  <button
                    onClick={() => setSelectedShopForLedger(null)}
                    className="text-xs text-brand-charcoal-muted underline"
                  >
                    Close Ledger
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-brand-sage text-brand-charcoal-muted">
                        <th className="py-2 px-3">Type</th>
                        <th className="py-2 px-3">Amount</th>
                        <th className="py-2 px-3">Balance After</th>
                        <th className="py-2 px-3">Reference</th>
                        <th className="py-2 px-3">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-brand-sage/40">
                      {shopLedgerEntries.map((e) => (
                        <tr key={e.id}>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                e.transaction_type === "CREDIT_TOPUP"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : e.transaction_type === "REVERSAL_REFUND"
                                  ? "bg-blue-100 text-blue-800"
                                  : "bg-rose-100 text-rose-800"
                              }`}
                            >
                              {e.transaction_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono font-bold">₹{e.amount}</td>
                          <td className="py-2.5 px-3 font-mono">₹{e.balance_after}</td>
                          <td className="py-2.5 px-3 font-mono text-brand-forest">{e.reference_id}</td>
                          <td className="py-2.5 px-3 text-brand-charcoal-muted">{e.notes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 11: SECURITY & AUDIT LOGS */}
        {activeTab === "audit" && (
          <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
            <h3 className="font-heading font-bold text-base text-brand-charcoal">
              Immutable System & Operational Audit Logs
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-brand-sage text-brand-charcoal-muted">
                    <th className="py-2 px-3">Role</th>
                    <th className="py-2 px-3">Action</th>
                    <th className="py-2 px-3">Target Entity</th>
                    <th className="py-2 px-3">Details</th>
                    <th className="py-2 px-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-sage/40">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-brand-ivory/50">
                      <td className="py-2.5 px-3 font-semibold text-brand-forest">{log.role}</td>
                      <td className="py-2.5 px-3 font-mono font-bold text-xs">{log.action}</td>
                      <td className="py-2.5 px-3 text-brand-charcoal-muted">{log.target_entity}</td>
                      <td className="py-2.5 px-3 text-brand-charcoal">{log.details}</td>
                      <td className="py-2.5 px-3 font-mono text-[10px] text-brand-charcoal-muted">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 10: REFUNDS ARCHIVE */}
        {activeTab === "refunds" && (
          <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
            <h3 className="font-heading font-bold text-base text-brand-charcoal">
              Refunds Log (2-Min Cancellations & Partial Rejections)
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-brand-sage text-brand-charcoal-muted">
                    <th className="py-2 px-3">Order Number</th>
                    <th className="py-2 px-3">Amount</th>
                    <th className="py-2 px-3">Reason</th>
                    <th className="py-2 px-3">Status</th>
                    <th className="py-2 px-3">Gateway ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-sage/40">
                  {refunds.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-4 text-center text-brand-charcoal-muted">
                        No refunds issued yet.
                      </td>
                    </tr>
                  ) : (
                    refunds.map((r) => (
                      <tr key={r.id}>
                        <td className="py-2.5 px-3 font-mono font-bold text-brand-forest">
                          {r.order_number || `#${r.master_order_id}`}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold text-rose-600">₹{r.amount}</td>
                        <td className="py-2.5 px-3">{r.reason}</td>
                        <td className="py-2.5 px-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            {r.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[10px] text-brand-charcoal-muted">
                          {r.gateway_refund_id}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 6: FLEET RUNNERS */}
        {activeTab === "runners" && (
          <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
            <h3 className="font-heading font-bold text-base text-brand-charcoal">
              AtDesk Dedicated Runners (JMD Megapolis)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {runners.map((run) => (
                <div
                  key={run.id}
                  className="p-4 bg-brand-ivory/50 rounded-2xl border border-brand-sage flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-brand-forest text-brand-ivory flex items-center justify-center font-bold">
                      <Bike className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-heading font-bold text-sm text-brand-charcoal">
                        {run.name}
                      </div>
                      <div className="text-[11px] text-brand-charcoal-muted font-mono">
                        Vehicle: {run.vehicle_number} • Phone: {run.phone}
                      </div>
                      <div className="text-[10px] text-brand-forest font-semibold mt-0.5">
                        GPS: Sector 48 Plaza (28.4162, 77.0425)
                      </div>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                    ACTIVE
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 7: EMPLOYEES */}
        {activeTab === "employees" && (
          <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
            <h3 className="font-heading font-bold text-base text-brand-charcoal">
              Registered JMD Megapolis Employees
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-brand-sage text-brand-charcoal-muted">
                    <th className="py-2 px-3">Name</th>
                    <th className="py-2 px-3">Phone</th>
                    <th className="py-2 px-3">Employer / Company</th>
                    <th className="py-2 px-3">Tower</th>
                    <th className="py-2 px-3">Floor</th>
                    <th className="py-2 px-3">Desk ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-sage/40">
                  {employees.map((emp) => (
                    <tr key={emp.id}>
                      <td className="py-2.5 px-3 font-semibold text-brand-charcoal">{emp.name}</td>
                      <td className="py-2.5 px-3 font-mono">{emp.phone}</td>
                      <td className="py-2.5 px-3">{emp.company}</td>
                      <td className="py-2.5 px-3 font-semibold">{emp.tower}</td>
                      <td className="py-2.5 px-3">Floor {emp.floor}</td>
                      <td className="py-2.5 px-3 font-mono text-brand-forest">{emp.desk}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* PRICE MODAL */}
      {isPriceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-3xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="font-heading font-bold text-sm text-brand-charcoal">
              Modify Price: {priceItemName}
            </h3>
            <div>
              <label className="text-xs font-semibold text-brand-charcoal-muted block mb-1">
                New Price (₹)
              </label>
              <input
                type="number"
                value={newPrice}
                onChange={(e) => setNewPrice(Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-xl font-mono text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-brand-charcoal-muted block mb-1">
                Mandatory Audit Reason
              </label>
              <textarea
                value={priceReason}
                onChange={(e) => setPriceReason(e.target.value)}
                placeholder="e.g. Vendor raw material cost revised"
                rows={2}
                className="w-full px-3 py-2 border rounded-xl text-xs"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setIsPriceModalOpen(false)}
                className="flex-1 py-2 rounded-xl border text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handlePriceUpdate}
                className="flex-1 py-2 bg-brand-forest text-brand-ivory rounded-xl text-xs font-bold"
              >
                Save & Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PREPAID TOPUP MODAL */}
      {isTopupModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-3xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="font-heading font-bold text-sm text-brand-charcoal">
              Record Advance Prepaid Deposit
            </h3>
            <div>
              <label className="text-xs font-semibold text-brand-charcoal-muted block mb-1">
                Target Shop
              </label>
              <select
                value={topupShopId}
                onChange={(e) => setTopupShopId(Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-xl text-xs"
              >
                {shops.filter((s) => s.settlement_type === "PREPAID").map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-brand-charcoal-muted block mb-1">
                Deposit Amount (₹)
              </label>
              <input
                type="number"
                value={topupAmount}
                onChange={(e) => setTopupAmount(Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-xl font-mono text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-brand-charcoal-muted block mb-1">
                Bank / UPI Transaction Reference
              </label>
              <input
                type="text"
                value={topupUtr}
                onChange={(e) => setTopupUtr(e.target.value)}
                className="w-full px-3 py-2 border rounded-xl font-mono text-xs"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setIsTopupModalOpen(false)}
                className="flex-1 py-2 rounded-xl border text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handlePrepaidTopup}
                className="flex-1 py-2 bg-brand-forest text-brand-ivory rounded-xl text-xs font-bold"
              >
                Record Deposit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SETTLEMENT VERIFY MODAL */}
      {isSettleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-3xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="font-heading font-bold text-sm text-brand-charcoal">
              Verify Daily Payout UTR
            </h3>
            <div>
              <label className="text-xs font-semibold text-brand-charcoal-muted block mb-1">
                Banking UTR / UPI Reference
              </label>
              <input
                type="text"
                value={settleUtr}
                onChange={(e) => setSettleUtr(e.target.value)}
                placeholder="e.g. UTR-HDFC-998822"
                className="w-full px-3 py-2 border rounded-xl font-mono text-xs"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setIsSettleModalOpen(false)}
                className="flex-1 py-2 rounded-xl border text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleVerifySettle}
                className="flex-1 py-2 bg-brand-forest text-brand-ivory rounded-xl text-xs font-bold"
              >
                Verify & Mark Paid
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

