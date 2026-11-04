"use client";

import React, { useState, useEffect } from "react";
import { fetchApi } from "@/lib/api";
import { 
  Building2, TrendingUp, AlertTriangle, CheckCircle2, Clock, 
  RotateCcw, ShieldCheck, DollarSign, Store, Bike, FileText,
  UserCheck, AlertCircle, HelpCircle, ArrowRight
} from "lucide-react";

interface PilotMetrics {
  filter_mode: string;
  total_orders: number;
  completed_orders: number;
  failed_orders: number;
  on_time_delivery_pct: number;
  avg_delivery_time_mins: number;
  refund_rate_pct: number;
  shop_fulfilment_accuracy: Array<{
    shop_id: number;
    shop_name: string;
    accuracy_pct: number;
    total_items: number;
    rejected_items: number;
  }>;
  runner_productivity: Array<{
    runner_name: string;
    completed_drops: number;
    active_assignments: number;
  }>;
  shop_settlement_discrepancies: {
    unsettled_orders_count: number;
    discrepancy_amount_inr: number;
    status: string;
  };
  unit_economics: {
    gross_revenue: number;
    food_payable_to_shops: number;
    delivery_fees_collected: number;
    payment_gateway_charges: number;
    delivery_runner_costs: number;
    packaging_materials_cost: number;
    total_refunds_deducted: number;
    net_contribution_margin: number;
    avg_contribution_margin_per_order: number;
  };
}

interface PilotDashboardViewProps {
  onSwitchTab?: (tab: string) => void;
}

