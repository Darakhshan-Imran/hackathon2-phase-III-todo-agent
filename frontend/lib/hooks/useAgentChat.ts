"use client";

import { useState, useCallback, useRef } from "react";
import { Message, AgentState } from "@/lib/types/message";
import * as agentApi from "@/lib/api/agent";

interface UseAgentChatReturn {
  messages: Message[];
  agentState: AgentState;
  isProcessing: boolean;
  error: string | null;
  sessionId: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  clearError: () => void;
  retryMessage: (messageId: string) => Promise<void>;
  editMessage: (messageId: string, newContent: string) => Promise<void>;
}

export function useAgentChat(): UseAgentChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [agentState, setAgentState] = useState<AgentState>("idle");
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  // Use ref to track current state for state machine transitions
  const stateRef = useRef<AgentState>("idle");

  /**
   * State machine for agent states
   * Simulates the agent's workflow through different stages
   */
  const transitionState = useCallback((newState: AgentState) => {
    stateRef.current = newState;
    setAgentState(newState);
  }, []);

  /**
   * Send a message to the agent
   */
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isProcessing) {
      return;
    }

    setIsProcessing(true);
    setError(null);
    
    // Add user message immediately (optimistic update)
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };
    
    setMessages(prev => [...prev, userMessage]);

    try {
      // Send to backend
      const response = await agentApi.sendMessage(content.trim(), sessionId || undefined);
      
      // Update session ID if returned
      if (response.session_id) {
        setSessionId(response.session_id);
      }
      
      // Use real agent logs from backend - ALWAYS prefer real logs over simulated
      const agentLogs = response.agent_logs && response.agent_logs.length > 0
        ? response.agent_logs.map(log => `[${log.action}] ${log.details}`)
        : ["⚠️ No execution logs captured"];
      
      // Add agent response with logs
      const agentMessage: Message = {
        id: `agent-${Date.now()}`,
        role: "assistant",
        content: response.response,
        timestamp: new Date().toISOString(),
        agentLogs: agentLogs,
        isStreaming: true,
      };
      
      setMessages(prev => [...prev, agentMessage]);
      
      // Complete state
      transitionState("complete");
      
      // Return to idle after brief delay
      setTimeout(() => {
        if (stateRef.current === "complete") {
          transitionState("idle");
        }
      }, 1500);
      
    } catch (err: any) {
      // Log error without exposing sensitive data
      if (process.env.NODE_ENV === 'development') {
        console.error("Failed to send message:", err.message || 'Unknown error');
      }
      
      // Extract detailed error information
      let errorMessage = "Failed to send message";
      let errorDetails = "";
      
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        // Handle both string and object error formats
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (typeof detail === 'object') {
          errorMessage = detail.error || "An error occurred";
          errorDetails = detail.details || "";
        }
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      
      // Add error message to chat
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `❌ **Error**\n\n${errorMessage}${errorDetails ? `\n\n${errorDetails}` : ''}`,
        timestamp: new Date().toISOString(),
        agentLogs: ["Error occurred during processing"],
      };
      setMessages(prev => [...prev, errorMsg]);
      
      setError(errorMessage);
      transitionState("error");
      
      // Return to idle after error display
      setTimeout(() => {
        if (stateRef.current === "error") {
          transitionState("idle");
        }
      }, 3000);
      
    } finally {
      setIsProcessing(false);
    }
  }, [isProcessing, sessionId, transitionState]);

  /**
   * Clear all messages and session
   */
  const clearMessages = useCallback(async () => {
    try {
      if (sessionId) {
        await agentApi.clearSession(sessionId);
      }
      setMessages([]);
      setSessionId(null);
      setAgentState("idle");
      setError(null);
    } catch (err) {
      console.error("Failed to clear session:", err);
      // Clear locally anyway
      setMessages([]);
      setSessionId(null);
    }
  }, [sessionId]);

  /**
   * Clear error message
   */
  const clearError = useCallback(() => {
    setError(null);
    if (stateRef.current === "error") {
      transitionState("idle");
    }
  }, [transitionState]);

  /**
   * Retry a message - resend the same message content
   */
  const retryMessage = useCallback(async (messageId: string) => {
    const message = messages.find(m => m.id === messageId);
    if (!message || message.role !== "user") {
      return;
    }
    
    // Resend the message content
    await sendMessage(message.content);
  }, [messages, sendMessage]);

  /**
   * Edit a message - update content and resend
   */
  const editMessage = useCallback(async (messageId: string, newContent: string) => {
    const messageIndex = messages.findIndex(m => m.id === messageId);
    if (messageIndex === -1) {
      return;
    }
    
    // Remove the old message and any subsequent messages
    setMessages(prev => prev.slice(0, messageIndex));
    
    // Send the edited message
    await sendMessage(newContent);
  }, [messages, sendMessage]);

  return {
    messages,
    agentState,
    isProcessing,
    error,
    sessionId,
    sendMessage,
    clearMessages,
    clearError,
    retryMessage,
    editMessage,
  };
}
