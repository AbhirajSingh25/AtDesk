"use client";

import React, { useState, useEffect } from "react";
import { useCart } from "@/lib/cart-context";
import { 
  ShoppingBag, X, Plus, Minus, Clock, MapPin, 
  ArrowRight, ShieldCheck, Sparkles, Calendar 
} from "lucide-react";
import { fetchApi } from "@/lib/api";

interface MultiShopCartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onProceedToPayment: (scheduledWindow?: string) => void;
  onEditLocation: () => void;
}

export function MultiShopCartDrawer({
  isOpen,
  onClose,
  onProceedToPayment,
  onEditLocation,
}: MultiShopCartDrawerProps) {
  const {
    items,
    itemsGroupedByShop,
    itemsSubtotal,
    flatDeliveryFee,
    discountAmount,
    appliedCoupon,
    applyCoupon,
    removeCoupon,
    grandTotal,
    deskLocation,
    updateQuantity,
    clearCart,
  } = useCart();

  const [deliveryMode, setDeliveryMode] = useState<"NOW" | "SCHEDULED">("NOW");
  const [selectedSlot, setSelectedSlot] = useState("13:00 - 13:30 (Lunch Peak)");
  const [etaPreview, setEtaPreview] = useState<string>("25 - 35 mins");
  const [isLoadingEta, setIsLoadingEta] = useState(false);
  const [couponInput, setCouponInput] = useState("");
  const [couponFeedback, setCouponFeedback] = useState<string | null>(null);
  const [isApplyingCoupon, setIsApplyingCoupon] = useState(false);

  const handleApplyCoupon = async () => {
    if (!couponInput.trim()) return;
    setIsApplyingCoupon(true);
    setCouponFeedback(null);
    try {
      const res = await applyCoupon(couponInput.trim());
      if (res.success) {
        setCouponFeedback(`Success: ${res.message}`);
        setCouponInput("");
      } else {
        setCouponFeedback(res.message);
      }
    } finally {
      setIsApplyingCoupon(false);
    }
  };

  // Fetch dynamic ETA preview when items or desk change
  useEffect(() => {
    if (items.length === 0) return;

    let isMounted = true;
    async function getEta() {
      setIsLoadingEta(true);
      try {
        const payload = {
          items: items.map((i) => ({ menu_item_id: i.menuItem.id, quantity: i.quantity })),
          tower: deskLocation.tower,
          floor: deskLocation.floor,
          desk_location: deskLocation.desk,
        };
        const res = await fetchApi<{ estimated_arrival_window: string }>(
          "/orders/calculate-preview",
          {
            method: "POST",
            body: JSON.stringify(payload),
          }
        );
        if (isMounted && res.estimated_arrival_window) {
          setEtaPreview(res.estimated_arrival_window);
        }
      } catch (err) {
        // fallback
        setEtaPreview("25 - 35 mins");
      } finally {
        if (isMounted) setIsLoadingEta(false);
      }
    }
    getEta();
    return () => {
      isMounted = false;
    };
  }, [items, deskLocation]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-brand-ivory w-full max-w-md h-full flex flex-col shadow-sheet overflow-hidden border-l border-brand-sage animate-in slide-in-from-right duration-300">
        {/* Drawer Header */}
        <div className="bg-brand-forest text-brand-ivory px-5 py-4 flex items-center justify-between border-b border-brand-forest-dark">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-brand-sage text-brand-forest flex items-center justify-center font-bold">
              <ShoppingBag className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-heading font-bold text-base">Your Multi-Shop Cart</h3>
              <p className="text-[11px] text-brand-sage/80">
                {itemsGroupedByShop.length} {itemsGroupedByShop.length === 1 ? "Shop" : "Shops"} • One Delivery
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-brand-sage hover:bg-brand-forest-dark transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Area */}
        {items.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
            <div className="w-16 h-16 rounded-3xl bg-brand-sage-light flex items-center justify-center text-brand-forest mb-3">
              <ShoppingBag className="w-8 h-8 opacity-60" />
            </div>
            <h4 className="font-heading font-bold text-brand-charcoal text-base">
              Your cart is empty
            </h4>
            <p className="text-xs text-brand-charcoal-muted mt-1 max-w-xs">
              Explore food, snacks, coffees, and desk essentials from shops in JMD Megapolis.
            </p>
            <button
              onClick={onClose}
              className="mt-4 px-5 py-2.5 bg-brand-forest text-brand-ivory rounded-2xl text-xs font-semibold"
            >
              Start Exploring
            </button>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Delivery Destination Badge */}
            <div className="bg-white rounded-2xl p-3.5 border border-brand-sage/80 shadow-soft flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-brand-sage-light text-brand-forest flex items-center justify-center shrink-0">
                  <MapPin className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-brand-charcoal">
                    {deskLocation.tower}, Floor {deskLocation.floor}
                  </div>
                  <div className="text-[11px] text-brand-charcoal-muted font-mono">
                    {deskLocation.desk}
                  </div>
                </div>
              </div>
              <button
                onClick={onEditLocation}
                className="text-xs font-semibold text-brand-forest underline hover:text-brand-tangerine transition-colors"
              >
                Change
              </button>
            </div>

            {/* Delivery Scheduling Toggle */}
            <div className="bg-white rounded-2xl p-3 border border-brand-sage/80 shadow-soft">
              <div className="text-xs font-semibold text-brand-charcoal-muted mb-2 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-brand-forest" />
                <span>Delivery Window</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setDeliveryMode("NOW")}
                  className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border transition-all ${
                    deliveryMode === "NOW"
                      ? "bg-brand-forest text-brand-ivory border-brand-forest"
                      : "bg-brand-ivory/40 border-brand-sage text-brand-charcoal hover:bg-brand-sage-light"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5 text-brand-tangerine" />
                  <span>Deliver Now</span>
                </button>

                <button
                  type="button"
                  onClick={() => setDeliveryMode("SCHEDULED")}
                  className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border transition-all ${
                    deliveryMode === "SCHEDULED"
                      ? "bg-brand-forest text-brand-ivory border-brand-forest"
                      : "bg-brand-ivory/40 border-brand-sage text-brand-charcoal hover:bg-brand-sage-light"
                  }`}
                >
                  <Calendar className="w-3.5 h-3.5" />
                  <span>Schedule Later</span>
                </button>
              </div>

              {deliveryMode === "SCHEDULED" && (
                <div className="mt-2.5 pt-2.5 border-t border-brand-sage/60">
                  <label className="text-[10px] text-brand-charcoal-muted font-semibold block mb-1">
                    Select Available Office Window
                  </label>
                  <select
                    value={selectedSlot}
                    onChange={(e) => setSelectedSlot(e.target.value)}
                    className="w-full px-3 py-1.5 rounded-lg border border-brand-sage bg-brand-ivory/30 text-xs font-medium"
                  >
                    <option value="12:30 - 13:00 (Early Lunch)">12:30 - 13:00 (Early Lunch)</option>
                    <option value="13:00 - 13:30 (Lunch Peak)">13:00 - 13:30 (Lunch Peak)</option>
                    <option value="13:30 - 14:00 (Post Lunch)">13:30 - 14:00 (Post Lunch)</option>
                    <option value="16:00 - 16:30 (Tea & Snack Time)">16:00 - 16:30 (Tea & Snack Time)</option>
                    <option value="17:30 - 18:00 (Evening Fuel)">17:30 - 18:00 (Evening Fuel)</option>
                  </select>
                </div>
              )}
            </div>

            {/* Shop-wise Item Groups */}
            <div className="space-y-3">
              <div className="text-xs font-bold text-brand-charcoal-muted uppercase tracking-wider px-1">
                Items Grouped by Shop
              </div>

              {itemsGroupedByShop.map(({ shop, items: shopItems, subtotal }) => (
                <div
                  key={shop.id}
                  className="bg-white rounded-2xl p-3.5 border border-brand-sage/80 shadow-soft space-y-2.5"
                >
                  {/* Shop Header */}
                  <div className="flex items-center justify-between border-b border-brand-sage/50 pb-2">
                    <div>
                      <div className="font-heading font-bold text-xs text-brand-forest">
                        {shop.name}
                      </div>
                      <div className="text-[10px] text-brand-charcoal-muted">
                        {shop.location_details}
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-semibold bg-brand-sage-light text-brand-forest px-2 py-0.5 rounded-full border border-brand-sage">
                      ~{shop.prep_lead_time_mins}m prep
                    </span>
                  </div>

                  {/* Items in Shop */}
                  <div className="space-y-2">
                    {shopItems.map((cartItem) => (
                      <div
                        key={cartItem.menuItem.id}
                        className="flex items-center justify-between text-xs"
                      >
                        <div className="flex-1 pr-2">
                          <div className="font-medium text-brand-charcoal">
                            {cartItem.menuItem.name}
                          </div>
                          <div className="text-[11px] font-mono text-brand-charcoal-muted">
                            ₹{cartItem.menuItem.price} × {cartItem.quantity}
                          </div>
                        </div>

                        {/* Stepper */}
                        <div className="flex items-center bg-brand-ivory rounded-lg px-2 py-1 gap-2 border border-brand-sage">
                          <button
                            onClick={() => updateQuantity(cartItem.menuItem.id, -1)}
                            className="text-brand-forest hover:text-brand-tangerine active:scale-90"
                          >
                            <Minus className="w-3 h-3" />
                          </button>
                          <span className="font-mono text-xs font-bold w-3 text-center">
                            {cartItem.quantity}
                          </span>
                          <button
                            onClick={() => updateQuantity(cartItem.menuItem.id, 1)}
                            className="text-brand-forest hover:text-brand-tangerine active:scale-90"
                          >
                            <Plus className="w-3 h-3" />
                          </button>
                        </div>

                        <div className="w-16 text-right font-mono font-semibold text-brand-forest">
                          ₹{cartItem.menuItem.price * cartItem.quantity}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Shop Subtotal */}
                  <div className="pt-2 border-t border-brand-sage/40 flex justify-between text-xs text-brand-charcoal-muted">
                    <span>Shop Subtotal</span>
                    <span className="font-mono font-semibold text-brand-charcoal">
                      ₹{subtotal}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Coupon Code Section */}
            <div className="bg-white rounded-2xl p-3.5 border border-brand-sage/80 shadow-soft space-y-2">
              <div className="flex items-center justify-between text-xs font-heading font-bold text-brand-charcoal">
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-brand-tangerine" />
                  Apply Campus Coupon
                </span>
                {appliedCoupon && (
                  <button
                    onClick={removeCoupon}
                    className="text-[11px] text-red-600 font-semibold hover:underline"
                  >
                    Remove
                  </button>
                )}
              </div>

              {appliedCoupon ? (
                <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-2.5 rounded-xl text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold bg-emerald-100 px-2 py-0.5 rounded">
                      {appliedCoupon.code}
                    </span>
                    <span>Applied successfully!</span>
                  </div>
                  <span className="font-mono font-bold text-emerald-700">
                    -₹{discountAmount}
                  </span>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={couponInput}
                      onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
                      placeholder="Enter promo code (e.g. WELCOME20)"
                      className="flex-1 px-3 py-2 text-xs font-mono rounded-xl border border-brand-sage bg-brand-ivory/50 focus:outline-none focus:ring-2 focus:ring-brand-forest/20 uppercase"
                    />
                    <button
                      onClick={handleApplyCoupon}
                      disabled={!couponInput.trim() || isApplyingCoupon}
                      className="px-4 py-2 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory text-xs font-bold rounded-xl transition-all disabled:opacity-50"
                    >
                      {isApplyingCoupon ? "..." : "Apply"}
                    </button>
                  </div>
                  {couponFeedback && (
                    <div className={`text-[11px] font-medium ${couponFeedback.startsWith("Success") ? "text-emerald-700" : "text-red-600"}`}>
                      {couponFeedback}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Bill Summary */}
            <div className="bg-white rounded-2xl p-4 border border-brand-sage/80 shadow-soft space-y-2">
              <div className="font-heading font-bold text-xs text-brand-charcoal mb-1">
                Bill Breakdown
              </div>

              <div className="flex justify-between text-xs text-brand-charcoal-muted">
                <span>Items Subtotal</span>
                <span className="font-mono font-medium text-brand-charcoal">
                  ₹{itemsSubtotal}
                </span>
              </div>

              {discountAmount > 0 && (
                <div className="flex justify-between text-xs text-emerald-700 font-medium">
                  <span>Coupon Discount ({appliedCoupon?.code})</span>
                  <span className="font-mono">-₹{discountAmount}</span>
                </div>
              )}

              <div className="flex justify-between text-xs items-center">
                <div className="flex items-center gap-1.5">
                  <span className="text-brand-charcoal-muted">Desk Delivery Fee</span>
                  <span className="text-[10px] bg-brand-sage text-brand-forest font-bold px-1.5 py-0.2 rounded">
                    FLAT RATE
                  </span>
                </div>
                <span className="font-mono font-medium text-brand-forest">
                  ₹{flatDeliveryFee}
                </span>
              </div>

              <div className="text-[10px] text-brand-charcoal-muted/80 italic">
                One single delivery fee covers all {itemsGroupedByShop.length} shops directly to your desk.
              </div>

              <div className="pt-2 border-t border-brand-sage flex justify-between items-baseline font-bold">
                <span className="text-sm font-heading text-brand-charcoal">Grand Total</span>
                <span className="text-base font-mono text-brand-forest">
                  ₹{grandTotal}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Footer Checkout Action */}
        {items.length > 0 && (
          <div className="p-4 bg-white border-t border-brand-sage space-y-2">
            <div className="flex items-center justify-between text-xs text-brand-charcoal-muted px-1">
              <span className="flex items-center gap-1 text-brand-forest font-medium">
                <Clock className="w-3.5 h-3.5" />
                <span>
                  {deliveryMode === "SCHEDULED" ? selectedSlot : `Estimated Arrival: ${etaPreview}`}
                </span>
              </span>
              <span className="text-brand-forest font-semibold">100% Desk Handover</span>
            </div>

            <button
              onClick={() => onProceedToPayment(deliveryMode === "SCHEDULED" ? selectedSlot : undefined)}
              className="w-full py-3.5 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory rounded-2xl font-heading font-bold text-sm shadow-md flex items-center justify-between px-5 transition-all active:scale-[0.99]"
            >
              <span>Proceed to Pay • ₹{grandTotal}</span>
              <ArrowRight className="w-4 h-4 text-brand-tangerine" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

