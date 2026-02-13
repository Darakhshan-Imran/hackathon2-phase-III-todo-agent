export interface Notification {
  id: number;
  user_id: number;
  task_id: number;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: Notification[];
  unread_count: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("access_token");
  if (!token) throw new Error("Not authenticated");
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

export async function getNotifications(): Promise<NotificationListResponse> {
  const response = await fetch(`${API_URL}/notifications`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error("Failed to fetch notifications");
  }

  return response.json();
}

export async function markAsRead(notificationId: number): Promise<void> {
  const response = await fetch(
    `${API_URL}/notifications/${notificationId}/read`,
    {
      method: "PATCH",
      headers: getAuthHeaders(),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to mark notification as read");
  }
}

export async function markAllAsRead(): Promise<void> {
  const response = await fetch(`${API_URL}/notifications/read-all`, {
    method: "PATCH",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error("Failed to mark all notifications as read");
  }
}
