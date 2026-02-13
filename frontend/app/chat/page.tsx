"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { useAgentChat } from "@/lib/hooks/useAgentChat";
import { IntegratedChat } from "@/components/ui/integrated-chat";
import { ErrorAlert } from "@/components/ui/error-alert";
import { NotificationBell } from "@/components/ui/notification-bell";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";

export default function ChatPage() {
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const { 
    messages, 
    agentState, 
    isProcessing, 
    error, 
    sendMessage, 
    clearError,
    retryMessage,
    editMessage
  } = useAgentChat();
  const router = useRouter();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, authLoading, router]);

  // Show loading state while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0A0A0B] text-white">
        <motion.div
          className="flex flex-col items-center gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <Loader2 className="w-8 h-8 animate-spin text-violet-400" />
          <p className="text-sm text-white/40">Loading...</p>
        </motion.div>
      </div>
    );
  }

  // Don't render chat if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <>
      {/* Notification Bell — top right */}
      <div className="fixed top-4 right-4 z-50">
        <NotificationBell />
      </div>

      {/* Error Alert */}
      {error && (
        <ErrorAlert
          message={error}
          onDismiss={clearError}
        />
      )}

      {/* Chat Interface */}
      <IntegratedChat
        messages={messages}
        agentState={agentState}
        onSendMessage={sendMessage}
        isProcessing={isProcessing}
        onRetryMessage={retryMessage}
        onEditMessage={editMessage}
        username={user?.username}
      />
    </>
  );
}
