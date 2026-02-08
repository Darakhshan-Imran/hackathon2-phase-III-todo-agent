export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date | string;
  agentLogs?: string[];
  isStreaming?: boolean;
}

export type AgentState = 
  | 'idle'
  | 'sending'
  | 'reasoning'
  | 'tool_selecting'
  | 'tool_executing'
  | 'processing'
  | 'complete'
  | 'error';
