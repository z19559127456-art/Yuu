export interface AgentPersonality {
  style: string;
  tone: string;
  verbosity: string;
}

export interface CLIToolConfig {
  enabled: boolean;
  allowed_commands: string[];
  blocked_commands: string[];
}

export interface WebToolConfig {
  enabled: boolean;
  max_pages: number;
  allowed_domains: string[];
  blocked_domains: string[];
}

export interface UIToolConfig {
  enabled: boolean;
}

export interface VisionToolConfig {
  enabled: boolean;
}

export interface ToolsConfig {
  cli: CLIToolConfig;
  web: WebToolConfig;
  ui_automation: UIToolConfig;
  vision: VisionToolConfig;
}

export interface MemoryConfig {
  mode: string;
  max_history_turns: number;
  summary_threshold: number;
}

export interface ConcurrencyConfig {
  max_parallel_tasks: number;
  queue_strategy: string;
}

export interface Agent {
  id: string;
  name: string;
  avatar: string;
  role: string;
  system_prompt: string;
  model_provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  api_base_url: string;
  api_key: string;
  personality: AgentPersonality;
  tools_config: ToolsConfig;
  skills: string[];
  memory_config: MemoryConfig;
  concurrency_config: ConcurrencyConfig;
  is_active: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  agent_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Attachment {
  type: 'file' | 'image' | 'code';
  name: string;
  data?: string;
  path?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResult {
  tool_call_id: string;
  result: unknown;
  status: 'success' | 'error';
}

export interface Message {
  id: string;
  conversation_id: string;
  group_id?: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  type: string;
  content: string;
  content_html?: string;
  attachments: Attachment[];
  tool_calls: ToolCall[];
  tool_results: ToolResult[];
  reply_to: string;
  is_edited: boolean;
  edited_from: string;
  is_pinned: boolean;
  is_remembered: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Plan {
  id: string;
  agent_id: string;
  conversation_id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  subtasks: SubTask[];
  created_at: string;
  updated_at: string;
}

export interface SubTask {
  id: string;
  plan_id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  depends_on: string[];
  result: Record<string, unknown>;
  assigned_agent_id: string;
  order_index: number;
  start_time: string;
  end_time: string;
  created_at: string;
  updated_at: string;
}

export type GroupMode = 'task' | 'discussion' | 'free_dialogue';

export interface GroupConversation {
  id: string;
  title: string;
  topic: string;
  mode: GroupMode;
  status: 'active' | 'archived';
  created_by: string;
  participants?: GroupParticipant[];
  created_at: string;
  updated_at: string;
}

export interface GroupParticipant {
  id: string;
  group_id: string;
  agent_id: string;
  role: 'moderator' | 'participant' | 'observer';
  joined_at: string;
}

export interface HistoryRecord {
  id: string;
  agent_id: string;
  conversation_id: string;
  plan_id: string;
  subtask_id: string;
  task_type: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  status: string;
  error_message: string;
  start_time: string;
  end_time: string;
  duration_ms: number;
  created_at: string;
}

export type NavItem = 'chats' | 'contacts' | 'settings';

export type UpdateStatus = 'checking' | 'downloading' | 'ready' | 'up-to-date' | 'error';

export interface UpdateState {
  status: UpdateStatus | null;
  version?: string;
  percent?: number;
  error?: string;
}

// WebSocket client messages
export type WSClientMessage =
  | { type: 'ping' }
  | { type: 'get_agents' }
  | { type: 'create_agent'; name: string; role?: string; system_prompt?: string; model_provider?: string; model_name?: string; temperature?: number; api_base_url?: string; api_key?: string; personality?: AgentPersonality; tools_config?: ToolsConfig; skills?: string[] }
  | { type: 'update_agent'; agent_id: string; name?: string; role?: string; system_prompt?: string; model_provider?: string; model_name?: string; temperature?: number; api_base_url?: string; api_key?: string; personality?: AgentPersonality; tools_config?: ToolsConfig; skills?: string[]; is_active?: boolean }
  | { type: 'delete_agent'; agent_id: string }
  | { type: 'get_conversations'; agent_id: string }
  | { type: 'get_messages'; conversation_id: string }
  | { type: 'create_conversation'; agent_id: string }
  | { type: 'delete_conversation'; conversation_id: string }
  | { type: 'send_message'; conversation_id: string; content: string }
  // Tool calls
  | { type: 'tool_call'; conversation_id: string; tool_name: string; arguments: Record<string, unknown> }
  // Plans
  | { type: 'create_plan'; conversation_id: string; goal: string; context?: string }
  | { type: 'get_plans'; conversation_id?: string }
  // Group chat
  | { type: 'group_send'; group_id: string; content: string }
  | { type: 'get_groups' }
  | { type: 'get_group_messages'; group_id: string }
  | { type: 'create_group'; title: string; topic?: string; mode?: string; participant_ids?: string[] }
  // Memory
  | { type: 'memory_query'; agent_id: string; query: string; k?: number }
  // Free dialogue
  | { type: 'start_free_dialogue'; group_id: string; topic?: string }
  | { type: 'free_dialogue_send'; group_id: string; content: string }
  | { type: 'switch_group_mode'; group_id: string; mode: GroupMode }
  | { type: 'stop_free_dialogue'; group_id: string }
  // Task dispatch
  | { type: 'decompose_and_dispatch'; group_id: string; goal: string; context?: string }
  | { type: 'get_plan_progress'; plan_id: string }
  | { type: 'get_plan_detail'; plan_id: string }
  | { type: 'retry_subtask'; subtask_id: string }
  // Approval
  | { type: 'approval_response'; request_id: string; response: 'approved' | 'rejected' | 'modified'; feedback?: string; modified_params?: Record<string, unknown> }
  // Message operations
  | { type: 'edit_message'; message_id: string; content: string }
  | { type: 'recall_message'; message_id: string }
  | { type: 'reference_message'; conversation_id: string; message_id: string; content: string };

// WebSocket server messages
export type WSServerMessage =
  | { type: 'pong' }
  | { type: 'agent_list'; agents: Agent[] }
  | { type: 'agent_created'; agent: Agent }
  | { type: 'agent_updated'; agent: Agent }
  | { type: 'agent_deleted'; agent_id: string }
  | { type: 'conversation_list'; conversations: Conversation[] }
  | { type: 'message_list'; messages: Message[] }
  | { type: 'conversation_created'; conversation: Conversation }
  | { type: 'conversation_deleted'; conversation_id: string }
  | { type: 'new_message'; message: Message }
  | { type: 'message_update'; message_id: string; content: string }
  | { type: 'message_final'; message: Message }
  // Tool results
  | { type: 'tool_result'; tool_call_id: string; result: unknown; status: 'success' | 'error'; error?: string }
  | { type: 'tool_executing'; tool_name: string; arguments: Record<string, unknown> }
  // Plans
  | { type: 'plan_list'; plans: unknown[] }
  | { type: 'plan_created'; plan: unknown }
  | { type: 'plan_updated'; plan: unknown }
  // Group messages
  | { type: 'group_list'; groups: GroupConversation[] }
  | { type: 'group_created'; group: GroupConversation }
  | { type: 'group_message_list'; messages: Message[] }
  | { type: 'group_message'; message: { id?: string; group_id: string; sender_id: string; sender_name?: string; content: string; timestamp: string } }
  // Memory
  | { type: 'memory_result'; results: unknown[] }
  // History
  | { type: 'history_list'; records: HistoryRecord[] }
  // Message operations
  | { type: 'message_edited'; message: Message }
  | { type: 'message_recalled'; message: Message }
  // Free dialogue
  | { type: 'free_dialogue_message'; group_id: string; agent_id: string; agent_name: string; content: string; reply_to?: string; timestamp: string }
  | { type: 'free_dialogue_typing'; group_id: string; agent_id: string; agent_name: string }
  | { type: 'consensus_reached'; group_id: string; summary: string; dissenting_agents?: string[] }
  | { type: 'free_dialogue_ended'; group_id: string; reason: string; turns: number; summary?: string }
  | { type: 'mode_switched'; group_id: string; mode: GroupMode }
  // Task dispatch
  | { type: 'plan_decomposed'; plan: Plan }
  | { type: 'subtask_started'; subtask_id: string; assigned_agent_id: string; agent_name: string }
  | { type: 'subtask_completed'; subtask_id: string; result: Record<string, unknown> }
  | { type: 'subtask_failed'; subtask_id: string; error: string }
  | { type: 'plan_progress'; plan_id: string; completed: number; total: number; running: number; failed: number; pending: number }
  | { type: 'plan_merged_result'; plan_id: string; merged_output: string; summary: string }
  // Approval
  | { type: 'approval_request'; request_id: string; approval_type: string; context: Record<string, unknown>; requester: string; timeout_seconds: number; dangerous?: boolean }
  | { type: 'approval_timeout'; request_id: string; approval_type: string }
  // Error
  | { type: 'error'; message: string };
