"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { motion } from "framer-motion";
import { UserPlus, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ErrorAlert } from "@/components/ui/error-alert";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState("");
  const { register, isAuthenticated, error, clearError } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/chat");
    }
  }, [isAuthenticated, router]);

  const validateForm = (): boolean => {
    setValidationError("");

    if (username.trim().length < 3) {
      setValidationError("Username must be at least 3 characters");
      return false;
    }

    if (username.trim().length > 50) {
      setValidationError("Username must be less than 50 characters");
      return false;
    }

    if (!email.includes("@")) {
      setValidationError("Please enter a valid email address");
      return false;
    }

    if (password.length < 8) {
      setValidationError("Password must be at least 8 characters");
      return false;
    }

    if (password !== confirmPassword) {
      setValidationError("Passwords do not match");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
      });
      // Redirect handled by useEffect after auto-login
    } catch (err) {
      // Error is handled by useAuth hook
      console.error("Registration failed:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayError = validationError || error;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#0A0A0B] text-white p-6 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 w-full h-full overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse delay-700" />
        <div className="absolute top-1/4 right-1/3 w-64 h-64 bg-fuchsia-500/10 rounded-full mix-blend-normal filter blur-[96px] animate-pulse delay-1000" />
      </div>

      {/* Error Alert */}
      {displayError && (
        <ErrorAlert 
          message={displayError} 
          onDismiss={() => {
            setValidationError("");
            clearError();
          }}
        />
      )}

      <motion.div
        className="w-full max-w-md relative z-10"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        {/* Header */}
        <div className="text-center mb-8">
          <motion.h1
            className="text-3xl font-medium tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white/90 to-white/40 pb-1"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            Create Account
          </motion.h1>
          <motion.p
            className="text-sm text-white/40 mt-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            Sign up to start managing your tasks with AI
          </motion.p>
        </div>

        {/* Register Form */}
        <motion.div
          className="backdrop-blur-2xl bg-white/[0.02] rounded-2xl border border-white/[0.05] shadow-2xl p-8"
          initial={{ scale: 0.98 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.1 }}
        >
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username */}
            <div className="space-y-2">
              <label 
                htmlFor="username" 
                className="text-sm text-white/70 font-medium"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isSubmitting}
                className={cn(
                  "w-full px-4 py-3 rounded-lg",
                  "bg-white/[0.03] border border-white/[0.05]",
                  "text-white/90 placeholder:text-white/20",
                  "focus:outline-none focus:ring-2 focus:ring-violet-500/30",
                  "transition-all duration-200",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
                placeholder="Choose a username (3-50 characters)"
                required
                autoComplete="username"
                minLength={3}
                maxLength={50}
              />
            </div>

            {/* Email */}
            <div className="space-y-2">
              <label 
                htmlFor="email" 
                className="text-sm text-white/70 font-medium"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isSubmitting}
                className={cn(
                  "w-full px-4 py-3 rounded-lg",
                  "bg-white/[0.03] border border-white/[0.05]",
                  "text-white/90 placeholder:text-white/20",
                  "focus:outline-none focus:ring-2 focus:ring-violet-500/30",
                  "transition-all duration-200",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
                placeholder="Enter your email address"
                required
                autoComplete="email"
              />
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label 
                htmlFor="password" 
                className="text-sm text-white/70 font-medium"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
                className={cn(
                  "w-full px-4 py-3 rounded-lg",
                  "bg-white/[0.03] border border-white/[0.05]",
                  "text-white/90 placeholder:text-white/20",
                  "focus:outline-none focus:ring-2 focus:ring-violet-500/30",
                  "transition-all duration-200",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
                placeholder="Create a password (min. 8 characters)"
                required
                autoComplete="new-password"
                minLength={8}
              />
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <label 
                htmlFor="confirmPassword" 
                className="text-sm text-white/70 font-medium"
              >
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isSubmitting}
                className={cn(
                  "w-full px-4 py-3 rounded-lg",
                  "bg-white/[0.03] border border-white/[0.05]",
                  "text-white/90 placeholder:text-white/20",
                  "focus:outline-none focus:ring-2 focus:ring-violet-500/30",
                  "transition-all duration-200",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
                placeholder="Confirm your password"
                required
                autoComplete="new-password"
                minLength={8}
              />
            </div>

            {/* Submit Button */}
            <motion.button
              type="submit"
              disabled={isSubmitting || !username.trim() || !email.trim() || !password || !confirmPassword}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                "w-full px-4 py-3 rounded-lg text-sm font-medium transition-all",
                "flex items-center justify-center gap-2 mt-6",
                !isSubmitting && username.trim() && email.trim() && password && confirmPassword
                  ? "bg-white text-[#0A0A0B] shadow-lg shadow-white/10"
                  : "bg-white/[0.05] text-white/40 cursor-not-allowed"
              )}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating account...</span>
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
                  <span>Create Account</span>
                </>
              )}
            </motion.button>
          </form>

          {/* Login Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-white/40">
              Already have an account?{" "}
              <a
                href="/login"
                className="text-white/70 hover:text-white transition-colors underline"
              >
                Sign in
              </a>
            </p>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
