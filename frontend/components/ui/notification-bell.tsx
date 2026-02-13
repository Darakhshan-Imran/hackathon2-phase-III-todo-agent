"use client";

import { useState, useRef, useEffect } from "react";
import { Bell, X, CheckCheck } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useNotifications } from "@/lib/hooks/useNotifications";
import { cn } from "@/lib/utils";

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const {
    notifications,
    unreadCount,
    dismissNotification,
    dismissAll,
  } = useNotifications();

  // Close panel when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const unreadNotifications = notifications.filter((n) => !n.is_read);

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "relative p-2 rounded-lg transition-all",
          "hover:bg-white/[0.05] text-white/60 hover:text-white/90",
          isOpen && "bg-white/[0.05] text-white/90"
        )}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-0.5 -right-0.5 w-4.5 h-4.5 bg-violet-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center"
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </motion.span>
        )}
      </button>

      {/* Dropdown Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className={cn(
              "absolute right-0 top-full mt-2 w-80 max-h-96 overflow-y-auto",
              "rounded-xl border border-white/[0.08] bg-[#141415] shadow-2xl shadow-black/40",
              "backdrop-blur-xl z-50"
            )}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
              <h3 className="text-sm font-medium text-white/80">
                Notifications
              </h3>
              {unreadCount > 0 && (
                <button
                  onClick={dismissAll}
                  className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300 transition-colors"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  Mark all read
                </button>
              )}
            </div>

            {/* Notification List */}
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-white/30">
                No notifications yet
              </div>
            ) : (
              <div className="divide-y divide-white/[0.04]">
                {notifications.map((notification) => (
                  <motion.div
                    key={notification.id}
                    layout
                    className={cn(
                      "px-4 py-3 flex items-start gap-3 transition-colors",
                      !notification.is_read
                        ? "bg-violet-500/[0.04]"
                        : "opacity-60"
                    )}
                  >
                    {/* Unread dot */}
                    <div className="mt-1.5 flex-shrink-0">
                      {!notification.is_read ? (
                        <div className="w-2 h-2 rounded-full bg-violet-400" />
                      ) : (
                        <div className="w-2 h-2 rounded-full bg-white/10" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white/80 leading-snug">
                        {notification.message}
                      </p>
                      <p className="text-xs text-white/30 mt-1">
                        {new Date(notification.created_at).toLocaleString()}
                      </p>
                    </div>

                    {/* Dismiss */}
                    {!notification.is_read && (
                      <button
                        onClick={() => dismissNotification(notification.id)}
                        className="flex-shrink-0 p-1 rounded hover:bg-white/[0.05] text-white/30 hover:text-white/60 transition-colors"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
