"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { MenuItem, Shop, CartItem, MasterOrder } from "@/types";
import { fetchApi } from "./api";

interface DeskLocation {
  tower: string;
  floor: number;
  desk: string;
  company: string;
  instructions: string;
}

interface CartContextType {
  items: CartItem[];
  addItem: (menuItem: MenuItem, shop: Shop) => void;
  removeItem: (menuItemId: number) => void;
  updateQuantity: (menuItemId: number, delta: number) => void;
  clearCart: () => void;
  deskLocation: DeskLocation;
  setDeskLocation: React.Dispatch<React.SetStateAction<DeskLocation>>;
  itemsSubtotal: number;
  flatDeliveryFee: number;
  grandTotal: number;
  itemsGroupedByShop: { shop: Shop; items: CartItem[]; subtotal: number }[];
  activeOrder: MasterOrder | null;
  setActiveOrder: (order: MasterOrder | null) => void;
  refreshActiveOrder: () => Promise<void>;
  cancelActiveOrder: (reason?: string) => Promise<{ success: boolean; message: string }>;
  isSubmittingOrder: boolean;
  submitOrder: (paymentMethod?: string, scheduledWindow?: string) => Promise<MasterOrder>;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [activeOrder, setActiveOrder] = useState<MasterOrder | null>(null);
  const [isSubmittingOrder, setIsSubmittingOrder] = useState(false);

  // Default JMD Megapolis Desk location
  const [deskLocation, setDeskLocation] = useState<DeskLocation>({
    tower: "Tower B",
    floor: 6,
    desk: "Desk B-612",
    company: "Zeta Global Technologies",
    instructions: "Leave gently on desk near monitor",
  });

  const flatDeliveryFee = items.length > 0 ? 25 : 0;

  const addItem = (menuItem: MenuItem, shop: Shop) => {
    setItems((prev) => {
      const idx = prev.findIndex((i) => i.menuItem.id === menuItem.id);
      if (idx > -1) {
        const copy = [...prev];
        copy[idx].quantity += 1;
        return copy;
      }
      return [...prev, { menuItem, shop, quantity: 1 }];
    });
  };

  const updateQuantity = (menuItemId: number, delta: number) => {
    setItems((prev) => {
      return prev
        .map((item) => {
          if (item.menuItem.id === menuItemId) {
            const newQty = item.quantity + delta;
            return newQty > 0 ? { ...item, quantity: newQty } : null;
          }
          return item;
        })
        .filter(Boolean) as CartItem[];
    });
  };

  const removeItem = (menuItemId: number) => {
    setItems((prev) => prev.filter((i) => i.menuItem.id !== menuItemId));
  };

  const clearCart = () => setItems([]);

  // Calculate items grouped by shop
  const shopMap = new Map<number, { shop: Shop; items: CartItem[]; subtotal: number }>();
  let itemsSubtotal = 0;

  items.forEach((item) => {
    const itemTotal = item.menuItem.price * item.quantity;
    itemsSubtotal += itemTotal;

    if (!shopMap.has(item.shop.id)) {
      shopMap.set(item.shop.id, {
        shop: item.shop,
        items: [item],
        subtotal: itemTotal,
      });
    } else {
      const entry = shopMap.get(item.shop.id)!;
      entry.items.push(item);
      entry.subtotal += itemTotal;
    }
  });

  const itemsGroupedByShop = Array.from(shopMap.values());
  const grandTotal = itemsSubtotal + flatDeliveryFee;

  const submitOrder = async (paymentMethod = "UPI", scheduledWindow?: string): Promise<MasterOrder> => {
    setIsSubmittingOrder(true);
    try {
      const payload = {
        items: items.map((i) => ({ menu_item_id: i.menuItem.id, quantity: i.quantity })),
        tower: deskLocation.tower,
        floor: deskLocation.floor,
        desk_location: deskLocation.desk,
        delivery_instructions: deskLocation.instructions,
        payment_method: paymentMethod,
        scheduled_window: scheduledWindow || null,
        idempotency_key: `IDEMP-${Date.now()}-${Math.random().toString(36).substring(7)}`,
      };

      const order = await fetchApi<MasterOrder>("/orders?user_id=1", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setActiveOrder(order);
      clearCart();
      return order;
    } finally {
      setIsSubmittingOrder(false);
    }
  };

  const refreshActiveOrder = async () => {
    if (!activeOrder) return;
    try {
      const updated = await fetchApi<MasterOrder>(`/orders/${activeOrder.id}`);
      setActiveOrder(updated);
    } catch (e) {
      console.error("Error refreshing active order", e);
    }
  };

  const cancelActiveOrder = async (reason = "Customer cancelled within 2 minutes") => {
    if (!activeOrder) throw new Error("No active order to cancel");
    const res = await fetchApi<{ success: boolean; message: string; refund_amount: number }>(
      `/orders/${activeOrder.id}/cancel?user_id=1`,
      {
        method: "POST",
        body: JSON.stringify({ reason }),
      }
    );
    await refreshActiveOrder();
    return res;
  };

  return (
    <CartContext.Provider
      value={{
        items,
        addItem,
        removeItem,
        updateQuantity,
        clearCart,
        deskLocation,
        setDeskLocation,
        itemsSubtotal,
        flatDeliveryFee,
        grandTotal,
        itemsGroupedByShop,
        activeOrder,
        setActiveOrder,
        refreshActiveOrder,
        cancelActiveOrder,
        isSubmittingOrder,
        submitOrder,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used within a CartProvider");
  return context;
}

