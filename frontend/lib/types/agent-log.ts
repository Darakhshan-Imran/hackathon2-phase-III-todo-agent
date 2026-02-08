/**
 * Types for agent execution logs and real-time updates
 */

export interface AgentLogEntry {
  id: string;
  type: 'reasoning' | 'tool_call' | 'tool_result' | 'decision';
  timestamp: Date;
  content: string;
  toolName?: string;
  metadata?: Record<string, unknown>;
}

export interface AgentExecutionLog {
  entries: AgentLogEntry[];
  status: 'running' | 'complete' | 'error';
}
