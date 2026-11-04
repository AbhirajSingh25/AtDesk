"use client";

import React, { useState, useEffect } from "react";
import { Shop, MenuItem, MasterOrder, PromoBanner } from "@/types";
import { useCart } from "@/lib/cart-context";
import { fetchApi } from "@/lib/api";
import { MenuItemCard } from "./MenuItemCard";
import { MultiShopCartDrawer } from "./MultiShopCartDrawer";
import { PaymentModal } from "./PaymentModal";
import { LiveOrderTracker } from "./LiveOrderTracker";
import { DeskLocationModal } from "./DeskLocationModal";
import { ShopDetailModal } from "./ShopDetailModal";
import { 
  Search, MapPin, ShoppingBag, Sparkles, Clock, 
  Store, Coffee, Utensils, Zap, Package, ArrowRight,
  Flame, Tag, ChevronRight, Check
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
  const [bestsellers, setBestsellers] = useState<MenuItem[]>([]);
  const [banners, setBanners] = useState<PromoBanner[]>([]);
  const [selectedShopForModal, setSelectedShopForModal] = useState<Shop | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isPaymentOpen, setIsPaymentOpen] = useState(false);
  const [isLocationModalOpen, setIsLocationModalOpen] = useState(false);
  const [isShopDetailOpen, setIsShopDetailOpen] = useState(false);
  const [scheduledWindow, setScheduledWindow] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(true);

  // Load shops, banners, and bestsellers from backend
  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const [rawShops, loadedBanners, loadedBestsellers] = await Promise.all([
          fetchApi<Shop[]>("/shops").catch(() => []),
          fetchApi<PromoBanner[]>("/orders/banners").catch(() => []),
          fetchApi<MenuItem[]>("/shops/bestsellers").catch(() => []),
        ]);

        // Load detailed items for each shop
        const fullShops = await Promise.all(
          rawShops.map((s) => fetchApi<Shop>(`/shops/${s.id}`).catch(() => s))
        );

        setShops(fullShops);
        setBanners(loadedBanners);
        setBestsellers(loadedBestsellers);
      } catch (e) {
        console.error("Failed to load initial customer app data", e);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const totalCartCount = items.reduce((sum, i) => sum + i.quantity, 0);

  // Gather all items across shops
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
      {/* Top Hero Bar & Location Header */}
      <div className="bg-brand-forest text-brand-ivory px-4 pt-5 pb-7 rounded-b-[2.5rem] shadow-md border-b border-brand-forest-dark">
        <div className="max-w-md mx-auto space-y-3.5">
          {/* Brand & Campus Identity */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-brand-sage text-brand-forest font-heading font-extrabold flex items-center justify-center text-sm shadow-sm">
                @
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="font-heading font-extrabold text-base tracking-tight text-white">
                    AtDesk
                  </span>
                  <span className="text-[10px] bg-brand-forest-dark border border-brand-forest-light/30 text-brand-sage px-1.5 py-0.2 rounded font-medium">
                    JMD Megapolis
                  </span>
                </div>
                <div className="text-[9px] text-brand-sage/80 font-sans">
                  A product of The Sorted Club
                </div>
              </div>
            </div>

            <button
              onClick={() => setIsCartOpen(true)}
              className="relative p-2.5 rounded-2xl bg-brand-forest-dark/80 border border-brand-forest-light/40 text-brand-sage hover:text-white"
            >
              <ShoppingBag className="w-4 h-4" />
              {totalCartCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-brand-tangerine text-brand-charcoal text-[10px] font-bold flex items-center justify-center shadow-xs">
                  {totalCartCount}
                </span>
              )}
            </button>
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
                  {deskLocation.company} • Direct desk delivery
                </div>
              </div>
            </div>
            <span className="text-[11px] text-brand-tangerine font-semibold underline shrink-0">
              Change
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

      <div className="max-w-md mx-auto px-4 mt-4 space-y-6">
        {/* Promotional Banners Carousel */}
        {banners.length > 0 && (
          <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-none snap-x">
            {banners.map((banner) => (
              <div
                key={banner.id}
                className="min-w-[280px] max-w-[280px] h-32 rounded-2xl overflow-hidden relative shadow-soft border border-brand-sage/80 shrink-0 snap-center"
              >
                <img
                  src={banner.image_url}
                  alt={banner.title}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent p-3 flex flex-col justify-end text-white">
                  {banner.badge_text && (
                    <span className="self-start text-[9px] font-bold bg-brand-tangerine text-brand-charcoal px-2 py-0.5 rounded-full mb-1">
                      {banner.badge_text}
                    </span>
                  )}
                  <h4 className="font-heading font-extrabold text-sm leading-tight text-white">
                    {banner.title}
                  </h4>
                  {banner.subtitle && (
                    <p className="text-[10px] text-white/80 mt-0.5">
                      {banner.subtitle}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Category Filter Pills (Swiggy Shortcuts) */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none text-xs">
          {[
            { id: "ALL", label: "All Items", icon: Sparkles },
            { id: "FOOD", label: "Food & Meals", icon: Utensils },
            { id: "BEVERAGES", label: "Chai & Coffee", icon: Coffee },
            { id: "SNACKS", label: "Snacks & Chaat", icon: Zap },
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

        {/* Multi-Shop Value Banner */}
        <div className="bg-brand-sage-light border border-brand-sage rounded-2xl p-3.5 flex items-center justify-between">
          <div className="text-xs">
            <span className="font-heading font-bold text-brand-forest block">
              Multi-Shop Single Delivery
            </span>
            <span className="text-[11px] text-brand-charcoal-muted">
              Combine tea from Chaayos, rolls from Subway, and cables from Essentials.
            </span>
          </div>
          <span className="text-xs font-mono font-bold text-brand-forest bg-white px-2.5 py-1 rounded-xl shadow-xs border border-brand-sage shrink-0 ml-2">
            ₹25 Flat Fee
          </span>
        </div>

        {/* Concourse Featured Shops */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-heading font-bold text-sm text-brand-charcoal flex items-center gap-1.5">
              <Store className="w-4 h-4 text-brand-forest" />
              <span>Concourse Kitchens (Ground Floor)</span>
            </h3>
            <span className="text-[11px] text-brand-charcoal-muted">
              {shops.length} Active
            </span>
          </div>

          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-none">
            {shops.map((shop) => (
              <div
                key={shop.id}
                onClick={() => {
                  setSelectedShopForModal(shop);
                  setIsShopDetailOpen(true);
                }}
                className="min-w-[170px] max-w-[170px] p-3 rounded-2xl border cursor-pointer transition-all bg-white shadow-soft border-brand-sage/80 hover:border-brand-forest/60 active:scale-98"
              >
                <div className="h-20 rounded-xl overflow-hidden bg-brand-ivory mb-2 relative">
                  <img
                    src={shop.image_url || "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=400"}
                    alt={shop.name}
                    className="w-full h-full object-cover"
                  />
                  <span className="absolute bottom-1 right-1 text-[9px] font-bold bg-white/90 text-brand-forest px-1.5 py-0.5 rounded shadow-xs">
                    {shop.items?.length || 0} items
                  </span>
                </div>
                <div className="font-heading font-bold text-xs text-brand-charcoal truncate">
                  {shop.name}
                </div>
                <div className="flex items-center justify-between text-[10px] text-brand-charcoal-muted mt-1">
                  <span className="flex items-center gap-0.5">
                    <Clock className="w-3 h-3 text-brand-forest" />
                    ~{shop.prep_lead_time_mins}m
                  </span>
                  <span className="text-brand-tangerine font-semibold flex items-center">
                    View <ChevronRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Campus Bestsellers Section */}
        {bestsellers.length > 0 && selectedCategory === "ALL" && !searchQuery && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-heading font-bold text-sm text-brand-charcoal flex items-center gap-1.5">
                <Flame className="w-4 h-4 text-brand-tangerine" />
                <span>Campus Bestsellers</span>
              </h3>
              <span className="text-[11px] text-brand-charcoal-muted">
                Popular today at JMD
              </span>
            </div>

            <div className="space-y-2.5">
              {bestsellers.slice(0, 4).map((item) => {
                const shop = shops.find((s) => s.id === item.shop_id) || shops[0];
                return <MenuItemCard key={`best-${item.id}`} item={item} shop={shop} />;
              })}
            </div>
          </div>
        )}

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
      <ShopDetailModal
        shop={selectedShopForModal}
        isOpen={isShopDetailOpen}
        onClose={() => setIsShopDetailOpen(false)}
        onOpenCart={() => setIsCartOpen(true)}
      />

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
