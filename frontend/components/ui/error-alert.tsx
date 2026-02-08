"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { XIcon, AlertCircle } from "lucide-react";

interface ErrorAlertProps {
  message: string;
  onDismiss?: () => void;
  autoDismiss?: boolean;
  autoDismissDelay?: number;
}

export function ErrorAlert({ 
  message, 
  onDismiss,
  autoDismiss = true,
  autoDismissDelay = 5000
}: ErrorAlertProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    if (autoDismiss && autoDismissDelay > 0) {
      const timer = setTimeout(() => {
        setIsVisible(false);
        setTimeout(() => onDismiss?.(), 300); // Wait for animation
      }, autoDismissDelay);

      return () => clearTimeout(timer);
    }
  }, [autoDismiss, autoDismissDelay, onDismiss]);

  const handleDismiss = () => {
    setIsVisible(false);
    setTimeout(() => onDismiss?.(), 300);
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          className="fixed top-4 right-4 z-50 max-w-md"
          initial={{ opacity: 0, y: -20, x: 20 }}
          animate={{ opacity: 1, y: 0, x: 0 }}
          exit={{ opacity: 0, y: -20, x: 20 }}
          transition={{ duration: 0.3 }}
        >
          <div 
            className="backdrop-blur-xl bg-red-500/10 border border-red-500/20 rounded-xl p-4 shadow-2xl"
            role="alert"
            aria-live="assertive"
            aria-atomic="true"
          >
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0">
                <AlertCircle className="w-5 h-5 text-red-400" />
              </div>
              
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-red-100">
                  Error
                </p>
                <p className="text-sm text-red-200/80 mt-1">
                  {message}
                </p>
              </div>
              
              <button
                onClick={handleDismiss}
                className="flex-shrink-0 p-1 rounded-lg hover:bg-red-500/20 transition-colors"
                aria-label="Dismiss error"
              >
                <XIcon className="w-4 h-4 text-red-300" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
