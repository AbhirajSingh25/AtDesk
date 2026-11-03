"use client";

import React, { useState } from "react";
import { useCart } from "@/lib/cart-context";
import { MapPin, Building2, Layers, Monitor, X, Check } from "lucide-react";

interface DeskLocationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const TOWERS = ["Tower A", "Tower B", "Tower C", "Tower D"];
const FLOORS = Array.from({ length: 14 }, (_, i) => i + 1);

export function DeskLocationModal({ isOpen, onClose }: DeskLocationModalProps) {
  const { deskLocation, setDeskLocation } = useCart();
  const [formData, setFormData] = useState({ ...deskLocation });

  if (!isOpen) return null;

  const handleSave = () => {
    setDeskLocation(formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-md w-full shadow-2xl overflow-hidden border border-brand-sage">
        {/* Header */}
        <div className="bg-brand-forest text-brand-ivory px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-brand-tangerine" />
            <div>
              <h3 className="font-heading font-bold text-base">Office Desk Location</h3>
              <p className="text-[11px] text-brand-sage/80">JMD Megapolis, Sector 48, Gurugram</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-full text-brand-sage hover:bg-brand-forest-dark transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 text-brand-charcoal">
          {/* Company Name */}
          <div>
            <label className="block text-xs font-semibold text-brand-charcoal-muted mb-1 flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-brand-forest" />
              Company / Employer Name
            </label>
            <input
              type="text"
              value={formData.company}
              onChange={(e) => setFormData({ ...formData, company: e.target.value })}
              className="w-full px-3.5 py-2.5 rounded-xl border border-brand-sage bg-brand-ivory/40 text-sm focus:outline-none focus:ring-2 focus:ring-brand-forest/20 focus:border-brand-forest"
              placeholder="e.g. Zeta Global Technologies"
            />
          </div>

          {/* Tower Selection */}
          <div>
            <label className="block text-xs font-semibold text-brand-charcoal-muted mb-1.5">
              Select Megapolis Tower
            </label>
            <div className="grid grid-cols-4 gap-2">
              {TOWERS.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setFormData({ ...formData, tower: t })}
                  className={`py-2 px-1 rounded-xl text-xs font-medium text-center border transition-all ${
                    formData.tower === t
                      ? "bg-brand-forest text-brand-ivory border-brand-forest shadow-sm"
                      : "bg-brand-ivory/50 border-brand-sage text-brand-charcoal hover:bg-brand-sage/40"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Floor Selection */}
          <div>
            <label className="block text-xs font-semibold text-brand-charcoal-muted mb-1.5 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-brand-forest" />
              Floor Level
            </label>
            <select
              value={formData.floor}
              onChange={(e) => setFormData({ ...formData, floor: Number(e.target.value) })}
              className="w-full px-3.5 py-2.5 rounded-xl border border-brand-sage bg-brand-ivory/40 text-sm focus:outline-none focus:ring-2 focus:ring-brand-forest/20 focus:border-brand-forest"
            >
              {FLOORS.map((f) => (
                <option key={f} value={f}>
                  Floor {f} {f === 6 ? "(Default Tech Hub)" : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Desk ID / Cabin */}
          <div>
            <label className="block text-xs font-semibold text-brand-charcoal-muted mb-1 flex items-center gap-1.5">
              <Monitor className="w-3.5 h-3.5 text-brand-forest" />
              Desk Number / Workstation ID
            </label>
            <input
              type="text"
              value={formData.desk}
              onChange={(e) => setFormData({ ...formData, desk: e.target.value })}
              className="w-full px-3.5 py-2.5 rounded-xl border border-brand-sage bg-brand-ivory/40 text-sm focus:outline-none focus:ring-2 focus:ring-brand-forest/20 focus:border-brand-forest font-mono"
              placeholder="e.g. Desk B-612 (Near South Wing)"
            />
          </div>

          {/* Special Instructions */}
          <div>
            <label className="block text-xs font-semibold text-brand-charcoal-muted mb-1">
              Desk Drop Instructions
            </label>
            <textarea
              rows={2}
              value={formData.instructions}
              onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
              className="w-full px-3.5 py-2 rounded-xl border border-brand-sage bg-brand-ivory/40 text-xs focus:outline-none focus:ring-2 focus:ring-brand-forest/20 focus:border-brand-forest resize-none"
              placeholder="e.g. If on a call, drop bag on edge of desk"
            />
          </div>

          {/* Save Button */}
          <button
            onClick={handleSave}
            className="w-full py-3 bg-brand-forest hover:bg-brand-forest-dark text-brand-ivory rounded-2xl font-semibold text-sm flex items-center justify-center gap-2 transition-all shadow-md active:scale-[0.99]"
          >
            <Check className="w-4 h-4" />
            <span>Confirm Desk Coordinates</span>
          </button>
        </div>
      </div>
    </div>
  );
}

