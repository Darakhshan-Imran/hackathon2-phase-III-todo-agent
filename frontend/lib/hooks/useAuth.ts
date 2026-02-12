"use client";

import { useState, useEffect } from "react";
import { User, LoginCredentials, RegisterData } from "@/lib/types/auth";
import * as authApi from "@/lib/api/auth";
import { saveTokens, clearTokens, isAuthenticated } from "@/lib/utils/token";

interface UseAuthReturn {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(() => isAuthenticated());

  // Load user on mount if authenticated
  useEffect(() => {
    async function loadUser() {
      if (!authenticated) {
        setIsLoading(false);
        return;
      }

      try {
        const currentUser = await authApi.getCurrentUser();
        setUser(currentUser);
      } catch (err) {
        console.error("Failed to load user:", err);
        // Token might be expired, clear it
        clearTokens();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }

    loadUser();
  }, [authenticated]);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    setError(null);

    try {
      const tokens = await authApi.login(credentials);
      saveTokens(tokens);
      setAuthenticated(true);

      const currentUser = await authApi.getCurrentUser();
      setUser(currentUser);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterData) => {
    setIsLoading(true);
    setError(null);

    try {
      // Register returns a message, not tokens
      await authApi.register(data);

      // Auto-login after successful registration
      const tokens = await authApi.login({
        username: data.username,
        password: data.password,
      });
      saveTokens(tokens);
      setAuthenticated(true);

      const currentUser = await authApi.getCurrentUser();
      setUser(currentUser);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Registration failed";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    
    try {
      await authApi.logout();
      clearTokens();
      setAuthenticated(false);
      setUser(null);
    } catch (err) {
      console.error("Logout error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  return {
    user,
    isLoading,
    error,
    isAuthenticated: authenticated && user !== null,
    login,
    register,
    logout,
    clearError,
  };
}
