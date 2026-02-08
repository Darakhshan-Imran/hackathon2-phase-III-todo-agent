"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Message } from "@/lib/types/message";
import { parseMarkdown } from "@/lib/utils/markdown";
import AILoadingState from "@/components/kokonutui/ai-loading";
import { useState, useEffect } from "react";
import { Copy, Check, RotateCcw, Edit2 } from "lucide-react";

interface MessageBubbleProps {
  message: Message;
  showTyping?: boolean;
  agentLogs?: string[];
  onRetry?: (messageId: string) => void;
  onEdit?: (messageId: string, content: string) => void;
}

export function MessageBubble({ 
  message, 
  showTyping = false, 
  agentLogs = [],
  onRetry,
  onEdit 
}: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [displayedContent, setDisplayedContent] = useState('');
  const [isTypingComplete, setIsTypingComplete] = useState(!showTyping);
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  
  // Copy to clipboard function
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Handle edit save
  const handleEditSave = () => {
    if (onEdit && editContent.trim() !== message.content) {
      onEdit(message.id, editContent.trim());
    }
    setIsEditing(false);
  };

  // Handle edit cancel
  const handleEditCancel = () => {
    setEditContent(message.content);
    setIsEditing(false);
  };
  
  // Typing effect for agent messages
  useEffect(() => {
    if (!showTyping || isUser) {
      setDisplayedContent(message.content);
      setIsTypingComplete(true);
      return;
    }

    let currentIndex = 0;
    const typingSpeed = 2; // ms per character - fast streaming

    const interval = setInterval(() => {
      if (currentIndex < message.content.length) {
        setDisplayedContent(message.content.substring(0, currentIndex + 1));
        currentIndex++;
      } else {
        setIsTypingComplete(true);
        clearInterval(interval);
      }
    }, typingSpeed);

    return () => clearInterval(interval);
  }, [message.content, showTyping, isUser]);
  
  return (
    <motion.div
      className={cn(
        "flex w-full mb-6",
        isUser ? "justify-end" : "justify-start"
      )}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      <div className={cn("max-w-[85%] space-y-3")}>
        {/* Agent Logs Section - Only for assistant */}
        {!isUser && agentLogs.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="backdrop-blur-xl bg-white/[0.02] rounded-2xl border border-white/[0.05] p-4 mb-2"
          >
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 bg-violet-400 rounded-full animate-pulse" />
              <span className="text-xs font-medium text-white/60">Agent Activity</span>
            </div>
            <div className="space-y-2">
              {agentLogs.map((log, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-start gap-2 text-xs text-white/50"
                >
                  <span className="text-violet-400/60">→</span>
                  <span>{log}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Message Bubble */}
        <div
          className={cn(
            "rounded-2xl px-5 py-4 text-sm relative overflow-hidden group",
            "backdrop-blur-xl border border-white/[0.05]",
            isUser
              ? "bg-white/[0.08] text-white"
              : "bg-gradient-to-br from-violet-500/15 via-indigo-500/15 to-fuchsia-500/10 text-white"
          )}
        >
          {/* Edit mode */}
          {isEditing ? (
            <div className="space-y-3">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white resize-none focus:outline-none focus:border-violet-400/50"
                rows={4}
                autoFocus
              />
              <div className="flex gap-2 justify-end">
                <button
                  onClick={handleEditCancel}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-xs transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleEditSave}
                  className="px-3 py-1.5 rounded-lg bg-violet-500/20 hover:bg-violet-500/30 text-violet-300 hover:text-violet-200 text-xs transition-colors"
                >
                  Save & Resend
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Action buttons on hover */}
              <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                {isUser ? (
                  <>
                    {/* Edit button for user messages */}
                    <button
                      onClick={() => setIsEditing(true)}
                      className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-colors"
                      title="Edit message"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    {/* Retry button for user messages */}
                    {onRetry && (
                      <button
                        onClick={() => onRetry(message.id)}
                        className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-colors"
                        title="Retry message"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </>
                ) : (
                  /* Copy button for agent messages */
                  <button
                    onClick={handleCopy}
                    className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/70 hover:text-white transition-colors"
                    title={copied ? "Copied!" : "Copy response"}
                  >
                    {copied ? (
                      <Check className="w-3.5 h-3.5 text-green-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                )}
              </div>

              {/* Markdown parsed content */}
              <div 
                className="prose prose-invert prose-sm max-w-none markdown-content"
                dangerouslySetInnerHTML={{ __html: parseMarkdown(isTypingComplete ? message.content : displayedContent) }}
              />

              <style jsx global>{`
            /* Custom Scrollbar Styles */
            .markdown-content .table-wrapper,
            .markdown-content pre {
              scrollbar-width: thin;
              scrollbar-color: rgba(139, 92, 246, 0.3) rgba(255, 255, 255, 0.05);
            }
            
            .markdown-content .table-wrapper::-webkit-scrollbar,
            .markdown-content pre::-webkit-scrollbar {
              width: 6px;
              height: 6px;
            }
            
            .markdown-content .table-wrapper::-webkit-scrollbar-track,
            .markdown-content pre::-webkit-scrollbar-track {
              background: rgba(255, 255, 255, 0.02);
              border-radius: 3px;
            }
            
            .markdown-content .table-wrapper::-webkit-scrollbar-thumb,
            .markdown-content pre::-webkit-scrollbar-thumb {
              background: rgba(139, 92, 246, 0.3);
              border-radius: 3px;
              transition: background 0.2s;
            }
            
            .markdown-content .table-wrapper::-webkit-scrollbar-thumb:hover,
            .markdown-content pre::-webkit-scrollbar-thumb:hover {
              background: rgba(139, 92, 246, 0.5);
            }
            
            .markdown-content .table-wrapper::-webkit-scrollbar-corner,
            .markdown-content pre::-webkit-scrollbar-corner {
              background: rgba(255, 255, 255, 0.02);
            }

            /* Table Container with Scroll */
            .markdown-content .table-wrapper {
              overflow: auto;
              max-width: 100%;
              max-height: 500px;
              margin: 1rem 0;
              border-radius: 8px;
              border: 1px solid rgba(255, 255, 255, 0.1);
              background: rgba(0, 0, 0, 0.2);
            }
            
            .markdown-content table {
              width: 100%;
              min-width: 500px;
              border-collapse: collapse;
              margin: 0;
            }
            
            .markdown-content th,
            .markdown-content td {
              border: 1px solid rgba(255, 255, 255, 0.1);
              padding: 0.75rem 1rem;
              text-align: left;
              white-space: nowrap;
            }
            
            .markdown-content th {
              background: rgba(139, 92, 246, 0.15);
              font-weight: 600;
              color: rgba(255, 255, 255, 0.95);
              position: sticky;
              top: 0;
              z-index: 10;
              backdrop-filter: blur(8px);
              border-bottom: 2px solid rgba(139, 92, 246, 0.3);
            }
            
            .markdown-content td {
              color: rgba(255, 255, 255, 0.75);
              background: rgba(0, 0, 0, 0.1);
            }
            
            .markdown-content tr:hover td {
              background: rgba(139, 92, 246, 0.08);
              color: rgba(255, 255, 255, 0.9);
            }

            /* Code Block Styles with Scroll */
            .markdown-content pre {
              background: rgba(0, 0, 0, 0.3);
              border-radius: 8px;
              padding: 1rem;
              margin: 1rem 0;
              overflow: auto;
              max-width: 100%;
              max-height: 400px;
              border: 1px solid rgba(255, 255, 255, 0.1);
              box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            }
            
            .markdown-content pre code {
              display: block;
              color: rgba(255, 255, 255, 0.85);
              font-family: 'Courier New', monospace;
              font-size: 0.875rem;
              line-height: 1.6;
            }

            /* Enhanced Typography */
            .markdown-content p {
              margin: 0.75rem 0;
              line-height: 1.7;
              color: rgba(255, 255, 255, 0.85);
            }
            
            .markdown-content ul,
            .markdown-content ol {
              margin: 0.75rem 0;
              padding-left: 1.5rem;
            }
            
            .markdown-content li {
              margin: 0.5rem 0;
              line-height: 1.6;
            }

            /* Inline Code */
            .markdown-content code {
              background: rgba(139, 92, 246, 0.15);
              padding: 0.2rem 0.5rem;
              border-radius: 4px;
              font-size: 0.875rem;
              border: 1px solid rgba(139, 92, 246, 0.2);
            }

            /* Links */
            .markdown-content a {
              color: rgba(167, 139, 250, 0.9);
              text-decoration: none;
              border-bottom: 1px solid rgba(167, 139, 250, 0.3);
              transition: all 0.2s;
            }
            
            .markdown-content a:hover {
              color: rgba(167, 139, 250, 1);
              border-bottom-color: rgba(167, 139, 250, 0.6);
            }

            /* Blockquotes */
            .markdown-content blockquote {
              border-left: 3px solid rgba(139, 92, 246, 0.4);
              padding-left: 1rem;
              margin: 1rem 0;
              font-style: italic;
              color: rgba(255, 255, 255, 0.7);
              background: rgba(139, 92, 246, 0.05);
              padding: 0.75rem 1rem;
              border-radius: 0 4px 4px 0;
            }

            /* Headers */
            .markdown-content h1,
            .markdown-content h2,
            .markdown-content h3,
            .markdown-content h4 {
              margin-top: 1.5rem;
              margin-bottom: 0.75rem;
              font-weight: 600;
              color: rgba(255, 255, 255, 0.95);
            }
          `}</style>
            </>
          )}
          
          {/* Typing indicator */}
          {!isTypingComplete && !isUser && (
            <motion.span
              className="inline-block w-1 h-4 bg-violet-400 ml-1"
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.5, repeat: Infinity }}
            />
          )}

          {/* Timestamp */}
          <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/[0.05]">
            <span className="text-[10px] text-white/30">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            {!isUser && (
              <span className="text-[10px] text-violet-400/40 font-mono">AI</span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