export function PilotDashboardView({ onSwitchTab }: PilotDashboardViewProps = {}) {
  const [mode, setMode] = useState<string>("PILOT_LIVE");
  const [metrics, setMetrics] = useState<PilotMetrics | null>(null);
  const [shops, setShops] = useState<any[]>([]);
  const [runners, setRunners] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Failure Interventions State
  const [selectedOrderId, setSelectedOrderId] = useState<string>("1");
  const [selectedRunnerId, setSelectedRunnerId] = useState<string>("1");
  const [reassignReason, setReassignReason] = useState<string>("Original runner uncontactable");
  const [delayMinutes, setDelayMinutes] = useState<number>(10);
  const [delayReason, setDelayReason] = useState<string>("Kitchen peak hour order congestion");
  const [otpOverrideReason, setOtpOverrideReason] = useState<string>("Customer phone battery discharged; in-person badge verified");
  const [disputeType, setDisputeType] = useState<string>("PACKAGE_MISSING");
  const [disputeDesc, setDisputeDesc] = useState<string>("Customer reports package not found on desk B-402");

  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [m, s, r] = await Promise.all([
        fetchApi<PilotMetrics>(`/admin/pilot-metrics?mode=${mode}`),
        fetchApi<any[]>("/admin/shops"),
        fetchApi<any[]>("/admin/delivery-partners"),
      ]);
      setMetrics(m);
      setShops(s);
      setRunners(r);
    } catch (e) {
      console.error("Failed to load pilot metrics", e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [mode]);

  const handleReassign = async () => {
    try {
      await fetchApi(`/admin/deliveries/${selectedOrderId}/reassign-runner`, {
        method: "POST",
        body: JSON.stringify({
          new_runner_id: parseInt(selectedRunnerId),
          reason: reassignReason,
        }),
      });
      setFeedbackMsg(`Runner reassigned successfully for Order #${selectedOrderId}!`);
      loadData();
    } catch (e: any) {
      setFeedbackMsg(`Error: ${e.message}`);
    }
  };

  const handleKitchenDelay = async () => {
    try {
      await fetchApi(`/admin/deliveries/${selectedOrderId}/kitchen-delay`, {
        method: "POST",
        body: JSON.stringify({
          delay_minutes: delayMinutes,
          reason: delayReason,
        }),
      });
      setFeedbackMsg(`Kitchen delay of +${delayMinutes} mins logged and customer notified!`);
      loadData();
    } catch (e: any) {
      setFeedbackMsg(`Error: ${e.message}`);
    }
  };

  const handleOtpOverride = async () => {
    if (!confirm(`Confirm Emergency Admin OTP Override for Order #${selectedOrderId}? This action is permanently audited.`)) {
      return;
    }
    try {
      await fetchApi(`/admin/deliveries/${selectedOrderId}/override-otp`, {
        method: "POST",
        body: JSON.stringify({ reason: otpOverrideReason }),
      });
      setFeedbackMsg(`Order #${selectedOrderId} marked DELIVERED via Admin OTP Override.`);
      loadData();
    } catch (e: any) {
      setFeedbackMsg(`Error: ${e.message}`);
    }
  };

  const handleLogDispute = async () => {
    try {
      const res = await fetchApi<{ ticket_id: number }>(`/admin/deliveries/${selectedOrderId}/dispute`, {
        method: "POST",
        body: JSON.stringify({
          issue_type: disputeType,
          description: disputeDesc,
        }),
      });
      setFeedbackMsg(`Dispute ticket #${res.ticket_id} opened for supervisor review.`);
      loadData();
    } catch (e: any) {
      setFeedbackMsg(`Error: ${e.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Pilot Header & Environment Filter */}
      <div className="bg-brand-forest text-brand-ivory p-6 rounded-3xl shadow-soft flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-brand-sage" />
            <h2 className="font-heading font-extrabold text-xl tracking-tight text-white">
              Controlled Commercial Pilot Dashboard
            </h2>
          </div>
          <p className="text-xs text-brand-sage/80 mt-1">
            Target Campus: JMD Megapolis, Sector 48, Gurugram • The Sorted Club
          </p>
        </div>

        {/* Environment Filter Mode */}
        <div className="flex items-center gap-1.5 bg-black/25 p-1 rounded-2xl border border-white/10 text-xs">
          {[
            { id: "PILOT_LIVE", label: "Commercial Pilot" },
            { id: "TEST_SANDBOX", label: "Sandbox / Automated" },
            { id: "ALL", label: "All Transactions" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setMode(item.id)}
              className={`px-3 py-1.5 rounded-xl font-medium transition-all ${
                mode === item.id
                  ? "bg-brand-sage text-brand-forest font-bold shadow-sm"
                  : "text-brand-ivory/70 hover:text-white"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {feedbackMsg && (
        <div className="bg-brand-sage/40 border border-brand-forest/20 text-brand-forest p-3.5 rounded-2xl text-xs flex items-center justify-between">
          <span>{feedbackMsg}</span>
          <button onClick={() => setFeedbackMsg(null)} className="font-bold underline text-[11px]">
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
          <div className="bg-white p-4 rounded-3xl border border-brand-sage/80 shadow-soft">
            <span className="text-[11px] text-brand-charcoal-muted block font-medium">Orders ({mode})</span>
            <div className="flex items-baseline gap-1.5 mt-1">
              <span className="text-2xl font-mono font-bold text-brand-charcoal">{metrics.total_orders}</span>
              <span className="text-[10px] text-brand-forest font-semibold">({metrics.completed_orders} deliv)</span>
            </div>
            <span className="text-[10px] text-brand-charcoal-muted block mt-1">Failed / Cancelled: {metrics.failed_orders}</span>
          </div>

          <div className="bg-white p-4 rounded-3xl border border-brand-sage/80 shadow-soft">
            <span className="text-[11px] text-brand-charcoal-muted block font-medium">On-Time Fulfillment</span>
            <span className="text-2xl font-mono font-bold text-brand-forest mt-1 block">
              {metrics.on_time_delivery_pct}%
            </span>
            <span className="text-[10px] text-brand-charcoal-muted block mt-1">&le; 35m Campus SLA</span>
          </div>

          <div className="bg-white p-4 rounded-3xl border border-brand-sage/80 shadow-soft">
            <span className="text-[11px] text-brand-charcoal-muted block font-medium">Avg Delivery Time</span>
            <span className="text-2xl font-mono font-bold text-brand-charcoal mt-1 block">
              {metrics.avg_delivery_time_mins} <span className="text-xs font-normal">mins</span>
            </span>
            <span className="text-[10px] text-brand-charcoal-muted block mt-1">Campus elevator calibrated</span>
          </div>

          <div className="bg-white p-4 rounded-3xl border border-brand-sage/80 shadow-soft">
            <span className="text-[11px] text-brand-charcoal-muted block font-medium">Refund Rate</span>
            <span className={`text-2xl font-mono font-bold mt-1 block ${metrics.refund_rate_pct > 5 ? "text-rose-600" : "text-emerald-700"}`}>
              {metrics.refund_rate_pct}%
            </span>
            <span className="text-[10px] text-brand-charcoal-muted block mt-1">Full & partial refunds</span>
          </div>

          <div className="bg-white p-4 rounded-3xl border border-brand-sage/80 shadow-soft">
            <span className="text-[11px] text-brand-charcoal-muted block font-medium">Contribution / Drop</span>
            <span className={`text-2xl font-mono font-bold mt-1 block ${metrics.unit_economics.avg_contribution_margin_per_order >= 0 ? "text-emerald-700" : "text-rose-600"}`}>
              Rs.{metrics.unit_economics.avg_contribution_margin_per_order}
            </span>
            <span className="text-[10px] text-brand-charcoal-muted block mt-1">Net platform margin</span>
          </div>
        </div>
      )}

      {/* Unit Economics Detailed Statement */}
      {metrics && (
        <div className="bg-white rounded-3xl p-6 border border-brand-sage/80 shadow-soft space-y-4">
          <div className="flex items-center justify-between border-b border-brand-sage/40 pb-3">
            <div>
              <h3 className="font-heading font-bold text-base text-brand-charcoal">
                Unit Economics & Financial Reconciliation ({mode})
              </h3>
              <p className="text-xs text-brand-charcoal-muted">
                Distinguishing Gross Customer GMV from Net Platform Contribution Margin
              </p>
            </div>
            <span className="text-xs font-mono font-bold bg-brand-sage/40 text-brand-forest px-3 py-1 rounded-full">
              Status: {metrics.shop_settlement_discrepancies.status}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div className="p-3 bg-brand-ivory rounded-2xl border border-brand-sage/60">
              <span className="text-brand-charcoal-muted block">Gross Customer Payment (GMV)</span>
              <span className="text-lg font-mono font-bold text-brand-charcoal mt-1 block">
                Rs.{metrics.unit_economics.gross_revenue}
              </span>
              <span className="text-[10px] text-brand-charcoal-muted">100% Topline collected</span>
            </div>

            <div className="p-3 bg-brand-ivory rounded-2xl border border-brand-sage/60">
              <span className="text-brand-charcoal-muted block">Food Cost (Shops Payable)</span>
              <span className="text-lg font-mono font-bold text-rose-700 mt-1 block">
                -Rs.{metrics.unit_economics.food_payable_to_shops}
              </span>
              <span className="text-[10px] text-brand-charcoal-muted">Daily / Prepaid payouts</span>
            </div>

            <div className="p-3 bg-brand-ivory rounded-2xl border border-brand-sage/60">
              <span className="text-brand-charcoal-muted block">Campus Operations (Runner + Bag)</span>
              <span className="text-lg font-mono font-bold text-amber-700 mt-1 block">
                -Rs.{(metrics.unit_economics.delivery_runner_costs + metrics.unit_economics.packaging_materials_cost).toFixed(2)}
              </span>
              <span className="text-[10px] text-brand-charcoal-muted">Rs.18 runner + Rs.3.50 packaging</span>
            </div>

            <div className="p-3 bg-brand-sage/30 rounded-2xl border border-brand-forest/20">
              <span className="text-brand-forest font-semibold block">Net Contribution Margin</span>
              <span className="text-lg font-mono font-bold text-brand-forest mt-1 block">
                Rs.{metrics.unit_economics.net_contribution_margin}
              </span>
              <span className="text-[10px] text-brand-forest">After 2.36% gateway fee & refunds</span>
            </div>
          </div>
        </div>
      )}

      {/* Shop Onboarding & Partnership Matrix */}
      <div className="bg-white rounded-3xl p-6 border border-brand-sage/80 shadow-soft space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-heading font-bold text-base text-brand-charcoal">
              JMD Megapolis Shop Onboarding & Commercial Audit
            </h3>
            <p className="text-xs text-brand-charcoal-muted">
              Differentiating Configured Shops from Verified Official Business Partners
            </p>
          </div>
          <span className="text-xs font-medium text-brand-charcoal-muted">
            {shops.length} campus shops configured
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-brand-sage/60 text-brand-charcoal-muted font-semibold">
                <th className="pb-3">Shop Name</th>
                <th className="pb-3">Onboarding Status</th>
                <th className="pb-3">Settlement</th>
                <th className="pb-3 text-center">Owner Perm.</th>
                <th className="pb-3 text-center">Contract</th>
                <th className="pb-3 text-center">Kitchen Audit</th>
                <th className="pb-3 text-center">Packaging</th>
                <th className="pb-3">Commercial Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-sage/30">
              {shops.map((s) => (
                <tr key={s.id} className="hover:bg-brand-ivory/50">
                  <td className="py-3 font-semibold text-brand-charcoal">
                    {s.name}
                    {s.official_business_partner && (
                      <span className="ml-2 text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
                        Official Partner
                      </span>
                    )}
                  </td>
                  <td className="py-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      s.onboarding_status === "OPERATIONALLY_VERIFIED"
                        ? "bg-emerald-100 text-emerald-800"
                        : s.onboarding_status === "CONTRACTED"
                        ? "bg-blue-100 text-blue-800"
                        : s.onboarding_status === "CONTACTED"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-gray-100 text-gray-700"
                    }`}>
                      {s.onboarding_status}
                    </span>
                  </td>
                  <td className="py-3 font-mono font-medium">{s.settlement_type}</td>
                  <td className="py-3 text-center">{s.owner_permission_verified ? "✅" : "❌"}</td>
                  <td className="py-3 text-center">{s.contract_signed ? "✅" : "❌"}</td>
                  <td className="py-3 text-center">{s.kitchen_prep_audited ? "✅" : "❌"}</td>
                  <td className="py-3 text-center">{s.packaging_standard_verified ? "✅" : "❌"}</td>
                  <td className="py-3 text-brand-charcoal-muted max-w-xs truncate">{s.onboarding_notes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Operational Failure Interventions Suite */}
      <div className="bg-white rounded-3xl p-6 border border-brand-sage/80 shadow-soft space-y-4">
        <div>
          <h3 className="font-heading font-bold text-base text-brand-charcoal">
            Operational Failure Interventions & Security Overrides
          </h3>
          <p className="text-xs text-brand-charcoal-muted">
            All supervisor overrides generate an immutable security audit entry with admin attribution.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* Action 1: Reassign Runner */}
          <div className="p-4 bg-brand-ivory rounded-2xl border border-brand-sage/60 space-y-3">
            <div className="flex items-center gap-2 font-bold text-brand-charcoal">
              <Bike className="w-4 h-4 text-brand-forest" />
              <span>1. Runner No-Show / Reassignment</span>
            </div>
            <div className="space-y-2">
              <div>
                <label className="text-[10px] text-brand-charcoal-muted block">Master Order ID</label>
                <input
                  type="text"
                  value={selectedOrderId}
                  onChange={(e) => setSelectedOrderId(e.target.value)}
                  className="w-full mt-1 p-2 bg-white rounded-xl border border-brand-sage text-xs font-mono"
                  placeholder="e.g. 1"
                />
              </div>
              <div>
                <label className="text-[10px] text-brand-charcoal-muted block">Assign New Runner</label>
                <select
                  value={selectedRunnerId}
                  onChange={(e) => setSelectedRunnerId(e.target.value)}
                  className="w-full mt-1 p-2 bg-white rounded-xl border border-brand-sage text-xs"
                >
                  {runners.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.vehicle_number})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-brand-charcoal-muted block">Reason for Reassignment</label>
                <input
                  type="text"
                  value={reassignReason}
                  onChange={(e) => setReassignReason(e.target.value)}
                  className="w-full mt-1 p-2 bg-white rounded-xl border border-brand-sage text-xs"
                />
              </div>
              <button
                onClick={handleReassign}
                className="w-full py-2 bg-brand-forest text-white font-bold rounded-xl hover:bg-brand-forest-dark transition-all"
              >
                Execute Runner Reassignment & Notify
              </button>
            </div>
          </div>

          {/* Action 2: Kitchen Delay */}
          <div className="p-4 bg-brand-ivory rounded-2xl border border-brand-sage/60 space-y-3">
            <div className="flex items-center gap-2 font-bold text-brand-charcoal">
              <Clock className="w-4 h-4 text-brand-tangerine" />
              <span>2. Kitchen Preparation Delay Extension</span>
            </div>
            <div className="space-y-2">
              <div>
                <label className="text-[10px] text-brand-charcoal-muted block">Additional Prep Time (Minutes)</label>
                <input
                  type="number"
                  value={delayMinutes}
                  onChange={(e) => setDelayMinutes(parseInt(e.target.value) || 5)}
                  className="w-full mt-1 p-2 bg-white rounded-xl border border-brand-sage text-xs font-mono"
                />
              </div>
              <div>
                <label className="text-[10px] text-brand-charcoal-muted block">Kitchen Delay Reason</label>
                <input
                  type="text"
                  value={delayReason}
                  onChange={(e) => setDelayReason(e.target.value)}
                  className="w-full mt-1 p-2 bg-white rounded-xl border border-brand-sage text-xs"
                />
              </div>
              <button
                onClick={handleKitchenDelay}
                className="w-full py-2 bg-brand-tangerine text-white font-bold rounded-xl hover:bg-brand-tangerine/90 transition-all mt-4"
              >
                Update Dynamic ETA & Notify Customer
              </button>
            </div>
          </div>

          {/* Action 3: Admin OTP Override */}
          <div className="p-4 bg-brand-ivory rounded-2xl border border-brand-sage/60 space-y-3">
            <div className="flex items-center gap-2 font-bold text-brand-charcoal">
              <ShieldCheck className="w-4 h-4 text-emerald-700" />
              <span>3. Emergency Admin OTP Bypass</span>
            </div>
            <div className="space-y-2">
              <p className="text-[10px] text-brand-charcoal-muted">
                Used strictly when customer phone battery is dead and employee identity is physically verified at desk.
              </p>
              <div>
                <label className="text-[10px] text-brand-charcoal-muted block">Verification Reason & Badge ID</label>
                <input
                  type="text"
                  value={otpOverrideReason}
                  onChange={(e) => setOtpOverrideReason(e.target.value)}
                  className="w-full mt-1 p-2 bg-white rounded-xl border border-brand-sage text-xs"
                />
              </div>
              <button
                onClick={handleOtpOverride}
                className="w-full py-2 bg-emerald-800 text-white font-bold rounded-xl hover:bg-emerald-900 transition-all"
              >
                Authorize Emergency Desk Drop Completion
              </button>
            </div>
          </div>

          {/* Action 4: Customer Dispute Intake */}
          <div className="p-4 bg-brand-ivory rounded-2xl border border-brand-sage/60 space-y-3">
            <div className="flex items-center gap-2 font-bold text-brand-charcoal">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <span>4. Delivery Dispute Intake Ticket</span>
            </div>
            <div className="space-y-2">
              <div>
                <label className="text-[10px] text-brand-charcoal-muted block">Dispute Classification</label>
                <select
                  value={disputeType}
                  onChange={(e) => setDisputeType(e.target.value)}
                  className="w-full mt-1 p-2 bg-white rounded-xl border border-brand-sage text-xs"
                >
                  <option value="PACKAGE_MISSING">Package Missing at Desk</option>
                  <option value="WRONG_DESK">Delivered to Wrong Floor/Desk</option>
                  <option value="ITEM_DAMAGED">Packaging Tampered / Cold Food</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] text-brand-charcoal-muted block">Dispute Narrative</label>
                <input
                  type="text"
                  value={disputeDesc}
                  onChange={(e) => setDisputeDesc(e.target.value)}
                  className="w-full mt-1 p-2 bg-white rounded-xl border border-brand-sage text-xs"
                />
              </div>
              <button
                onClick={handleLogDispute}
                className="w-full py-2 bg-rose-700 text-white font-bold rounded-xl hover:bg-rose-800 transition-all"
              >
                Open Supervisor Dispute Case
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

