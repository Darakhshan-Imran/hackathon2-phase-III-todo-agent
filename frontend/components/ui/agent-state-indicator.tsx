"use client";

import { motion, AnimatePresence } from "framer-motion";
import { 
  Brain, 
  Wrench, 
  Database, 
  Search,
  CheckCircle2,
  Loader2,
  Sparkles,
  Zap
} from "lucide-react";

export type AgentState = 
  | 'idle'
  | 'sending'
  | 'reasoning'
  | 'tool_selecting'
  | 'tool_executing'
  | 'processing'
  | 'complete'
  | 'error';

export interface AgentStateIndicatorProps {
  state: AgentState;
  currentTool?: string;
  customMessage?: string;
}

const stateConfig = {
  idle: {
    icon: null,
    label: '',
    color: 'text-white/40',
    bgColor: 'from-white/5 to-white/5',
  },
  sending: {
    icon: Zap,
    label: 'Sending message',
    color: 'text-violet-400',
    bgColor: 'from-violet-500/10 to-indigo-500/10',
  },
  reasoning: {
    icon: Brain,
    label: 'Thinking',
    color: 'text-violet-400',
    bgColor: 'from-violet-500/10 to-fuchsia-500/10',
  },
  tool_selecting: {
    icon: Sparkles,
    label: 'Choosing action',
    color: 'text-fuchsia-400',
    bgColor: 'from-fuchsia-500/10 to-violet-500/10',
  },
  tool_executing: {
    icon: Wrench,
    label: 'Executing',
    color: 'text-indigo-400',
    bgColor: 'from-indigo-500/10 to-violet-500/10',
  },
  processing: {
    icon: Database,
    label: 'Processing',
    color: 'text-blue-400',
    bgColor: 'from-blue-500/10 to-indigo-500/10',
  },
  complete: {
    icon: CheckCircle2,
    label: 'Complete',
    color: 'text-green-400',
    bgColor: 'from-green-500/10 to-emerald-500/10',
  },
  error: {
    icon: null,
    label: 'Error',
    color: 'text-red-400',
    bgColor: 'from-red-500/10 to-rose-500/10',
  },
};

const toolLabels: Record<string, string> = {
  create_task: 'Creating task',
  list_tasks: 'Listing tasks',
  update_task: 'Updating task',
  delete_task: 'Deleting task',
  search_tasks_by_keyword: 'Searching tasks',
  get_task_details: 'Getting task details',
  execute_sql_query: 'Querying database',
  generate_sql_query: 'Generating SQL query',
};

export function AgentStateIndicator({ 
  state, 
  currentTool,
  customMessage 
}: AgentStateIndicatorProps) {
  if (state === 'idle') return null;

  const config = stateConfig[state];
  const Icon = config.icon;
  
  // Determine the display text
  let displayText = customMessage || config.label;
  
  if (state === 'tool_executing' && currentTool) {
    displayText = toolLabels[currentTool] || `Using ${currentTool}`;
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={state}
        className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50"
        initial={{ opacity: 0, y: 20, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.9 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
      >
        <div className={`
          backdrop-blur-2xl rounded-full px-5 py-3 
          shadow-2xl border border-white/10
          bg-gradient-to-r ${config.bgColor}
        `}>
          <div className="flex items-center gap-3">
            {/* Icon */}
            {Icon && (
              <motion.div
                animate={{ 
                  rotate: state === 'tool_executing' ? 360 : 0,
                  scale: [1, 1.1, 1]
                }}
                transition={{ 
                  rotate: { duration: 2, repeat: Infinity, ease: "linear" },
                  scale: { duration: 1.5, repeat: Infinity, ease: "easeInOut" }
                }}
              >
                <Icon className={`w-5 h-5 ${config.color}`} />
              </motion.div>
            )}
            
            {/* Agent Avatar */}
            <div className="w-8 h-7 rounded-full bg-white/[0.05] flex items-center justify-center">
              <motion.span 
                className="text-xs font-medium text-white/90 mb-0.5"
                animate={{ opacity: [0.6, 1, 0.6] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                zap
              </motion.span>
            </div>
            
            {/* Status Text with Animated Dots */}
            <div className="flex items-center gap-2">
              <span className={`text-sm font-medium ${config.color}`}>
                {displayText}
              </span>
              {state !== 'complete' && <AnimatedDots color={config.color} />}
            </div>
          </div>
        </div>
        
        {/* Glow Effect */}
        <motion.div
          className={`absolute inset-0 rounded-full blur-xl opacity-20 bg-gradient-to-r ${config.bgColor} -z-10`}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.2, 0.3, 0.2],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </motion.div>
    </AnimatePresence>
  );
}

function AnimatedDots({ color }: { color: string }) {
  return (
    <div className="flex items-center ml-1">
      {[1, 2, 3].map((dot) => (
        <motion.div
          key={dot}
          className={`w-1.5 h-1.5 rounded-full mx-0.5 ${color.replace('text-', 'bg-')}`}
          initial={{ opacity: 0.3 }}
          animate={{ 
            opacity: [0.3, 1, 0.3],
            scale: [0.85, 1.15, 0.85]
          }}
          transition={{
            duration: 1.4,
            repeat: Infinity,
            delay: dot * 0.2,
            ease: "easeInOut",
          }}
          style={{
            boxShadow: `0 0 8px currentColor`,
          }}
        />
      ))}
    </div>
  );
}

// Compact version for inline use
export function InlineAgentState({ 
  state, 
  currentTool 
}: { 
  state: AgentState; 
  currentTool?: string;
}) {
  if (state === 'idle' || state === 'complete') return null;

  const config = stateConfig[state];
  const Icon = config.icon;
  
  let displayText = config.label;
  if (state === 'tool_executing' && currentTool) {
    displayText = toolLabels[currentTool] || currentTool;
  }

  return (
    <motion.div
      className={`
        inline-flex items-center gap-2 px-3 py-1.5 rounded-full
        bg-gradient-to-r ${config.bgColor}
        border border-white/5
      `}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
    >
      {Icon && <Icon className={`w-3.5 h-3.5 ${config.color}`} />}
      <span className={`text-xs font-medium ${config.color}`}>
        {displayText}
      </span>
      <AnimatedDots color={config.color} />
    </motion.div>
  );
}

// Progress bar variant
export function AgentProgressBar({ 
  state,
  currentTool,
  stepsComplete = 0,
  totalSteps = 3
}: AgentStateIndicatorProps & { 
  stepsComplete?: number; 
  totalSteps?: number;
}) {
  if (state === 'idle') return null;

  const config = stateConfig[state];
  const progress = state === 'complete' ? 100 : (stepsComplete / totalSteps) * 100;
  
  return (
    <motion.div
      className="w-full max-w-md"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
    >
      {/* Label */}
      <div className="flex items-center justify-between mb-2">
        <InlineAgentState state={state} currentTool={currentTool} />
        <span className="text-xs text-white/40">
          {Math.round(progress)}%
        </span>
      </div>
      
      {/* Progress Bar */}
      <div className="h-1 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          className={`h-full bg-gradient-to-r ${config.bgColor} ${config.color}`}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        />
      </div>
    </motion.div>
  );
}
