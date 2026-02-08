import { ChatRequest, ChatResponse } from "@/lib/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Send a message to the agent and get a response
 */
export async function sendMessage(
  message: string,
  sessionId?: string
): Promise<ChatResponse> {
  const token = localStorage.getItem("access_token");
  
  if (!token) {
    throw new Error("Not authenticated");
  }

  const requestBody: ChatRequest = {
    message,
    ...(sessionId && { session_id: sessionId }),
  };

  const response = await fetch(`${API_URL}/agent/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Unauthorized - please login again");
    }
    
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Clear the current chat session
 */
export async function clearSession(sessionId?: string): Promise<void> {
  const token = localStorage.getItem("access_token");
  
  if (!token) {
    throw new Error("Not authenticated");
  }

  const url = `${API_URL}/agent/chat/session/${sessionId || 'current'}`;

  const response = await fetch(url, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok && response.status !== 404) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to clear session");
  }
}
