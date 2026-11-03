"use client";

import React, { useState, useEffect } from "react";
import { Shop, MenuItem, MasterOrder } from "@/types";
import { useCart } from "@/lib/cart-context";
import { fetchApi } from "@/lib/api";
import { MenuItemCard } from "./MenuItemCard";
import { MultiShopCartDrawer } from "./MultiShopCartDrawer";
import { PaymentModal } from "./PaymentModal";
import { LiveOrderTracker } from "./LiveOrderTracker";
import { DeskLocationModal } from "./DeskLocationModal";
import { 
  Search, MapPin, ShoppingBag, Sparkles, Clock, 
  Store, Coffee, Utensils, Zap, Package, ArrowRight 
} from "lucide-react";

export function EmployeeApp() {
  const {
    items,
    deskLocation,
    grandTotal,
    activeOrder,
    setActiveOrder,
  } = useCart();

  const [shops, setShops] = useState<Shop[]>([]);
  const [selectedShop, setSelectedShop] = useState<Shop | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isPaymentOpen, setIsPaymentOpen] = useState(false);
  const [isLocationModalOpen, setIsLocationModalOpen] = useState(false);
  const [scheduledWindow, setScheduledWindow] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(true);

  // Load shops and their menus
  useEffect(() => {
    async function loadShops() {
      try {
        const rawShops = await fetchApi<Shop[]>("/shops");
        // Load detailed items for each shop
        const fullShops = await Promise.all(
          rawShops.map((s) => fetchApi<Shop>(`/shops/${s.id}`))
        );
        setShops(fullShops);
        if (fullShops.length > 0) {
          setSelectedShop(fullShops[0]);
        }
      } catch (e) {
        console.error("Failed to load shops", e);
      } finally {
        setIsLoading(false);
      }
    }
    loadShops();
  }, []);

  const totalCartCount = items.reduce((sum, i) => sum + i.quantity, 0);

  // Filtered items across shops or within selected shop
  const allMenuItems: { item: MenuItem; shop: Shop }[] = [];
  shops.forEach((s) => {
    (s.items || []).forEach((itm) => {
      allMenuItems.push({ item: itm, shop: s });
    });
  });

  const filteredItems = allMenuItems.filter(({ item, shop }) => {
    const matchesSearch =
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.description && item.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
      shop.name.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory =
      selectedCategory === "ALL" ||
      (selectedCategory === "FOOD" && item.is_food && !item.name.toLowerCase().includes("chai") && !item.name.toLowerCase().includes("coffee")) ||
      (selectedCategory === "BEVERAGES" && (item.name.toLowerCase().includes("chai") || item.name.toLowerCase().includes("tea") || item.name.toLowerCase().includes("coffee") || item.name.toLowerCase().includes("latte"))) ||
      (selectedCategory === "SNACKS" && (item.name.toLowerCase().includes("chaat") || item.name.toLowerCase().includes("samosa") || item.name.toLowerCase().includes("cookie") || item.name.toLowerCase().includes("croissant") || item.name.toLowerCase().includes("bun maska"))) ||
      (selectedCategory === "ESSENTIALS" && !item.is_food);

    return matchesSearch && matchesCategory;
  });

  if (activeOrder) {
    return (
      <div className="min-h-screen bg-brand-ivory p-4 pt-6">
        <LiveOrderTracker
          order={activeOrder}
          onBackToExplore={() => setActiveOrder(null)}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-ivory pb-28">
      {/* Top Hero Bar */}
      <div className="bg-brand-forest text-brand-ivory px-4 pt-6 pb-8 rounded-b-[2.5rem] shadow-md border-b border-brand-forest-dark">
        <div className="max-w-md mx-auto space-y-4">
          {/* Greeting & Location Selector */}
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[11px] text-brand-sage font-medium tracking-wide block">
                The Sorted Club Presents
              </span>
              <h1 className="font-heading font-extrabold text-2xl text-white tracking-tight">
                Good things, to your desk.
              </h1>
            </div>

            <div className="w-10 h-10 rounded-2xl bg-brand-sage-light text-brand-forest font-bold flex items-center justify-center text-sm shadow-inner">
              AS
            </div>
          </div>

          {/* Interactive Desk Picker Pill */}
          <button
            onClick={() => setIsLocationModalOpen(true)}
            className="w-full bg-brand-forest-dark/70 hover:bg-brand-forest-dark border border-brand-forest-light/40 rounded-2xl p-3 flex items-center justify-between text-left transition-all active:scale-[0.99]"
          >
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-brand-tangerine text-brand-charcoal flex items-center justify-center shrink-0">
                <MapPin className="w-4 h-4 font-bold" />
              </div>
              <div className="text-xs">
                <div className="font-heading font-bold text-white flex items-center gap-1.5">
                  <span>{deskLocation.tower}, Floor {deskLocation.floor}</span>
                  <span className="text-[10px] bg-brand-forest px-1.5 py-0.2 rounded font-mono text-brand-sage">
                    {deskLocation.desk}
                  </span>
                </div>
                <div className="text-[10px] text-brand-sage/80 truncate max-w-[240px]">
                  {deskLocation.company} • Drop directly at office desk
                </div>
              </div>
            </div>
            <span className="text-[11px] text-brand-tangerine font-semibold underline shrink-0">
              Edit
            </span>
          </button>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-4 h-4 text-brand-charcoal-muted absolute left-3.5 top-3.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search Chai, Subway Subs, Bhature, Chargers..."
              className="w-full pl-10 pr-4 py-3 rounded-2xl bg-white text-brand-charcoal placeholder-brand-charcoal-muted text-xs shadow-soft focus:outline-none focus:ring-2 focus:ring-brand-tangerine"
            />
          </div>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 mt-5 space-y-6">
        {/* Category Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none text-xs">
          {[
            { id: "ALL", label: "All Items", icon: Sparkles },
            { id: "FOOD", label: "Food", icon: Utensils },
            { id: "BEVERAGES", label: "Chai & Coffee", icon: Coffee },
            { id: "SNACKS", label: "Snacks", icon: Zap },
            { id: "ESSENTIALS", label: "Desk Essentials", icon: Package },
          ].map((cat) => {
            const Icon = cat.icon;
            const isSelected = selectedCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-2xl font-semibold whitespace-nowrap transition-all border ${
                  isSelected
                    ? "bg-brand-forest text-brand-ivory border-brand-forest shadow-sm"
                    : "bg-white text-brand-charcoal border-brand-sage hover:bg-brand-sage-light"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isSelected ? "text-brand-tangerine" : "text-brand-forest"}`} />
                <span>{cat.label}</span>
              </button>
            );
          })}
        </div>

        {/* Multi-Shop Banner Callout */}
        <div className="bg-brand-sage-light border border-brand-sage rounded-2xl p-3.5 flex items-center justify-between">
          <div className="text-xs">
            <span className="font-heading font-bold text-brand-forest block">
              Multi-Shop Single Delivery
            </span>
            <span className="text-[11px] text-brand-charcoal-muted">
              Add tea from Chaayos, subs from Subway, and cables from Essentials. Pay flat ₹25 delivery.
            </span>
          </div>
          <span className="text-xs font-mono font-bold text-brand-forest bg-white px-2.5 py-1 rounded-xl shadow-xs border border-brand-sage shrink-0 ml-2">
            ₹25 Flat Fee
          </span>
        </div>

        {/* Popular Shops in JMD Megapolis */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-heading font-bold text-sm text-brand-charcoal">
              Concourse Shops (JMD Megapolis)
            </h3>
            <span className="text-[11px] text-brand-charcoal-muted">
              {shops.length} Active Kitchens
            </span>
          </div>

          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-none">
            {shops.map((shop) => (
              <div
                key={shop.id}
                onClick={() => setSelectedShop(shop)}
                className={`min-w-[160px] max-w-[160px] p-3 rounded-2xl border cursor-pointer transition-all bg-white shadow-soft ${
                  selectedShop?.id === shop.id
                    ? "border-brand-forest ring-2 ring-brand-forest/20"
                    : "border-brand-sage/80 hover:border-brand-forest/40"
                }`}
              >
                <div className="h-16 rounded-xl overflow-hidden bg-brand-ivory mb-2">
                  <img
                    src={shop.image_url || "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=400"}
                    alt={shop.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="font-heading font-bold text-xs text-brand-charcoal truncate">
                  {shop.name}
                </div>
                <div className="flex items-center gap-1 text-[10px] text-brand-charcoal-muted mt-0.5">
                  <Clock className="w-3 h-3 text-brand-forest" />
                  <span>~{shop.prep_lead_time_mins}m prep</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Menu Items List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-heading font-bold text-sm text-brand-charcoal">
              Available Items ({filteredItems.length})
            </h3>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="text-xs text-brand-forest underline font-semibold"
              >
                Clear Search
              </button>
            )}
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-28 bg-white/60 animate-pulse rounded-3xl" />
              ))}
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="p-8 text-center bg-white rounded-3xl border border-brand-sage text-brand-charcoal-muted text-xs">
              No matching items found for your search.
            </div>
          ) : (
            <div className="space-y-3">
              {filteredItems.map(({ item, shop }) => (
                <MenuItemCard key={item.id} item={item} shop={shop} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Floating Bottom Cart Bar */}
      {items.length > 0 && (
        <div className="fixed bottom-3 inset-x-0 z-40 px-4">
          <div className="max-w-md mx-auto">
            <button
              onClick={() => setIsCartOpen(true)}
              className="w-full py-3.5 px-5 bg-brand-forest text-brand-ivory rounded-2xl shadow-float flex items-center justify-between transition-all active:scale-[0.99] border border-brand-forest-dark"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-brand-sage text-brand-forest flex items-center justify-center font-bold text-xs">
                  {totalCartCount}
                </div>
                <div className="text-left">
                  <div className="text-xs font-heading font-bold">
                    View Multi-Shop Cart
                  </div>
                  <div className="text-[10px] text-brand-sage">
                    {deskLocation.desk} • Flat ₹25 Delivery
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-sm">₹{grandTotal}</span>
                <ArrowRight className="w-4 h-4 text-brand-tangerine" />
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Modals & Drawers */}
      <MultiShopCartDrawer
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        onProceedToPayment={(slot) => {
          setScheduledWindow(slot);
          setIsCartOpen(false);
          setIsPaymentOpen(true);
        }}
        onEditLocation={() => setIsLocationModalOpen(true)}
      />

      <PaymentModal
        isOpen={isPaymentOpen}
        onClose={() => setIsPaymentOpen(false)}
        scheduledWindow={scheduledWindow}
        onSuccess={(confirmedOrder) => {
          setActiveOrder(confirmedOrder);
        }}
      />

      <DeskLocationModal
        isOpen={isLocationModalOpen}
        onClose={() => setIsLocationModalOpen(false)}
      />
    </div>
  );
}

