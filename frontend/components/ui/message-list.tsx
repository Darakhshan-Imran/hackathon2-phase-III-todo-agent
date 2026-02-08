"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Message } from "@/lib/types/message";
import { MessageBubble } from "./message-bubble";
import { Sparkles } from "lucide-react";
import AILoadingState from "@/components/kokonutui/ai-loading";

interface MessageListProps {
  messages: Message[];
  isProcessing?: boolean;
  onRetryMessage?: (messageId: string) => void;
  onEditMessage?: (messageId: string, newContent: string) => void;
}

export function MessageList({ 
  messages, 
  isProcessing = false,
  onRetryMessage,
  onEditMessage
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isProcessing]);

  if (messages.length === 0 && !isProcessing) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <motion.div
          className="text-center space-y-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-r from-violet-500/20 to-indigo-500/20 flex items-center justify-center backdrop-blur-xl border border-white/[0.05]">
            <Sparkles className="w-8 h-8 text-violet-400" />
          </div>
          <div>
            <h3 className="text-lg font-medium text-white/90 mb-1">
              No messages yet
            </h3>
            <p className="text-sm text-white/40">
              Start a conversation by sending a message below
            </p>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-6 space-y-2"
      style={{
        scrollbarWidth: "thin",
        scrollbarColor: "rgba(255, 255, 255, 0.1) transparent",
      }}
    >
      {messages.map((message, index) => (
        <MessageBubble 
          key={message.id} 
          message={message}
          agentLogs={message.agentLogs}
          showTyping={message.isStreaming && index === messages.length - 1}
          onRetry={onRetryMessage}
          onEdit={onEditMessage}
        />
      ))}
      
      {/* AI Loading while processing */}
      {isProcessing && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="flex justify-start w-full"
        >
          <div className="max-w-[85%] backdrop-blur-xl bg-gradient-to-br from-violet-500/15 via-indigo-500/15 to-fuchsia-500/10 rounded-2xl border border-white/[0.05] p-6">
            <AILoadingState />
          </div>
        </motion.div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
}
