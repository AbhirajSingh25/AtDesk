"use client";

import React, { useState } from "react";
import { useCart } from "@/lib/cart-context";
import { MasterOrder } from "@/types";
import { 
  ShieldCheck, CreditCard, Smartphone, CheckCircle, 
  Lock, X, Loader2, Sparkles 
} from "lucide-react";

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  scheduledWindow?: string;
  onSuccess: (order: MasterOrder) => void;
}

export function PaymentModal({
  isOpen,
  onClose,
  scheduledWindow,
  onSuccess,
}: PaymentModalProps) {
  const { grandTotal, submitOrder, isSubmittingOrder, deskLocation } = useCart();
  const [selectedMethod, setSelectedMethod] = useState("UPI");
  const [upiId, setUpiId] = useState("aarav@okhdfcbank");
  const [paymentStep, setPaymentStep] = useState<"SELECT" | "PROCESSING" | "SUCCESS">("SELECT");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handlePay = async () => {
    setErrorMsg(null);
    setPaymentStep("PROCESSING");

    try {
      // Simulate real-time bank gateway processing (1.2s)
      await new Promise((r) => setTimeout(r, 1200));

      const order = await submitOrder(selectedMethod, scheduledWindow);
      setPaymentStep("SUCCESS");

      // Give 800ms to show verified checkmark
      setTimeout(() => {
        onSuccess(order);
        onClose();
        setPaymentStep("SELECT");
      }, 800);
    } catch (err: any) {
      setPaymentStep("SELECT");
      setErrorMsg(err.message || "Payment verification failed. Please try again.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-md w-full shadow-2xl overflow-hidden border border-brand-sage">
        {/* Header */}
        <div className="bg-brand-forest text-brand-ivory px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-brand-tangerine" />
            <div>
              <h3 className="font-heading font-bold text-base">AtDesk Secure Gateway</h3>
              <p className="text-[11px] text-brand-sage/80">Pay Once for All Shops</p>
            </div>
          </div>
          {paymentStep !== "PROCESSING" && (
            <button onClick={onClose} className="p-1 rounded-full text-brand-sage hover:bg-brand-forest-dark">
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 text-brand-charcoal">
          {paymentStep === "PROCESSING" ? (
            <div className="py-8 flex flex-col items-center justify-center text-center space-y-3">
              <Loader2 className="w-10 h-10 text-brand-forest animate-spin" />
              <div className="font-heading font-bold text-base text-brand-charcoal">
                Verifying Payment with Gateway...
              </div>
              <p className="text-xs text-brand-charcoal-muted max-w-xs">
                Server-side idempotency check in progress. Please do not close this window.
              </p>
            </div>
          ) : paymentStep === "SUCCESS" ? (
            <div className="py-8 flex flex-col items-center justify-center text-center space-y-3 animate-in zoom-in-95">
              <CheckCircle className="w-12 h-12 text-emerald-600" />
              <div className="font-heading font-bold text-lg text-brand-forest">
                Payment Confirmed!
              </div>
              <p className="text-xs text-brand-charcoal-muted">
                Coordinating multi-vendor pickup for {deskLocation.desk}...
              </p>
            </div>
          ) : (
            <>
              {/* Order Amount Banner */}
              <div className="bg-brand-ivory rounded-2xl p-4 border border-brand-sage flex items-center justify-between">
                <div>
                  <span className="text-xs text-brand-charcoal-muted block">Total Payable</span>
                  <span className="text-2xl font-mono font-bold text-brand-forest">
                    ₹{grandTotal}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[11px] bg-brand-sage text-brand-forest px-2 py-0.5 rounded-full font-semibold">
                    Desk Drop Verified
                  </span>
                  <span className="text-[10px] text-brand-charcoal-muted block mt-1">
                    {deskLocation.tower}, {deskLocation.desk}
                  </span>
                </div>
              </div>

              {errorMsg && (
                <div className="p-3 bg-rose-50 text-rose-700 rounded-xl text-xs border border-rose-200">
                  {errorMsg}
                </div>
              )}

              {/* Payment Methods */}
              <div className="space-y-2.5">
                <label className="text-xs font-semibold text-brand-charcoal-muted block">
                  Select Payment Method
                </label>

                {/* UPI Option */}
                <div
                  onClick={() => setSelectedMethod("UPI")}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition-all flex items-center justify-between ${
                    selectedMethod === "UPI"
                      ? "border-brand-forest bg-brand-sage-light/60 ring-1 ring-brand-forest"
                      : "border-brand-sage hover:bg-brand-ivory/50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-brand-forest text-brand-ivory flex items-center justify-center font-bold text-xs">
                      UPI
                    </div>
                    <div>
                      <div className="font-semibold text-xs text-brand-charcoal">
                        Instant UPI (GPay / PhonePe / Paytm)
                      </div>
                      <div className="text-[11px] text-brand-charcoal-muted">
                        Fastest checkout with 0 convenience fees
                      </div>
                    </div>
                  </div>
                  <input
                    type="radio"
                    checked={selectedMethod === "UPI"}
                    onChange={() => setSelectedMethod("UPI")}
                    className="accent-brand-forest"
                  />
                </div>

                {selectedMethod === "UPI" && (
                  <div className="pl-4 pr-1">
                    <input
                      type="text"
                      value={upiId}
                      onChange={(e) => setUpiId(e.target.value)}
                      placeholder="Enter your UPI ID (e.g. mobile@upi)"
                      className="w-full px-3 py-2 rounded-xl border border-brand-sage bg-brand-ivory/30 text-xs font-mono"
                    />
                  </div>
                )}

                {/* Card Option */}
                <div
                  onClick={() => setSelectedMethod("CARD")}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition-all flex items-center justify-between ${
                    selectedMethod === "CARD"
                      ? "border-brand-forest bg-brand-sage-light/60 ring-1 ring-brand-forest"
                      : "border-brand-sage hover:bg-brand-ivory/50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-brand-forest text-brand-ivory flex items-center justify-center">
                      <CreditCard className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-semibold text-xs text-brand-charcoal">
                        Corporate / Personal Card
                      </div>
                      <div className="text-[11px] text-brand-charcoal-muted">
                        Visa, Mastercard, RuPay & Amex
                      </div>
                    </div>
                  </div>
                  <input
                    type="radio"
                    checked={selectedMethod === "CARD"}
                    onChange={() => setSelectedMethod("CARD")}
                    className="accent-brand-forest"
                  />
                </div>
              </div>

              {/* Anti-Fraud Disclaimer */}
              <div className="p-3 bg-brand-ivory/70 rounded-xl border border-brand-sage/60 text-[11px] text-brand-charcoal-muted flex items-start gap-2">
                <Lock className="w-3.5 h-3.5 text-brand-forest shrink-0 mt-0.5" />
                <span>
                  Payments are received directly by AtDesk (The Sorted Club). Delivery partners never collect cash or UPI. Full refunds are guaranteed if cancelled within 2 minutes.
                </span>
              </div>

              {/* Pay Button */}
              <button
                onClick={handlePay}
                disabled={isSubmittingOrder}
                className="w-full py-3.5 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory rounded-2xl font-heading font-bold text-sm shadow-md flex items-center justify-center gap-2 transition-all active:scale-[0.99] disabled:opacity-50"
              >
                <span>Authorize & Pay ₹{grandTotal}</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

