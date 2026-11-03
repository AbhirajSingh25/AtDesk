"use client";

import React from "react";
import { MenuItem, Shop } from "@/types";
import { useCart } from "@/lib/cart-context";
import { Plus, Minus, Clock, ShieldAlert, Sparkles, Package } from "lucide-react";

interface MenuItemCardProps {
  item: MenuItem;
  shop: Shop;
}

export function MenuItemCard({ item, shop }: MenuItemCardProps) {
  const { items, addItem, updateQuantity } = useCart();
  const cartEntry = items.find((i) => i.menuItem.id === item.id);
  const quantity = cartEntry ? cartEntry.quantity : 0;

  // 1. COMPACT ESSENTIAL PRODUCT ROW (Stationery, cables, lozenges, tissues)
  if (!item.is_food) {
    return (
      <div className="flex items-center justify-between p-3.5 bg-white rounded-2xl border border-brand-sage/80 shadow-soft hover:border-brand-forest/30 transition-all">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-sage-light flex items-center justify-center text-brand-forest shrink-0">
            <Package className="w-5 h-5" />
          </div>
          <div>
            <div className="font-heading font-semibold text-sm text-brand-charcoal">
              {item.name}
            </div>
            <div className="text-xs text-brand-charcoal-muted line-clamp-1">
              {item.description}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs font-mono font-bold text-brand-forest">
                ₹{item.price}
              </span>
              {item.portion_size && (
                <span className="text-[10px] bg-brand-ivory text-brand-charcoal-muted px-2 py-0.5 rounded-full border border-brand-sage">
                  {item.portion_size}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Quantity Controls */}
        <div className="shrink-0 ml-3">
          {quantity === 0 ? (
            <button
              onClick={() => addItem(item, shop)}
              className="px-3.5 py-1.5 bg-brand-sage-light hover:bg-brand-sage text-brand-forest font-semibold text-xs rounded-xl border border-brand-forest/20 flex items-center gap-1 transition-all active:scale-95"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>ADD</span>
            </button>
          ) : (
            <div className="flex items-center bg-brand-forest text-brand-ivory rounded-xl px-2 py-1 gap-2 shadow-sm">
              <button
                onClick={() => updateQuantity(item.id, -1)}
                className="hover:text-brand-tangerine active:scale-90"
              >
                <Minus className="w-3.5 h-3.5" />
              </button>
              <span className="font-mono text-xs font-bold w-4 text-center">
                {quantity}
              </span>
              <button
                onClick={() => updateQuantity(item.id, 1)}
                className="hover:text-brand-tangerine active:scale-90"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // 2. RICH FOOD CATALOGUE CARD (Chai, Subs, Bhature, Coffee, Bakery)
  return (
    <div className="bg-white rounded-3xl p-4 border border-brand-sage/80 shadow-soft hover:shadow-float transition-all flex flex-col justify-between">
      <div className="flex gap-3.5">
        {/* Left Information */}
        <div className="flex-1">
          {/* Dietary Indicator */}
          <div className="flex items-center gap-1.5 mb-1.5">
            {item.dietary === "VEG" && (
              <span className="w-3.5 h-3.5 rounded border border-emerald-600 flex items-center justify-center">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
              </span>
            )}
            {item.dietary === "NON_VEG" && (
              <span className="w-3.5 h-3.5 rounded border border-rose-600 flex items-center justify-center">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-600" />
              </span>
            )}
            {item.dietary === "EGG" && (
              <span className="w-3.5 h-3.5 rounded border border-amber-600 flex items-center justify-center">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
              </span>
            )}
            <span className="text-[10px] text-brand-charcoal-muted font-medium">
              {item.portion_size || "Serves 1"}
            </span>
          </div>

          <h4 className="font-heading font-bold text-sm text-brand-charcoal leading-snug">
            {item.name}
          </h4>

          <div className="text-sm font-mono font-bold text-brand-forest mt-1">
            ₹{item.price}
          </div>

          {item.description && (
            <p className="text-xs text-brand-charcoal-muted/90 mt-1.5 line-clamp-2 leading-relaxed">
              {item.description}
            </p>
          )}

          <div className="flex items-center gap-2 mt-2 text-[10px] text-brand-charcoal-muted">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-brand-forest" />
              {item.prep_time_mins}m prep
            </span>
            <span>•</span>
            <span className="text-brand-forest font-medium">{shop.name}</span>
          </div>
        </div>

        {/* Right Photo & Action */}
        <div className="shrink-0 flex flex-col items-center justify-between w-28">
          {item.image_url ? (
            <div className="w-24 h-24 rounded-2xl overflow-hidden bg-brand-ivory relative border border-brand-sage">
              <img
                src={item.image_url}
                alt={item.name}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            </div>
          ) : (
            <div className="w-24 h-24 rounded-2xl bg-brand-sage-light flex items-center justify-center text-brand-forest">
              <Sparkles className="w-6 h-6" />
            </div>
          )}

          {/* Quantity Stepper */}
          <div className="mt-2 w-full">
            {quantity === 0 ? (
              <button
                onClick={() => addItem(item, shop)}
                className="w-full py-1.5 bg-brand-ivory hover:bg-brand-sage-light text-brand-forest font-heading font-bold text-xs rounded-xl border border-brand-forest/20 shadow-sm flex items-center justify-center gap-1 transition-all active:scale-95"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>ADD</span>
              </button>
            ) : (
              <div className="w-full flex items-center justify-between bg-brand-forest text-brand-ivory rounded-xl px-2.5 py-1.5 shadow-sm">
                <button
                  onClick={() => updateQuantity(item.id, -1)}
                  className="hover:text-brand-tangerine active:scale-90"
                >
                  <Minus className="w-3.5 h-3.5" />
                </button>
                <span className="font-mono text-xs font-bold">{quantity}</span>
                <button
                  onClick={() => updateQuantity(item.id, 1)}
                  className="hover:text-brand-tangerine active:scale-90"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

