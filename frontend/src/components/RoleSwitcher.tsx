"use client";

import React from "react";
import { usePathname, useRouter } from "next/navigation";
import { UserCheck, Bike, ShieldCheck, MapPin } from "lucide-react";

export function RoleSwitcher() {
  const pathname = usePathname();
  const router = useRouter();

  const isEmployee = pathname === "/" || pathname.startsWith("/employee");
  const isDelivery = pathname.startsWith("/delivery");
  const isAdmin = pathname.startsWith("/admin");

  return (
    <header className="sticky top-0 z-50 bg-brand-forest text-brand-ivory border-b border-brand-forest-dark shadow-sm">
      <div className="max-w-7xl mx-auto px-3 py-2 flex flex-wrap items-center justify-between gap-2 text-xs">
        {/* Brand identity badge */}
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-brand-sage text-brand-forest font-heading font-extrabold flex items-center justify-center text-sm shadow-sm">
            @
          </div>
          <div className="leading-tight">
            <div className="font-heading font-bold tracking-tight text-white flex items-center gap-1.5">
              <span>AtDesk</span>
              <span className="text-[10px] bg-brand-forest-dark text-brand-sage px-1.5 py-0.5 rounded font-normal">
                JMD Megapolis
              </span>
            </div>
            <div className="text-[9px] text-brand-sage/80 tracking-wide font-sans">
              A product of The Sorted Club
            </div>
          </div>
        </div>

        {/* Global Role Switcher Navigation Pills */}
        <div className="flex items-center bg-brand-forest-dark/70 p-1 rounded-full border border-brand-forest-light/40">
          <button
            onClick={() => router.push("/")}
            className={`flex items-center gap-1 px-3 py-1 rounded-full font-medium transition-all ${
              isEmployee
                ? "bg-brand-sage text-brand-forest shadow-sm"
                : "text-brand-ivory/80 hover:text-white"
            }`}
          >
            <UserCheck className="w-3.5 h-3.5" />
            <span>Employee App</span>
          </button>

          <button
            onClick={() => router.push("/delivery")}
            className={`flex items-center gap-1 px-3 py-1 rounded-full font-medium transition-all ${
              isDelivery
                ? "bg-brand-tangerine text-brand-charcoal font-semibold shadow-sm"
                : "text-brand-ivory/80 hover:text-white"
            }`}
          >
            <Bike className="w-3.5 h-3.5" />
            <span>Delivery Partner</span>
          </button>

          <button
            onClick={() => router.push("/admin")}
            className={`flex items-center gap-1 px-3 py-1 rounded-full font-medium transition-all ${
              isAdmin
                ? "bg-white text-brand-forest font-semibold shadow-sm"
                : "text-brand-ivory/80 hover:text-white"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Admin Center</span>
          </button>
        </div>

        {/* Launch Location pill */}
        <div className="hidden md:flex items-center gap-1 text-[11px] text-brand-sage/90">
          <MapPin className="w-3 h-3 text-brand-tangerine" />
          <span>Sector 48, Gurugram</span>
        </div>
      </div>
    </header>
  );
}

