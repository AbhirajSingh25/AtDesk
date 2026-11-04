"use client";

import React, { useState } from "react";
import { Shop, MenuItem } from "@/types";
import { useCart } from "@/lib/cart-context";
import { 
  X, Clock, MapPin, Plus, Minus, Check, 
  Sparkles, ShieldCheck, ShoppingBag, ArrowRight 
} from "lucide-react";

interface ShopDetailModalProps {
  shop: Shop | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenCart: () => void;
}

export function ShopDetailModal({ shop, isOpen, onClose, onOpenCart }: ShopDetailModalProps) {
  const { items, addItem, updateQuantity, grandTotal } = useCart();
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  if (!isOpen || !shop) return null;

  const shopItems = shop.items || [];
  const categories = Array.from(new Set(shopItems.map((i) => i.dietary || "ALL")));

  const filteredItems = shopItems.filter((item) => {
    if (selectedCategory === "ALL") return true;
    return item.dietary === selectedCategory;
  });

  const cartItemCountForShop = items
    .filter((i) => i.shop.id === shop.id)
    .reduce((sum, i) => sum + i.quantity, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-brand-ivory rounded-3xl max-w-lg w-full max-h-[90vh] shadow-2xl overflow-hidden border border-brand-sage flex flex-col">
        {/* Cover Image & Shop Header */}
        <div className="relative h-44 shrink-0 bg-brand-forest">
          <img
            src={shop.image_url || "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=800"}
            alt={shop.name}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent" />
          
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/80 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="absolute bottom-4 left-4 right-4 text-white">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] uppercase font-bold tracking-wider bg-brand-tangerine text-brand-charcoal px-2 py-0.5 rounded-full">
                {shop.category}
              </span>
              <span className="text-[10px] bg-white/20 backdrop-blur-xs text-white px-2 py-0.5 rounded-full flex items-center gap-1 font-mono">
                <Clock className="w-3 h-3 text-brand-sage" />
                ~{shop.prep_lead_time_mins}m prep
              </span>
            </div>
            <h2 className="font-heading font-extrabold text-xl text-white">
              {shop.name}
            </h2>
            <p className="text-xs text-white/80 flex items-center gap-1 mt-0.5">
              <MapPin className="w-3 h-3 text-brand-tangerine" />
              {shop.location_details}
            </p>
          </div>
        </div>

        {/* Dietary Filter Jump Links */}
        <div className="p-3 bg-white border-b border-brand-sage flex items-center gap-2 overflow-x-auto scrollbar-none shrink-0">
          <button
            onClick={() => setSelectedCategory("ALL")}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              selectedCategory === "ALL"
                ? "bg-brand-forest text-brand-ivory"
                : "bg-brand-ivory text-brand-charcoal hover:bg-brand-sage-light"
            }`}
          >
            All Items ({shopItems.length})
          </button>
          <button
            onClick={() => setSelectedCategory("VEG")}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1 ${
              selectedCategory === "VEG"
                ? "bg-emerald-700 text-white"
                : "bg-brand-ivory text-brand-charcoal hover:bg-brand-sage-light"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-600 inline-block" />
            Pure Veg
          </button>
          <button
            onClick={() => setSelectedCategory("NON_VEG")}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1 ${
              selectedCategory === "NON_VEG"
                ? "bg-red-700 text-white"
                : "bg-brand-ivory text-brand-charcoal hover:bg-brand-sage-light"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-red-600 inline-block" />
            Non-Veg
          </button>
        </div>

        {/* Menu Items Scrollable Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {filteredItems.length === 0 ? (
            <div className="py-12 text-center text-xs text-brand-charcoal-muted">
              No items available in this category.
            </div>
          ) : (
            filteredItems.map((item) => {
              const inCart = items.find((i) => i.menuItem.id === item.id);
              const qty = inCart ? inCart.quantity : 0;

              return (
                <div
                  key={item.id}
                  className="bg-white rounded-2xl p-3.5 border border-brand-sage/80 shadow-soft flex items-center justify-between gap-3"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`w-3.5 h-3.5 border rounded-xs flex items-center justify-center shrink-0 ${
                          item.dietary === "VEG"
                            ? "border-emerald-600"
                            : item.dietary === "NON_VEG"
                            ? "border-red-600"
                            : "border-amber-600"
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            item.dietary === "VEG"
                              ? "bg-emerald-600"
                              : item.dietary === "NON_VEG"
                              ? "bg-red-600"
                              : "bg-amber-600"
                          }`}
                        />
                      </span>
                      <span className="font-heading font-bold text-xs text-brand-charcoal">
                        {item.name}
                      </span>
                    </div>

                    {item.description && (
                      <p className="text-[11px] text-brand-charcoal-muted line-clamp-2 mb-1.5">
                        {item.description}
                      </p>
                    )}

                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono font-bold text-brand-forest">
                        ₹{item.price}
                      </span>
                      {item.portion_size && (
                        <span className="text-[10px] text-brand-charcoal-muted">
                          • {item.portion_size}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col items-center gap-2 shrink-0">
                    {item.image_url && (
                      <div className="w-16 h-16 rounded-xl overflow-hidden bg-brand-ivory border border-brand-sage/60">
                        <img
                          src={item.image_url}
                          alt={item.name}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    )}

                    {!item.is_available ? (
                      <span className="text-[10px] font-bold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                        Sold Out
                      </span>
                    ) : qty === 0 ? (
                      <button
                        onClick={() => addItem(item, shop)}
                        className="px-3.5 py-1.5 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory font-bold text-xs rounded-xl shadow-xs transition-all active:scale-95 flex items-center gap-1"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add</span>
                      </button>
                    ) : (
                      <div className="flex items-center bg-brand-forest text-brand-ivory rounded-xl px-2 py-1 gap-2 shadow-xs">
                        <button
                          onClick={() => updateQuantity(item.id, -1)}
                          className="hover:text-brand-tangerine transition-colors active:scale-90"
                        >
                          <Minus className="w-3 h-3" />
                        </button>
                        <span className="font-mono text-xs font-bold w-4 text-center">
                          {qty}
                        </span>
                        <button
                          onClick={() => updateQuantity(item.id, 1)}
                          className="hover:text-brand-tangerine transition-colors active:scale-90"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Floating Cart Pill at Bottom */}
        {cartItemCountForShop > 0 && (
          <div className="p-3 bg-white border-t border-brand-sage flex items-center justify-between">
            <div className="text-xs">
              <span className="font-bold text-brand-charcoal block">
                {cartItemCountForShop} {cartItemCountForShop === 1 ? "item" : "items"} in cart
              </span>
              <span className="text-[10px] text-brand-charcoal-muted">
                Multi-Shop Total: ₹{grandTotal} (inc. ₹25 delivery)
              </span>
            </div>

            <button
              onClick={() => {
                onClose();
                onOpenCart();
              }}
              className="px-4 py-2 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory text-xs font-bold rounded-xl flex items-center gap-1.5 shadow-md active:scale-95"
            >
              <span>View Cart</span>
              <ArrowRight className="w-3.5 h-3.5 text-brand-tangerine" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

