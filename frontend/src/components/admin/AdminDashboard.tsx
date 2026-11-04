"use client";

import React, { useState, useEffect } from "react";
import { 
  MasterOrder, Shop, DashboardStats, DailySettlement, 
  PrepaidAccount, PrepaidLedgerEntry, AuditLogItem, MenuItem,
  Coupon, PromoBanner
} from "@/types";
import { fetchApi } from "@/lib/api";
import { 
  LayoutDashboard, ShoppingCart, Store, UtensilsCrossed, 
  Bike, MapPin, Receipt, Wallet, RotateCcw, Users, 
  ShieldAlert, RefreshCw, CheckCircle2, AlertCircle, 
  Search, Filter, ArrowUpRight, Plus, ExternalLink, 
  ChevronRight, Building2, Check, Clock, Eye, EyeOff,
  Upload, FileText, Tag, Image, Trash2, Edit3, X, Sparkles,
  AlertTriangle
} from "lucide-react";

import { PilotDashboardView } from "./PilotDashboardView";

type AdminTab = 
  | "pilot"
  | "overview" 
  | "exceptions"
  | "live-orders" 
  | "all-orders" 
  | "shops" 
  | "catalogue"
  | "promos"
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

  // Database-backed Catalogue & Promo state
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [exceptions, setExceptions] = useState<any[]>([]);
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [banners, setBanners] = useState<PromoBanner[]>([]);

  // Modals
  const [isNewItemModalOpen, setIsNewItemModalOpen] = useState(false);
  const [isBulkCsvModalOpen, setIsBulkCsvModalOpen] = useState(false);
  const [isCouponModalOpen, setIsCouponModalOpen] = useState(false);
  const [isBannerModalOpen, setIsBannerModalOpen] = useState(false);
  const [csvText, setCsvText] = useState("");
  const [csvFeedback, setCsvFeedback] = useState<string | null>(null);

  // New Item Form
  const [itemForm, setItemForm] = useState({
    shop_id: 1,
    name: "",
    description: "",
    price: 150,
    dietary: "VEG",
    prep_time_mins: 10,
    portion_size: "Serves 1",
    is_food: true,
    image_url: "",
  });

  // New Coupon Form
  const [couponForm, setCouponForm] = useState({
    code: "",
    discount_type: "FLAT",
    discount_value: 50,
    min_order_amount: 199,
    max_discount: 100,
  });

  // New Banner Form
  const [bannerForm, setBannerForm] = useState({
    title: "",
    subtitle: "",
    image_url: "",
    badge_text: "FEATURED",
  });

  // Price Modification Modal
  const [isPriceModalOpen, setIsPriceModalOpen] = useState(false);
  const [priceItemName, setPriceItemName] = useState("");
  const [priceItemId, setPriceItemId] = useState<number>(1);
  const [newPrice, setNewPrice] = useState<number>(150);
  const [priceReason, setPriceReason] = useState("");

  // OTP Reveal State
  const [revealedOtps, setRevealedOtps] = useState<Record<number, string>>({});

  // Topup Modal
  const [isTopupModalOpen, setIsTopupModalOpen] = useState(false);
  const [topupShopId, setTopupShopId] = useState<number>(1);
  const [topupAmount, setTopupAmount] = useState<number>(2000);
  const [topupUtr, setTopupUtr] = useState<string>("BANK-ADVANCE-778899");

  // Settlement UTR Modal
  const [isSettleModalOpen, setIsSettleModalOpen] = useState(false);
  const [settleId, setSettleId] = useState<number | null>(null);
  const [settleUtr, setSettleUtr] = useState("");

  const [isLoading, setIsLoading] = useState(true);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      const [
        sStats, sOrders, sShops, sSettles, sPrepaid, sRefunds, sEmps, sAudits, sRunners,
        sMenu, sExceptions, sCoupons, sBanners
      ] = await Promise.all([
        fetchApi<DashboardStats>("/admin/dashboard-stats").catch(() => null),
        fetchApi<MasterOrder[]>("/admin/orders").catch(() => []),
        fetchApi<any[]>("/admin/shops").catch(() => []),
        fetchApi<DailySettlement[]>("/admin/settlements").catch(() => []),
        fetchApi<PrepaidAccount[]>("/admin/prepaid-accounts").catch(() => []),
        fetchApi<any[]>("/admin/refunds").catch(() => []),
        fetchApi<any[]>("/admin/employees").catch(() => []),
        fetchApi<AuditLogItem[]>("/admin/audit-logs").catch(() => []),
        fetchApi<any[]>("/admin/delivery-partners").catch(() => []),
        fetchApi<MenuItem[]>("/admin/menu-items").catch(() => []),
        fetchApi<any[]>("/admin/exceptions").catch(() => []),
        fetchApi<Coupon[]>("/admin/coupons").catch(() => []),
        fetchApi<PromoBanner[]>("/admin/banners").catch(() => []),
      ]);

      if (sStats) setStats(sStats);
      setOrders(sOrders);
      setShops(sShops);
      setSettlements(sSettles);
      setPrepaidAccounts(sPrepaid);
      setRefunds(sRefunds);
      setEmployees(sEmps);
      setAuditLogs(sAudits);
      setRunners(sRunners);
      setMenuItems(sMenu);
      setExceptions(sExceptions);
      setCoupons(sCoupons);
      setBanners(sBanners);
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

  // Reveal OTP with audit log
  const handleRevealOtp = async (orderId: number) => {
    const reason = prompt("Supervisor Audit: Please enter reason for revealing customer OTP (e.g. Employee unable to unlock phone):", "Customer phone battery dead");
    if (!reason) return;
    try {
      const res = await fetchApi<{ master_otp: string; order_id: number }>(`/admin/orders/${orderId}/reveal-otp`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      setRevealedOtps((prev) => ({ ...prev, [orderId]: res.master_otp }));
    } catch (e: any) {
      alert(e.message || "Failed to reveal OTP");
    }
  };

  // Create Menu Item
  const handleCreateMenuItem = async () => {
    try {
      await fetchApi("/admin/menu-items", {
        method: "POST",
        body: JSON.stringify(itemForm),
      });
      setIsNewItemModalOpen(false);
      setItemForm({
        shop_id: 1,
        name: "",
        description: "",
        price: 150,
        dietary: "VEG",
        prep_time_mins: 10,
        portion_size: "Serves 1",
        is_food: true,
        image_url: "",
      });
      await loadAllData();
    } catch (e: any) {
      alert(e.message || "Failed to create menu item");
    }
  };

  // Bulk CSV Upload
  const handleBulkCsv = async () => {
    setCsvFeedback(null);
    try {
      const res = await fetchApi<{ success: boolean; imported_count: number; message: string }>("/admin/menu-items/bulk-csv", {
        method: "POST",
        body: JSON.stringify({ csv_content: csvText }),
      });
      setCsvFeedback(`Success: ${res.message} (${res.imported_count} items)`);
      setCsvText("");
      setTimeout(async () => {
        setIsBulkCsvModalOpen(false);
        setCsvFeedback(null);
        await loadAllData();
      }, 1200);
    } catch (e: any) {
      setCsvFeedback(e.message || "CSV Import Failed");
    }
  };

  // Create Coupon
  const handleCreateCoupon = async () => {
    try {
      await fetchApi("/admin/coupons", {
        method: "POST",
        body: JSON.stringify(couponForm),
      });
      setIsCouponModalOpen(false);
      setCouponForm({
        code: "",
        discount_type: "FLAT",
        discount_value: 50,
        min_order_amount: 199,
        max_discount: 100,
      });
      await loadAllData();
    } catch (e: any) {
      alert(e.message || "Failed to create coupon");
    }
  };

  // Create Banner
  const handleCreateBanner = async () => {
    try {
      await fetchApi("/admin/banners", {
        method: "POST",
        body: JSON.stringify(bannerForm),
      });
      setIsBannerModalOpen(false);
      setBannerForm({ title: "", subtitle: "", image_url: "", badge_text: "FEATURED" });
      await loadAllData();
    } catch (e: any) {
      alert(e.message || "Failed to create banner");
    }
  };

  const handleUpdatePrice = async () => {
    if (!priceReason) {
      alert("Mandatory audit requirement: Please state the business reason for price change.");
      return;
    }
    try {
      await fetchApi(`/admin/menu/price-update?item_id=${priceItemId}`, {
        method: "POST",
        body: JSON.stringify({
          new_price: newPrice,
          reason: priceReason,
          admin_id: "operations@thesortedclub.com",
        }),
      });
      setIsPriceModalOpen(false);
      setPriceReason("");
      await loadAllData();
    } catch (e: any) {
      alert(e.message || "Failed to update price");
    }
  };

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
      await fetchApi(`/admin/orders/${orderId}/status?status=${nextStatus}`, {
        method: "POST",
      });
      await loadAllData();
    } catch (e: any) {
      alert(e.message || "Failed to advance order status");
    }
  };

  const handleTopupPrepaid = async () => {
    try {
      await fetchApi(`/admin/prepaid-accounts/${topupShopId}/topup`, {
        method: "POST",
        body: JSON.stringify({
          amount: topupAmount,
          bank_utr: topupUtr,
          notes: "Operations console verified bank transfer",
        }),
      });
      setIsTopupModalOpen(false);
      await loadAllData();
    } catch (e: any) {
      alert(e.message || "Failed to topup prepaid account");
    }
  };

  const handleMarkSettlementPaid = async () => {
    if (!settleId || !settleUtr) return;
    try {
      await fetchApi(`/admin/settlements/${settleId}/mark-paid?payout_utr_ref=${settleUtr}`, {
        method: "POST",
      });
      setIsSettleModalOpen(false);
      setSettleUtr("");
      await loadAllData();
    } catch (e: any) {
      alert(e.message || "Failed to record payout");
    }
  };

  return (
    <div className="min-h-screen bg-brand-ivory text-brand-charcoal flex flex-col md:flex-row pb-16 md:pb-0">
      {/* Sidebar Navigation (Desktop) */}
      <aside className="hidden md:flex flex-col w-64 bg-brand-forest text-brand-ivory p-4 border-r border-brand-forest-dark shrink-0">
        <div className="flex items-center gap-2 px-2 py-3 mb-4">
          <div className="w-8 h-8 rounded-xl bg-brand-sage text-brand-forest font-heading font-extrabold flex items-center justify-center text-sm">
            @
          </div>
          <div>
            <div className="font-heading font-extrabold text-sm text-white">
              AtDesk Operations
            </div>
            <div className="text-[10px] text-brand-sage/80">
              JMD Megapolis Console
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 text-xs font-semibold">
          {[
            { id: "pilot", label: "Operations Command", icon: ShieldAlert },
            { id: "exceptions", label: `Exceptions (${exceptions.length})`, icon: AlertTriangle },
            { id: "overview", label: "Dashboard Metrics", icon: LayoutDashboard },
            { id: "live-orders", label: "Live Order Stages", icon: Clock },
            { id: "all-orders", label: "Orders History", icon: ShoppingCart },
            { id: "shops", label: "Shop Partners", icon: Store },
            { id: "catalogue", label: "Catalogue CRUD", icon: UtensilsCrossed },
            { id: "promos", label: "Coupons & Banners", icon: Tag },
            { id: "runners", label: "Fleet Runners", icon: Bike },
            { id: "settlements", label: "Daily Settlements", icon: Receipt },
            { id: "prepaid", label: "Prepaid Accounts", icon: Wallet },
            { id: "refunds", label: "Refunds & Reversals", icon: RotateCcw },
            { id: "employees", label: "Registered Desks", icon: Users },
            { id: "audit", label: "Audit Logs", icon: ShieldCheck },
          ].map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as AdminTab)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all ${
                  isActive
                    ? "bg-brand-sage text-brand-forest shadow-xs font-bold"
                    : "text-brand-ivory/80 hover:bg-brand-forest-dark hover:text-white"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="pt-4 border-t border-brand-forest-dark text-[11px] text-brand-sage/60 px-2 flex justify-between items-center">
          <span>Campus: JMD Megapolis</span>
          <button onClick={loadAllData} className="hover:text-white">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Operations Header */}
        <header className="bg-white border-b border-brand-sage px-6 py-4 flex items-center justify-between sticky top-0 z-20">
          <div>
            <h2 className="font-heading font-extrabold text-lg text-brand-forest capitalize">
              {activeTab.replace("-", " ")}
            </h2>
            <p className="text-xs text-brand-charcoal-muted">
              Campus JMD Megapolis, Sector 48, Gurugram
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadAllData}
              className="px-3 py-1.5 bg-brand-ivory hover:bg-brand-sage-light border border-brand-sage rounded-xl text-xs font-semibold flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </header>

        <div className="p-6 space-y-6">
          {/* TAB: OPERATIONS PILOT VIEW */}
          {activeTab === "pilot" && (
            <PilotDashboardView onSwitchTab={(tab) => setActiveTab(tab as AdminTab)} />
          )}

          {/* TAB: EXCEPTIONS QUEUE */}
          {activeTab === "exceptions" && (
            <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-heading font-bold text-base text-brand-charcoal flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                    <span>Live Order Exception Queue</span>
                  </h3>
                  <p className="text-xs text-brand-charcoal-muted">
                    Delayed vendor orders, unaccepted tickets, and runner pickup bottlenecks requiring operational escalation.
                  </p>
                </div>
              </div>

              {exceptions.length === 0 ? (
                <div className="p-12 text-center text-xs text-brand-charcoal-muted space-y-2">
                  <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto" />
                  <p className="font-bold text-brand-forest">All Clear — Zero Unhandled Exceptions</p>
                  <p>All active orders are on schedule across JMD Megapolis concourse shops.</p>
                </div>
              ) : (
                <div className="divide-y divide-brand-sage/60">
                  {exceptions.map((exc) => (
                    <div key={exc.id} className="py-3.5 flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-xs text-brand-forest">
                            #{exc.order_number}
                          </span>
                          <span className="text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                            {exc.status}
                          </span>
                        </div>
                        <div className="text-xs text-brand-charcoal font-medium">
                          {exc.tower}, {exc.desk_location}
                        </div>
                        <div className="text-[11px] text-brand-charcoal-muted">
                          Shops: {exc.vendor_orders?.map((vo: any) => vo.shop_name).join(", ")}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => handleAdvanceOrderStatus(exc.id, "OUT_FOR_DELIVERY")}
                          className="px-3 py-1.5 bg-brand-forest hover:bg-brand-forest-dark text-white text-xs font-bold rounded-xl"
                        >
                          Dispatch Runner
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB: CATALOGUE MANAGEMENT (CRUD & BULK CSV) */}
          {activeTab === "catalogue" && (
            <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-brand-sage pb-4">
                <div>
                  <h3 className="font-heading font-bold text-base text-brand-charcoal flex items-center gap-2">
                    <UtensilsCrossed className="w-5 h-5 text-brand-forest" />
                    <span>Concourse Menu Catalogue</span>
                  </h3>
                  <p className="text-xs text-brand-charcoal-muted">
                    Database-driven menu items, dietary tags, preparation times, and prices.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsBulkCsvModalOpen(true)}
                    className="px-3.5 py-2 bg-brand-ivory hover:bg-brand-sage-light border border-brand-sage text-brand-forest text-xs font-bold rounded-xl flex items-center gap-1.5 shadow-xs"
                  >
                    <Upload className="w-4 h-4" />
                    <span>Bulk Import CSV</span>
                  </button>

                  <button
                    onClick={() => setIsNewItemModalOpen(true)}
                    className="px-4 py-2 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory text-xs font-bold rounded-xl flex items-center gap-1.5 shadow-sm"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add Menu Item</span>
                  </button>
                </div>
              </div>

              {/* Menu Items Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-brand-sage text-brand-charcoal-muted">
                      <th className="py-2.5 px-3">Item</th>
                      <th className="py-2.5 px-3">Shop</th>
                      <th className="py-2.5 px-3">Dietary</th>
                      <th className="py-2.5 px-3">Prep Lead</th>
                      <th className="py-2.5 px-3">Price</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-brand-sage/40">
                    {menuItems.map((item) => (
                      <tr key={item.id} className="hover:bg-brand-ivory/50">
                        <td className="py-3 px-3">
                          <div className="font-bold text-brand-charcoal">{item.name}</div>
                          {item.portion_size && (
                            <span className="text-[10px] text-brand-charcoal-muted">
                              {item.portion_size}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-3 text-brand-forest font-semibold">
                          {shops.find((s) => s.id === item.shop_id)?.name || `Shop #${item.shop_id}`}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              item.dietary === "VEG"
                                ? "bg-emerald-100 text-emerald-800"
                                : item.dietary === "NON_VEG"
                                ? "bg-red-100 text-red-800"
                                : "bg-amber-100 text-amber-800"
                            }`}
                          >
                            {item.dietary}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-mono text-brand-charcoal-muted">
                          ~{item.prep_time_mins} mins
                        </td>
                        <td className="py-3 px-3 font-mono font-bold text-brand-forest">
                          ₹{item.price}
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              item.is_available
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-rose-100 text-rose-800"
                            }`}
                          >
                            {item.is_available ? "In Stock" : "86'd Out"}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() => {
                              setPriceItemId(item.id);
                              setPriceItemName(item.name);
                              setNewPrice(item.price);
                              setIsPriceModalOpen(true);
                            }}
                            className="px-2.5 py-1 bg-brand-forest/10 hover:bg-brand-forest text-brand-forest hover:text-white rounded-lg text-xs font-semibold transition-colors"
                          >
                            Edit Price
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB: PROMOS & COUPONS */}
          {activeTab === "promos" && (
            <div className="space-y-6">
              {/* Coupons Section */}
              <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-heading font-bold text-base text-brand-charcoal flex items-center gap-2">
                      <Tag className="w-5 h-5 text-brand-tangerine" />
                      <span>Promotional Coupons Engine</span>
                    </h3>
                    <p className="text-xs text-brand-charcoal-muted">
                      Admin-scheduled coupon discounts applicable at multi-vendor checkout.
                    </p>
                  </div>
                  <button
                    onClick={() => setIsCouponModalOpen(true)}
                    className="px-4 py-2 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory text-xs font-bold rounded-xl flex items-center gap-1.5"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Create Coupon</span>
                  </button>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
                  {coupons.map((coupon) => (
                    <div
                      key={coupon.id}
                      className="p-4 rounded-2xl border border-brand-sage/80 bg-brand-ivory/40 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-extrabold text-sm text-brand-forest bg-white px-2.5 py-1 rounded-lg border border-brand-sage">
                          {coupon.code}
                        </span>
                        <span className="text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                          ACTIVE
                        </span>
                      </div>
                      <div className="text-xs text-brand-charcoal font-semibold">
                        {coupon.discount_type === "FLAT" ? `Flat ₹${coupon.discount_value} OFF` : `${coupon.discount_value}% OFF`}
                      </div>
                      <div className="text-[11px] text-brand-charcoal-muted">
                        Min Order: ₹{coupon.min_order_amount}
                        {coupon.max_discount ? ` • Max: ₹${coupon.max_discount}` : ""}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Banners Section */}
              <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-heading font-bold text-base text-brand-charcoal flex items-center gap-2">
                      <Image className="w-5 h-5 text-brand-forest" />
                      <span>Customer App Promotional Banners</span>
                    </h3>
                    <p className="text-xs text-brand-charcoal-muted">
                      Display banners rendered in the Swiggy-style carousel in the employee app.
                    </p>
                  </div>
                  <button
                    onClick={() => setIsBannerModalOpen(true)}
                    className="px-4 py-2 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory text-xs font-bold rounded-xl flex items-center gap-1.5"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add Banner</span>
                  </button>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
                  {banners.map((banner) => (
                    <div
                      key={banner.id}
                      className="h-32 rounded-2xl overflow-hidden relative border border-brand-sage/80 shadow-soft"
                    >
                      <img src={banner.image_url} alt={banner.title} className="w-full h-full object-cover" />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-3 flex flex-col justify-end text-white">
                        {banner.badge_text && (
                          <span className="self-start text-[9px] font-bold bg-brand-tangerine text-brand-charcoal px-2 py-0.5 rounded-full mb-1">
                            {banner.badge_text}
                          </span>
                        )}
                        <h4 className="font-heading font-bold text-xs">{banner.title}</h4>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB: ORDERS WITH MASKED OTP */}
          {(activeTab === "all-orders" || activeTab === "overview") && (
            <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-heading font-bold text-base text-brand-charcoal">
                    Multi-Shop Orders & Security Verification
                  </h3>
                  <p className="text-xs text-brand-charcoal-muted">
                    Customer OTP is masked by default for privacy. Reveals require supervisor audit reasons.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-brand-sage text-brand-charcoal-muted">
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
                    {orders.map((ord) => (
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
                          {ord.vendor_orders?.map((vo) => vo.shop_name).join(", ")}
                        </td>
                        <td className="py-3 px-3 font-mono font-bold">₹{ord.grand_total}</td>
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-sage text-brand-forest">
                            {ord.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-mono font-bold">
                          {revealedOtps[ord.id] ? (
                            <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-300">
                              {revealedOtps[ord.id]}
                            </span>
                          ) : (
                            <div className="flex items-center gap-1.5">
                              <span className="text-brand-charcoal-muted">••••••</span>
                              <button
                                onClick={() => handleRevealOtp(ord.id)}
                                title="Reveal customer OTP with supervisor audit"
                                className="p-1 hover:bg-brand-sage rounded text-brand-forest"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          )}
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
          )}

          {/* TAB: SHOPS */}
          {activeTab === "shops" && (
            <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-heading font-bold text-base text-brand-charcoal">
                    Concourse Shop Partners
                  </h3>
                  <p className="text-xs text-brand-charcoal-muted">
                    Open/close toggles, lead times, and settlement models.
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
                        <td className="py-3 px-3 font-semibold">
                          {s.settlement_type}
                        </td>
                        <td className="py-3 px-3 font-mono font-bold">
                          ₹{s.prepaid_balance ?? 0}
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

          {/* TAB: SETTLEMENTS */}
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
                        <td className="py-3 px-3 font-mono font-semibold text-brand-forest">
                          {st.settlement_reference}
                        </td>
                        <td className="py-3 px-3 font-semibold">{st.shop_name}</td>
                        <td className="py-3 px-3 font-mono">{st.settlement_date}</td>
                        <td className="py-3 px-3 font-mono font-bold">₹{st.total_payable}</td>
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-sage text-brand-forest">
                            {st.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-mono text-brand-charcoal-muted">
                          {st.payout_utr_ref || "Pending Transfer"}
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
                              Record Payout
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

          {/* TAB: AUDIT LOGS */}
          {activeTab === "audit" && (
            <div className="bg-white rounded-3xl p-6 border border-brand-sage shadow-soft space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-heading font-bold text-base text-brand-charcoal">
                    Immutable Compliance Audit Trail
                  </h3>
                  <p className="text-xs text-brand-charcoal-muted">
                    Complete records of orders, payments, supervisor OTP reveals, and menu price modifications.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-brand-sage text-brand-charcoal-muted">
                      <th className="py-2.5 px-3">Timestamp</th>
                      <th className="py-2.5 px-3">Role</th>
                      <th className="py-2.5 px-3">Action</th>
                      <th className="py-2.5 px-3">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-brand-sage/40">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-brand-ivory/50">
                        <td className="py-3 px-3 font-mono text-brand-charcoal-muted">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </td>
                        <td className="py-3 px-3 font-bold text-brand-forest">{log.role}</td>
                        <td className="py-3 px-3 font-semibold text-brand-charcoal">{log.action}</td>
                        <td className="py-3 px-3 text-brand-charcoal-muted">{log.details}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Mobile Bottom Navigation Bar */}
      <div className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-brand-forest text-brand-ivory border-t border-brand-forest-dark px-2 py-2 flex items-center justify-around text-[10px]">
        {[
          { id: "pilot", label: "Command", icon: ShieldAlert },
          { id: "exceptions", label: "Alerts", icon: AlertTriangle },
          { id: "all-orders", label: "Orders", icon: ShoppingCart },
          { id: "catalogue", label: "Menu", icon: UtensilsCrossed },
          { id: "promos", label: "Promos", icon: Tag },
        ].map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id as AdminTab)}
              className={`flex flex-col items-center gap-1 py-1 px-2 rounded-xl ${
                isActive ? "text-brand-tangerine font-bold" : "text-brand-ivory/70"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Price Update Modal */}
      {isPriceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 space-y-4 shadow-2xl border border-brand-sage">
            <h3 className="font-heading font-bold text-base text-brand-charcoal">
              Edit Price: {priceItemName}
            </h3>
            <div>
              <label className="block text-xs text-brand-charcoal-muted mb-1">New Price (₹)</label>
              <input
                type="number"
                value={newPrice}
                onChange={(e) => setNewPrice(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-xl border border-brand-sage text-sm font-bold"
              />
            </div>
            <div>
              <label className="block text-xs text-brand-charcoal-muted mb-1">Audit Reason</label>
              <input
                type="text"
                value={priceReason}
                onChange={(e) => setPriceReason(e.target.value)}
                placeholder="Reason for change"
                className="w-full px-3 py-2 rounded-xl border border-brand-sage text-xs"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setIsPriceModalOpen(false)}
                className="flex-1 py-2 bg-brand-ivory text-brand-charcoal text-xs font-bold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdatePrice}
                className="flex-1 py-2 bg-brand-forest text-brand-ivory text-xs font-bold rounded-xl"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk CSV Modal */}
      {isBulkCsvModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-2xl border border-brand-sage">
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-bold text-base text-brand-charcoal flex items-center gap-2">
                <Upload className="w-5 h-5 text-brand-forest" />
                <span>Bulk Import Menu Items (CSV)</span>
              </h3>
              <button onClick={() => setIsBulkCsvModalOpen(false)} className="text-brand-charcoal-muted hover:text-black">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-brand-charcoal-muted">
              CSV Header Format: <code>shop_id,name,description,price,dietary,prep_time_mins,is_food</code>
            </p>
            <textarea
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              placeholder="1,Kadak Masala Chai,Cardamom infused tea,80,VEG,8,true"
              rows={6}
              className="w-full p-3 text-xs font-mono rounded-xl border border-brand-sage bg-brand-ivory/40 focus:outline-none focus:ring-2 focus:ring-brand-forest"
            />
            {csvFeedback && (
              <div className={`text-xs font-bold p-2.5 rounded-xl ${csvFeedback.startsWith("Success") ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"}`}>
                {csvFeedback}
              </div>
            )}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsBulkCsvModalOpen(false)}
                className="px-4 py-2 bg-brand-ivory text-brand-charcoal text-xs font-bold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleBulkCsv}
                disabled={!csvText.trim()}
                className="px-4 py-2 bg-brand-forest hover:bg-brand-forest-dark disabled:opacity-50 text-brand-ivory text-xs font-bold rounded-xl"
              >
                Import CSV Rows
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Menu Item Modal */}
      {isNewItemModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-brand-sage">
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-bold text-base text-brand-charcoal">
                Add New Menu Item
              </h3>
              <button onClick={() => setIsNewItemModalOpen(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-brand-charcoal-muted mb-1 font-semibold">Select Shop</label>
                <select
                  value={itemForm.shop_id}
                  onChange={(e) => setItemForm({ ...itemForm, shop_id: Number(e.target.value) })}
                  className="w-full p-2.5 rounded-xl border border-brand-sage"
                >
                  {shops.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-brand-charcoal-muted mb-1 font-semibold">Item Name</label>
                <input
                  type="text"
                  value={itemForm.name}
                  onChange={(e) => setItemForm({ ...itemForm, name: e.target.value })}
                  placeholder="e.g. Masala Chai"
                  className="w-full p-2.5 rounded-xl border border-brand-sage"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-brand-charcoal-muted mb-1 font-semibold">Price (₹)</label>
                  <input
                    type="number"
                    value={itemForm.price}
                    onChange={(e) => setItemForm({ ...itemForm, price: Number(e.target.value) })}
                    className="w-full p-2.5 rounded-xl border border-brand-sage font-bold"
                  />
                </div>
                <div>
                  <label className="block text-brand-charcoal-muted mb-1 font-semibold">Prep Lead (Mins)</label>
                  <input
                    type="number"
                    value={itemForm.prep_time_mins}
                    onChange={(e) => setItemForm({ ...itemForm, prep_time_mins: Number(e.target.value) })}
                    className="w-full p-2.5 rounded-xl border border-brand-sage"
                  />
                </div>
              </div>
              <div>
                <label className="block text-brand-charcoal-muted mb-1 font-semibold">Dietary Label</label>
                <select
                  value={itemForm.dietary}
                  onChange={(e) => setItemForm({ ...itemForm, dietary: e.target.value })}
                  className="w-full p-2.5 rounded-xl border border-brand-sage"
                >
                  <option value="VEG">VEG</option>
                  <option value="NON_VEG">NON_VEG</option>
                  <option value="EGG">EGG</option>
                  <option value="NONE">NONE</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setIsNewItemModalOpen(false)}
                className="flex-1 py-2 bg-brand-ivory text-brand-charcoal text-xs font-bold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateMenuItem}
                disabled={!itemForm.name.trim()}
                className="flex-1 py-2 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory text-xs font-bold rounded-xl"
              >
                Save Item
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Coupon Modal */}
      {isCouponModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 space-y-4 shadow-2xl border border-brand-sage">
            <h3 className="font-heading font-bold text-base text-brand-charcoal">
              Create Promo Coupon
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-brand-charcoal-muted mb-1 font-semibold">Coupon Code</label>
                <input
                  type="text"
                  value={couponForm.code}
                  onChange={(e) => setCouponForm({ ...couponForm, code: e.target.value.toUpperCase() })}
                  placeholder="e.g. MEGAPOLIS30"
                  className="w-full p-2.5 rounded-xl border border-brand-sage font-mono uppercase font-bold"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-brand-charcoal-muted mb-1 font-semibold">Discount Type</label>
                  <select
                    value={couponForm.discount_type}
                    onChange={(e) => setCouponForm({ ...couponForm, discount_type: e.target.value })}
                    className="w-full p-2.5 rounded-xl border border-brand-sage"
                  >
                    <option value="FLAT">FLAT (₹)</option>
                    <option value="PERCENTAGE">PERCENT (%)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-brand-charcoal-muted mb-1 font-semibold">Value</label>
                  <input
                    type="number"
                    value={couponForm.discount_value}
                    onChange={(e) => setCouponForm({ ...couponForm, discount_value: Number(e.target.value) })}
                    className="w-full p-2.5 rounded-xl border border-brand-sage font-bold"
                  />
                </div>
              </div>
              <div>
                <label className="block text-brand-charcoal-muted mb-1 font-semibold">Min Order Amount (₹)</label>
                <input
                  type="number"
                  value={couponForm.min_order_amount}
                  onChange={(e) => setCouponForm({ ...couponForm, min_order_amount: Number(e.target.value) })}
                  className="w-full p-2.5 rounded-xl border border-brand-sage"
                />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setIsCouponModalOpen(false)}
                className="flex-1 py-2 bg-brand-ivory text-brand-charcoal text-xs font-bold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCoupon}
                disabled={!couponForm.code.trim()}
                className="flex-1 py-2 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory text-xs font-bold rounded-xl"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Banner Modal */}
      {isBannerModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-white rounded-3xl max-w-sm w-full p-6 space-y-4 shadow-2xl border border-brand-sage">
            <h3 className="font-heading font-bold text-base text-brand-charcoal">
              Add Promotional Banner
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-brand-charcoal-muted mb-1 font-semibold">Title</label>
                <input
                  type="text"
                  value={bannerForm.title}
                  onChange={(e) => setBannerForm({ ...bannerForm, title: e.target.value })}
                  placeholder="e.g. Afternoon Chai Break"
                  className="w-full p-2.5 rounded-xl border border-brand-sage font-semibold"
                />
              </div>
              <div>
                <label className="block text-brand-charcoal-muted mb-1 font-semibold">Subtitle</label>
                <input
                  type="text"
                  value={bannerForm.subtitle}
                  onChange={(e) => setBannerForm({ ...bannerForm, subtitle: e.target.value })}
                  placeholder="e.g. Freshly brewed to desk in 15 mins"
                  className="w-full p-2.5 rounded-xl border border-brand-sage"
                />
              </div>
              <div>
                <label className="block text-brand-charcoal-muted mb-1 font-semibold">Image URL</label>
                <input
                  type="text"
                  value={bannerForm.image_url}
                  onChange={(e) => setBannerForm({ ...bannerForm, image_url: e.target.value })}
                  placeholder="https://..."
                  className="w-full p-2.5 rounded-xl border border-brand-sage"
                />
              </div>
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setIsBannerModalOpen(false)}
                className="flex-1 py-2 bg-brand-ivory text-brand-charcoal text-xs font-bold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateBanner}
                disabled={!bannerForm.title.trim()}
                className="flex-1 py-2 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory text-xs font-bold rounded-xl"
              >
                Publish Banner
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
