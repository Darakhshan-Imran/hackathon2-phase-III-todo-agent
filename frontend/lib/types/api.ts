export interface AgentLog {
  step: number;
  action: string;  // 'tool_call', 'tool_result', 'thinking', 'error'
  details: string;
  timestamp?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  tasks_affected?: number[];
  agent_logs?: AgentLog[];
  error_details?: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ErrorResponse {
  detail: string | {
    error: string;
    details: string;
    type: string;
  };
}
