import { 
  LoginCredentials, 
  RegisterData, 
  AuthTokens, 
  User 
} from "@/lib/types/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Register a new user
 */
export async function register(data: RegisterData): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Registration failed");
  }

  return response.json();
}

/**
 * Login with username and password
 */
export async function login(credentials: LoginCredentials): Promise<AuthTokens> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Login failed");
  }

  return response.json();
}

/**
 * Get current user information
 */
export async function getCurrentUser(): Promise<User> {
  const token = localStorage.getItem("access_token");
  
  if (!token) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(`${API_URL}/auth/me`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Unauthorized");
    }
    
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to get user");
  }

  return response.json();
}

/**
 * Logout (client-side only - clears tokens)
 */
export async function logout(): Promise<void> {
  localStorage.removeItem("access_token");
  localStorage.removeItem("token_type");
}
