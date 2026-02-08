import { AuthTokens } from "@/lib/types/auth";

const ACCESS_TOKEN_KEY = "access_token";
const TOKEN_TYPE_KEY = "token_type";

/**
 * Save authentication tokens to localStorage
 */
export function saveTokens(tokens: AuthTokens): void {
  if (typeof window === "undefined") return;
  
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(TOKEN_TYPE_KEY, tokens.token_type);
}

/**
 * Get access token from localStorage
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Get token type from localStorage
 */
export function getTokenType(): string | null {
  if (typeof window === "undefined") return null;
  
  return localStorage.getItem(TOKEN_TYPE_KEY);
}

/**
 * Get both tokens as AuthTokens object
 */
export function getTokens(): AuthTokens | null {
  const access_token = getAccessToken();
  const token_type = getTokenType();
  
  if (!access_token || !token_type) {
    return null;
  }
  
  return {
    access_token,
    token_type,
  };
}

/**
 * Clear all authentication tokens from localStorage
 */
export function clearTokens(): void {
  if (typeof window === "undefined") return;
  
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(TOKEN_TYPE_KEY);
}

/**
 * Check if user is authenticated (has valid tokens)
 */
export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}
