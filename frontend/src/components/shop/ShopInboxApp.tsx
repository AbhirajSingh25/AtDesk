"use client";

import React, { useState, useEffect } from "react";
import { fetchApi } from "@/lib/api";
import { Shop, MenuItem, VendorOrder } from "@/types";
import { 
  Store, Clock, CheckCircle2, AlertCircle, ChefHat, 
  PackageCheck, XCircle, RefreshCw, Power, Flame,
  Check, X, Volume2, ShieldCheck, Tag
} from "lucide-react";

interface ShopInboxStats {
  shop_name: string;
  total_orders_today: number;
  completed_today: number;
  avg_prep_time_mins: number;
}

export function ShopInboxApp() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [selectedShopId, setSelectedShopId] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<"ORDERS" | "MENU" | "STATS">("ORDERS");
  const [orders, setOrders] = useState<VendorOrder[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [stats, setStats] = useState<ShopInboxStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Load available shops
  useEffect(() => {
    async function getShops() {
      try {
        const list = await fetchApi<Shop[]>("/shops");
        setShops(list);
        if (list.length > 0) {
          setSelectedShopId(list[0].id);
        }
      } catch (e) {
        console.error("Failed to load shops", e);
      }
    }
    getShops();
  }, []);

  // Poll orders & menu for selected shop
  const loadShopData = async () => {
    if (!selectedShopId) return;
    setIsLoading(true);
    setActionError(null);
    try {
      const [fetchedOrders, fetchedMenu, fetchedStats] = await Promise.all([
        fetchApi<VendorOrder[]>(`/shop-inbox/orders?shop_id=${selectedShopId}`).catch(() => []),
        fetchApi<MenuItem[]>(`/shop-inbox/menu?shop_id=${selectedShopId}`).catch(() => []),
        fetchApi<ShopInboxStats>(`/shop-inbox/stats?shop_id=${selectedShopId}`).catch(() => null),
      ]);
      setOrders(fetchedOrders);
      setMenuItems(fetchedMenu);
      setStats(fetchedStats);
    } catch (e: any) {
      console.error("Error loading shop inbox", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadShopData();
    const interval = setInterval(loadShopData, 5000);
    return () => clearInterval(interval);
  }, [selectedShopId]);

  // Action handlers
  const handleAcceptOrder = async (orderId: number, prepTime: number) => {
    try {
      await fetchApi(`/shop-inbox/orders/${orderId}/accept?shop_id=${selectedShopId}`, {
        method: "POST",
        body: JSON.stringify({ prep_time_mins: prepTime }),
      });
      await loadShopData();
    } catch (e: any) {
      setActionError(e.message || "Failed to accept order");
    }
  };

  const handleMarkPreparing = async (orderId: number) => {
    try {
      await fetchApi(`/shop-inbox/orders/${orderId}/mark-preparing?shop_id=${selectedShopId}`, {
        method: "POST",
      });
      await loadShopData();
    } catch (e: any) {
      setActionError(e.message || "Failed to update status");
    }
  };

  const handleMarkReady = async (orderId: number) => {
    try {
      await fetchApi(`/shop-inbox/orders/${orderId}/mark-ready?shop_id=${selectedShopId}`, {
        method: "POST",
      });
      await loadShopData();
    } catch (e: any) {
      setActionError(e.message || "Failed to mark ready");
    }
  };

  const handleRejectOrder = async (orderId: number) => {
    const reason = prompt("Reason for rejection (e.g. Ingredients Out of Stock):", "Item out of stock");
    if (!reason) return;
    try {
      await fetchApi(`/shop-inbox/orders/${orderId}/reject?shop_id=${selectedShopId}`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      await loadShopData();
    } catch (e: any) {
      setActionError(e.message || "Failed to reject order");
    }
  };

  const handleToggleItemAvailability = async (itemId: number, currentAvailable: boolean) => {
    try {
      await fetchApi(`/shop-inbox/menu/${itemId}/toggle-availability?shop_id=${selectedShopId}`, {
        method: "POST",
        body: JSON.stringify({ is_available: !currentAvailable }),
      });
      setMenuItems((prev) =>
        prev.map((i) => (i.id === itemId ? { ...i, is_available: !currentAvailable } : i))
      );
    } catch (e: any) {
      setActionError(e.message || "Failed to toggle item availability");
    }
  };

  const currentShop = shops.find((s) => s.id === selectedShopId) || shops[0];
  const pendingOrders = orders.filter((o) => o.status === "PENDING");
  const inKitchenOrders = orders.filter((o) => o.status === "ACCEPTED" || o.status === "PREPARING");
  const readyOrders = orders.filter((o) => o.status === "READY_FOR_PICKUP");

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 pb-20 font-sans">
      {/* Top Concourse Staff Bar */}
      <div className="bg-slate-950 border-b border-slate-800 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-4xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-brand-forest text-brand-sage flex items-center justify-center font-bold shadow-sm">
              <ChefHat className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-heading font-extrabold text-sm text-white">
                  Shop Order Inbox
                </h1>
                <span className="text-[10px] bg-slate-800 text-emerald-400 px-2 py-0.5 rounded-full border border-slate-700 font-mono">
                  LIVE CONCOURSE
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                AtDesk Kitchen Tablet & Mobile Order Receiver
              </p>
            </div>
          </div>

          {/* Shop Switcher Dropdown */}
          <div className="flex items-center gap-2">
            <select
              value={selectedShopId}
              onChange={(e) => setSelectedShopId(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 text-white text-xs font-semibold rounded-xl px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              {shops.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.location_details})
                </option>
              ))}
            </select>

            <button
              onClick={loadShopData}
              className="p-1.5 rounded-xl border border-slate-700 bg-slate-800 text-slate-300 hover:text-white"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-4 space-y-4">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
          <button
            onClick={() => setActiveTab("ORDERS")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === "ORDERS"
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-slate-800/80 text-slate-400 hover:text-white"
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Active Orders ({orders.length})</span>
            {pendingOrders.length > 0 && (
              <span className="w-5 h-5 rounded-full bg-amber-500 text-slate-950 text-[10px] font-extrabold flex items-center justify-center animate-pulse">
                {pendingOrders.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("MENU")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === "MENU"
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-slate-800/80 text-slate-400 hover:text-white"
            }`}
          >
            <Tag className="w-3.5 h-3.5" />
            <span>Menu & Stock 86 ({menuItems.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("STATS")}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeTab === "STATS"
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-slate-800/80 text-slate-400 hover:text-white"
            }`}
          >
            <Flame className="w-3.5 h-3.5" />
            <span>Kitchen Stats</span>
          </button>
        </div>

        {/* Global Action Error Alert */}
        {actionError && (
          <div className="p-3 bg-rose-950/60 border border-rose-800 text-rose-300 rounded-xl text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{actionError}</span>
            </div>
            <button onClick={() => setActionError(null)} className="text-rose-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* TAB 1: ACTIVE ORDERS */}
        {activeTab === "ORDERS" && (
          <div className="space-y-6">
            {/* 1. Pending Acceptance Orders */}
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs font-heading font-bold text-amber-400">
                <span className="flex items-center gap-1.5">
                  <Volume2 className="w-4 h-4 animate-bounce" />
                  New Incoming Orders ({pendingOrders.length})
                </span>
                <span className="text-[11px] text-slate-400">
                  Accept within 3 mins
                </span>
              </div>

              {pendingOrders.length === 0 ? (
                <div className="p-6 bg-slate-800/40 rounded-2xl border border-slate-800 text-center text-xs text-slate-500">
                  No new pending orders waiting.
                </div>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {pendingOrders.map((order) => (
                    <div
                      key={order.id}
                      className="bg-slate-800 border-2 border-amber-500/80 rounded-2xl p-4 space-y-3 shadow-lg"
                    >
                      <div className="flex items-center justify-between border-b border-slate-700 pb-2">
                        <div>
                          <div className="font-heading font-extrabold text-sm text-white">
                            Order #{order.id}
                          </div>
                          <div className="text-[11px] text-slate-400">
                            Subtotal: ₹{order.shop_subtotal}
                          </div>
                        </div>
                        <span className="text-[10px] font-bold bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full border border-amber-500/40">
                          PENDING ACCEPTANCE
                        </span>
                      </div>

                      {/* Items List */}
                      <div className="space-y-1.5 text-xs">
                        {order.order_items?.map((item) => (
                          <div key={item.id} className="flex justify-between text-slate-200">
                            <span>
                              {item.quantity} × {item.item_name}
                            </span>
                            <span className="font-mono text-slate-400">₹{item.subtotal}</span>
                          </div>
                        ))}
                      </div>

                      {/* Accept with prep time selector */}
                      <div className="pt-2 border-t border-slate-700/80 space-y-2">
                        <span className="text-[10px] text-slate-400 font-bold block">
                          Set Prep Time & Accept:
                        </span>
                        <div className="grid grid-cols-4 gap-1.5">
                          {[5, 10, 15, 20].map((mins) => (
                            <button
                              key={mins}
                              onClick={() => handleAcceptOrder(order.id, mins)}
                              className="py-1.5 bg-emerald-700 hover:bg-emerald-600 text-white font-bold text-xs rounded-xl transition-all active:scale-95 text-center"
                            >
                              {mins}m
                            </button>
                          ))}
                        </div>

                        <button
                          onClick={() => handleRejectOrder(order.id)}
                          className="w-full py-1.5 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-semibold rounded-xl text-center"
                        >
                          Reject (Out of Stock)
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 2. Kitchen Preparation Queue */}
            <div className="space-y-3">
              <h3 className="text-xs font-heading font-bold text-slate-300 flex items-center gap-1.5">
                <ChefHat className="w-4 h-4 text-emerald-400" />
                Kitchen Preparation Queue ({inKitchenOrders.length})
              </h3>

              {inKitchenOrders.length === 0 ? (
                <div className="p-6 bg-slate-800/40 rounded-2xl border border-slate-800 text-center text-xs text-slate-500">
                  Kitchen queue is clear.
                </div>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {inKitchenOrders.map((order) => (
                    <div
                      key={order.id}
                      className="bg-slate-800 rounded-2xl p-4 border border-slate-700 space-y-3"
                    >
                      <div className="flex items-center justify-between border-b border-slate-700 pb-2">
                        <div>
                          <div className="font-heading font-bold text-sm text-white">
                            Order #{order.id}
                          </div>
                          <div className="text-[11px] text-slate-400">
                            Prep lead: ~{order.estimated_prep_time_mins} mins
                          </div>
                        </div>
                        <span className="text-[10px] font-bold bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full border border-blue-500/40">
                          {order.status}
                        </span>
                      </div>

                      {/* Items */}
                      <div className="space-y-1 text-xs">
                        {order.order_items?.map((item) => (
                          <div key={item.id} className="flex justify-between text-slate-200">
                            <span>
                              {item.quantity} × {item.item_name}
                            </span>
                            <span className="font-mono text-slate-400">₹{item.subtotal}</span>
                          </div>
                        ))}
                      </div>

                      {/* Action buttons */}
                      <div className="pt-2 border-t border-slate-700 flex gap-2">
                        {order.status === "ACCEPTED" && (
                          <button
                            onClick={() => handleMarkPreparing(order.id)}
                            className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-xl"
                          >
                            Mark Preparing
                          </button>
                        )}
                        <button
                          onClick={() => handleMarkReady(order.id)}
                          className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 shadow-md"
                        >
                          <PackageCheck className="w-4 h-4" />
                          <span>Mark Ready for Pickup</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 3. Ready for Runner Pickup */}
            <div className="space-y-3">
              <h3 className="text-xs font-heading font-bold text-slate-300 flex items-center gap-1.5">
                <PackageCheck className="w-4 h-4 text-emerald-400" />
                Waiting for Campus Runner Pickup ({readyOrders.length})
              </h3>

              {readyOrders.length === 0 ? (
                <div className="p-6 bg-slate-800/40 rounded-2xl border border-slate-800 text-center text-xs text-slate-500">
                  No orders waiting for runner.
                </div>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {readyOrders.map((order) => (
                    <div
                      key={order.id}
                      className="bg-emerald-950/30 rounded-2xl p-4 border border-emerald-800/60 flex items-center justify-between"
                    >
                      <div>
                        <div className="font-heading font-bold text-sm text-white">
                          Order #{order.id}
                        </div>
                        <div className="text-xs text-emerald-300">
                          Packaged & Waiting for runner collection
                        </div>
                      </div>
                      <span className="text-xs font-mono font-bold bg-emerald-900 text-emerald-200 px-3 py-1 rounded-xl border border-emerald-700">
                        READY
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: MENU & 86 STOCK AVAILABILITY TOGGLE */}
        {activeTab === "MENU" && (
          <div className="bg-slate-800/80 rounded-3xl p-4 border border-slate-700 space-y-4">
            <div>
              <h3 className="font-heading font-bold text-sm text-white">
                {currentShop?.name} Menu Availability
              </h3>
              <p className="text-xs text-slate-400">
                Toggle items off when kitchen runs out of stock (86 item). Changes update live across the employee app.
              </p>
            </div>

            <div className="divide-y divide-slate-700">
              {menuItems.map((item) => (
                <div
                  key={item.id}
                  className="py-3 flex items-center justify-between gap-3 text-xs"
                >
                  <div className="flex-1">
                    <div className="font-semibold text-white flex items-center gap-1.5">
                      <span>{item.name}</span>
                      <span className="font-mono text-slate-400">₹{item.price}</span>
                      {item.portion_size && (
                        <span className="text-[10px] text-slate-500">
                          ({item.portion_size})
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <div className="text-[11px] text-slate-400 line-clamp-1">
                        {item.description}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        item.is_available
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-700"
                          : "bg-rose-950 text-rose-300 border border-rose-800"
                      }`}
                    >
                      {item.is_available ? "In Stock" : "86'd Out"}
                    </span>

                    <button
                      onClick={() => handleToggleItemAvailability(item.id, item.is_available)}
                      className={`px-3 py-1 rounded-xl text-xs font-bold transition-all ${
                        item.is_available
                          ? "bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700"
                          : "bg-emerald-700 hover:bg-emerald-600 text-white"
                      }`}
                    >
                      {item.is_available ? "Mark Out of Stock" : "Mark Available"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: KITCHEN STATS */}
        {activeTab === "STATS" && (
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="bg-slate-800 p-4 rounded-2xl border border-slate-700 space-y-1">
              <span className="text-[11px] text-slate-400">Total Orders Today</span>
              <div className="font-heading font-extrabold text-2xl text-white">
                {stats?.total_orders_today || orders.length}
              </div>
            </div>

            <div className="bg-slate-800 p-4 rounded-2xl border border-slate-700 space-y-1">
              <span className="text-[11px] text-slate-400">Completed Orders</span>
              <div className="font-heading font-extrabold text-2xl text-emerald-400">
                {stats?.completed_today || 0}
              </div>
            </div>

            <div className="bg-slate-800 p-4 rounded-2xl border border-slate-700 space-y-1">
              <span className="text-[11px] text-slate-400">Avg Kitchen Prep Time</span>
              <div className="font-heading font-extrabold text-2xl text-amber-400">
                ~{stats?.avg_prep_time_mins || currentShop?.prep_lead_time_mins || 12} mins
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

