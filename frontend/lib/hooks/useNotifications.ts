"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Notification,
  getNotifications,
  markAsRead,
  markAllAsRead,
} from "@/lib/api/notifications";

interface UseNotificationsReturn {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  dismissNotification: (id: number) => Promise<void>;
  dismissAll: () => Promise<void>;
  refresh: () => Promise<void>;
}

const POLL_INTERVAL = 60_000; // Poll every 60 seconds

export function useNotifications(): UseNotificationsReturn {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await getNotifications();
      setNotifications(data.notifications);
      setUnreadCount(data.unread_count);
    } catch {
      // Silently fail — user might not be authenticated yet
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Poll for new notifications
  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [refresh]);

  const dismissNotification = useCallback(
    async (id: number) => {
      await markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    },
    []
  );

  const dismissAll = useCallback(async () => {
    await markAllAsRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  }, []);

  return {
    notifications,
    unreadCount,
    isLoading,
    dismissNotification,
    dismissAll,
    refresh,
  };
}
