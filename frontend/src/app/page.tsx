"use client";

import { useEffect, useState } from "react";
import { EmployeeApp } from "@/components/employee/EmployeeApp";
import { DeliveryApp } from "@/components/delivery/DeliveryApp";

export default function Home() {
  const [isRunnerApp, setIsRunnerApp] = useState(false);

  useEffect(() => {
    async function detectAppFlavor() {
      try {
        const { App } = await import("@capacitor/app");
        const info = await App.getInfo();
        if (info && info.id === "com.thesortedclub.atdesk.runner") {
          setIsRunnerApp(true);
        }
      } catch {
        // Web browser or standard environment
      }
    }
    detectAppFlavor();
  }, []);

  if (isRunnerApp) {
    return <DeliveryApp />;
  }

  return <EmployeeApp />;
}

