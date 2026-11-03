"use client";

import React, { useState, useEffect } from "react";
import { MasterOrder } from "@/types";
import { useCart } from "@/lib/cart-context";
import { 
  Clock, ShieldAlert, CheckCircle, MapPin, 
  Store, AlertCircle, ArrowLeft, RefreshCw 
} from "lucide-react";

interface LiveOrderTrackerProps {
  order: MasterOrder;
  onBackToExplore: () => void;
}

export function LiveOrderTracker({ order, onBackToExplore }: LiveOrderTrackerProps) {
  const { cancelActiveOrder, refreshActiveOrder } = useCart();
  const [secondsRemaining, setSecondsRemaining] = useState<number>(
    order.cancellation_seconds_remaining || 0
  );
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelFeedback, setCancelFeedback] = useState<string | null>(null);

  // Poll server every 4 seconds to get real-time shop preparation & delivery status updates
  useEffect(() => {
    const pollInterval = setInterval(() => {
      refreshActiveOrder();
    }, 4000);
    return () => clearInterval(pollInterval);
  }, [refreshActiveOrder]);

  // Tick countdown locally
  useEffect(() => {
    setSecondsRemaining(order.cancellation_seconds_remaining || 0);

    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [order.cancellation_seconds_remaining]);

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel this order? You will receive a 100% immediate refund.")) {
      return;
    }
    setIsCancelling(true);
    try {
      const res = await cancelActiveOrder("Customer cancelled via 2-minute live timer");
      setCancelFeedback(res.message);
    } catch (err: any) {
      alert(err.message || "Could not cancel order");
    } finally {
      setIsCancelling(false);
    }
  };

  const isCancelled = order.status === "CANCELLED";
  const isDelivered = order.status === "DELIVERED";
  const canCancel = order.can_cancel && secondsRemaining > 0 && !isCancelled && !isDelivered;

  const totalWindow = 120;
  const progressPct = Math.max(0, Math.min(100, (secondsRemaining / totalWindow) * 100));

  return (
    <div className="max-w-md mx-auto space-y-4 pb-20 animate-in fade-in duration-200">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBackToExplore}
          className="flex items-center gap-1.5 text-xs font-semibold text-brand-forest hover:text-brand-tangerine transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Shops</span>
        </button>

        <button
          onClick={() => refreshActiveOrder()}
          className="flex items-center gap-1 text-[11px] text-brand-charcoal-muted hover:text-brand-forest transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Refresh Status</span>
        </button>
      </div>

      {/* Main Order Card */}
      <div className="bg-white rounded-3xl p-5 border border-brand-sage shadow-float space-y-4">
        {/* Header Status */}
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[10px] font-mono text-brand-charcoal-muted uppercase tracking-wider">
              Master Order #{order.order_number}
            </div>
            <h2 className="font-heading font-extrabold text-xl text-brand-charcoal mt-0.5">
              {isCancelled
                ? "Order Cancelled"
                : isDelivered
                ? "Delivered to Desk"
                : order.status === "OUT_FOR_DELIVERY"
                ? "Runner En Route to Desk"
                : "Coordinating Order"}
            </h2>
          </div>

          <span
            className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
              isCancelled
                ? "bg-rose-100 text-rose-700"
                : isDelivered
                ? "bg-emerald-100 text-emerald-800"
                : "bg-brand-sage text-brand-forest"
            }`}
          >
            {order.status}
          </span>
        </div>

        {/* 2-MINUTE CANCELLATION ENGINE COUNTDOWN */}
        {!isCancelled && !isDelivered && (
          <div className="bg-brand-ivory rounded-2xl p-4 border border-brand-sage/80 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-brand-tangerine" />
                <span className="text-xs font-bold text-brand-charcoal">
                  {secondsRemaining > 0
                    ? "2-Minute Grace Cancellation Window"
                    : "Cancellation Window Closed"}
                </span>
              </div>
              <span className="text-xs font-mono font-bold text-brand-tangerine">
                {secondsRemaining > 0 ? `${secondsRemaining}s remaining` : "Expired"}
              </span>
            </div>

            {/* Visual Progress Bar */}
            <div className="w-full bg-brand-sage/60 rounded-full h-2 overflow-hidden">
              <div
                className="bg-brand-tangerine h-full transition-all duration-1000 ease-linear rounded-full"
                style={{ width: `${progressPct}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-[11px] text-brand-charcoal-muted pt-1">
              <span>
                {secondsRemaining > 0
                  ? "Full refund guaranteed if cancelled now."
                  : "Dispatch finalized. Delivery partner is at the concourse."}
              </span>

              {canCancel && (
                <button
                  onClick={handleCancel}
                  disabled={isCancelling}
                  className="px-3 py-1 bg-white hover:bg-rose-50 text-rose-600 font-semibold rounded-xl border border-rose-200 transition-colors shrink-0 ml-2 disabled:opacity-50"
                >
                  {isCancelling ? "Processing..." : "Cancel Order"}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Cancel Confirmation Banner */}
        {isCancelled && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-800 space-y-1">
            <div className="font-bold flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-rose-600" />
              <span>Full Refund Initiated • ₹{order.grand_total}</span>
            </div>
            <p className="text-[11px] text-rose-700">
              The full amount has been refunded to your original payment method. Reversal entries were made in vendor ledgers.
            </p>
          </div>
        )}

        {/* Master Order 6-Digit OTP */}
        {!isCancelled && (
          <div className="bg-brand-forest text-brand-ivory rounded-2xl p-4 text-center space-y-1 shadow-md">
            <span className="text-[10px] uppercase font-bold text-brand-sage tracking-widest block">
              Desk Delivery Master OTP
            </span>
            <div className="text-3xl font-mono font-extrabold tracking-widest text-brand-tangerine py-1">
              {order.master_otp}
            </div>
            <p className="text-[11px] text-brand-sage/90">
              Share this 6-digit OTP with Deepak (Runner) when your food is handed over at your desk.
            </p>
          </div>
        )}

        {/* Desk Destination Coordinates */}
        <div className="p-3.5 bg-brand-ivory/50 rounded-2xl border border-brand-sage/60 flex items-start gap-3">
          <MapPin className="w-4 h-4 text-brand-forest shrink-0 mt-0.5" />
          <div className="text-xs">
            <span className="font-bold text-brand-charcoal block">
              {order.tower}, Floor {order.floor}
            </span>
            <span className="text-brand-charcoal-muted font-mono">{order.desk_location}</span>
            {order.delivery_instructions && (
              <span className="text-[11px] text-brand-forest block mt-1 italic">
                Note: {order.delivery_instructions}
              </span>
            )}
          </div>
        </div>

        {/* Shop-by-Shop Preparation Progress */}
        <div className="space-y-3 pt-2">
          <div className="font-heading font-bold text-xs text-brand-charcoal uppercase tracking-wider flex items-center justify-between">
            <span>Shop Preparation Status</span>
            <span className="text-brand-forest font-semibold text-[11px]">
              {order.vendor_orders.length} Shops Involved
            </span>
          </div>

          <div className="space-y-2.5">
            {order.vendor_orders.map((vo) => (
              <div
                key={vo.id}
                className="p-3 bg-brand-ivory/30 rounded-2xl border border-brand-sage/70 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Store className="w-3.5 h-3.5 text-brand-forest" />
                    <span className="font-heading font-bold text-xs text-brand-charcoal">
                      {vo.shop_name || `Shop #${vo.shop_id}`}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                      vo.status === "PICKED_UP"
                        ? "bg-emerald-100 text-emerald-800"
                        : vo.status === "READY_FOR_PICKUP"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-brand-sage-light text-brand-forest"
                    }`}
                  >
                    {vo.status.replace(/_/g, " ")}
                  </span>
                </div>

                {/* Items in this shop */}
                <div className="space-y-1 pl-5 text-xs text-brand-charcoal-muted">
                  {vo.order_items.map((oi) => (
                    <div key={oi.id} className="flex justify-between items-center">
                      <span className={oi.is_rejected ? "line-through text-rose-500" : ""}>
                        {oi.quantity}× {oi.item_name}
                      </span>
                      <span className="font-mono font-medium">₹{oi.subtotal}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Financial Summary */}
        <div className="pt-3 border-t border-brand-sage/60 text-xs space-y-1.5 text-brand-charcoal-muted">
          <div className="flex justify-between">
            <span>Items Subtotal</span>
            <span className="font-mono">₹{order.items_subtotal}</span>
          </div>
          <div className="flex justify-between">
            <span>Desk Delivery Fee</span>
            <span className="font-mono">₹{order.flat_delivery_fee}</span>
          </div>
          <div className="flex justify-between font-bold text-brand-charcoal text-sm pt-1">
            <span>Total Paid</span>
            <span className="font-mono text-brand-forest">₹{order.grand_total}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

