"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { motion } from "framer-motion";
import { Bot, ArrowRight, MessageSquare, Sparkles, Zap } from "lucide-react";

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push("/chat");
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#0A0A0B] text-white relative overflow-hidden">
      {/* Background Glow Effects */}
      <div className="absolute inset-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-1/4 w-125 h-125 bg-violet-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse" />
        <div className="absolute bottom-[-10%] right-1/4 w-125 h-125 bg-indigo-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse delay-700" />
        <div className="absolute top-1/3 right-1/3 w-72 h-72 bg-fuchsia-500/8 rounded-full mix-blend-normal filter blur-[96px] animate-pulse delay-1000" />
      </div>

      {/* Grid Pattern Overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
        }}
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center gap-10 px-6 max-w-2xl text-center">
        {/* Animated Icon */}
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, type: "spring", stiffness: 200 }}
          className="relative"
        >
          <div className="w-20 h-20 rounded-2xl bg-linear-to-br from-violet-500/20 to-indigo-500/20 border border-white/8 flex items-center justify-center backdrop-blur-xl shadow-2xl shadow-violet-500/10">
            <Bot className="w-10 h-10 text-violet-400" />
          </div>
          <motion.div
            className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-green-400 border-2 border-[#0A0A0B]"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ repeat: Infinity, duration: 2 }}
          />
        </motion.div>

        {/* Heading */}
        <motion.div
          className="space-y-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
        >
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight bg-clip-text text-transparent bg-linear-to-b from-white to-white/50 leading-tight">
            AI Task Assistant
          </h1>
          <p className="text-base sm:text-lg text-white/40 max-w-md mx-auto leading-relaxed">
            Manage your tasks effortlessly with natural language. Just chat — your AI agent handles the rest.
          </p>
        </motion.div>

        {/* Feature Pills */}
        <motion.div
          className="flex flex-wrap items-center justify-center gap-3"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          {[
            { icon: MessageSquare, label: "Natural Language" },
            { icon: Zap, label: "Instant Actions" },
            { icon: Sparkles, label: "AI Powered" },
          ].map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/3 border border-white/6 text-sm text-white/50"
            >
              <Icon className="w-3.5 h-3.5 text-violet-400/70" />
              {label}
            </div>
          ))}
        </motion.div>

        {/* CTA Buttons */}
        <motion.div
          className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.45 }}
        >
          <motion.button
            onClick={() => router.push("/register")}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-white text-[#0A0A0B] font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-white/10 hover:shadow-white/20 transition-shadow"
          >
            Get Started
            <ArrowRight className="w-4 h-4" />
          </motion.button>
          <motion.button
            onClick={() => router.push("/login")}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-white/4 border border-white/8 text-white/70 font-medium text-sm hover:bg-white/7 hover:text-white transition-all"
          >
            Sign In
          </motion.button>
        </motion.div>
      </div>

      {/* Bottom Fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-linear-to-t from-[#0A0A0B] to-transparent pointer-events-none" />
    </div>
  );
}
