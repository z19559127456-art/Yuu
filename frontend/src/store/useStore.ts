import { create } from 'zustand';
import type { Agent, Conversation, Message, NavItem, HistoryRecord, GroupConversation, UpdateState } from '@/types';

interface AppState {
  // WebSocket
  ws: WebSocket | null;
  wsConnected: boolean;

  // Navigation
  activeNav: NavItem;

  // Domain data
  agents: Agent[];
  conversations: Conversation[];
  groups: GroupConversation[];
  messages: Message[];
  historyRecords: HistoryRecord[];

  // Selection
  activeAgentId: string | null;
  activeConversationId: string | null;
  activeGroupId: string | null;

  // UI State
  showAgentForm: boolean;
  editingAgent: Agent | null;

  // Tool execution status
  toolExecuting: { toolName: string; arguments: string } | null;
  isAiResponding: boolean;
  lastError: string | null;

  // Update state
  updateState: UpdateState | null;

  // Actions
  setWs: (ws: WebSocket | null) => void;
  setWsConnected: (connected: boolean) => void;
  setActiveNav: (nav: NavItem) => void;

  setAgents: (agents: Agent[]) => void;
  addAgent: (agent: Agent) => void;
  updateAgent: (agent: Agent) => void;
  removeAgent: (agentId: string) => void;

  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  removeConversation: (conversationId: string) => void;

  setGroups: (groups: GroupConversation[]) => void;
  addGroup: (group: GroupConversation) => void;

  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  removeMessage: (messageId: string) => void;
  updateMessageContent: (messageId: string, content: string) => void;
  finalizeMessage: (message: Message) => void;

  setHistoryRecords: (records: HistoryRecord[]) => void;

  setActiveAgentId: (id: string | null) => void;
  setActiveConversationId: (id: string | null) => void;
  setActiveGroupId: (id: string | null) => void;

  setShowAgentForm: (show: boolean) => void;
  setEditingAgent: (agent: Agent | null) => void;

  setToolExecuting: (exec: { toolName: string; arguments: string } | null) => void;
  setIsAiResponding: (responding: boolean) => void;
  setLastError: (error: string | null) => void;

  setUpdateState: (updateState: UpdateState | null) => void;
}

export const useStore = create<AppState>((set) => ({
  ws: null,
  wsConnected: false,
  activeNav: 'chats',

  agents: [],
  conversations: [],
  groups: [],
  messages: [],
  historyRecords: [],

  activeAgentId: null,
  activeConversationId: null,
  activeGroupId: null,

  showAgentForm: false,
  editingAgent: null,

  toolExecuting: null,
  isAiResponding: false,
  lastError: null,

  setWs: (ws) => set({ ws }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  setActiveNav: (nav) => set({ activeNav: nav }),

  setAgents: (agents) => set({ agents }),
  addAgent: (agent) =>
    set((state) => ({ agents: [...state.agents, agent] })),
  updateAgent: (agent) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === agent.id ? agent : a)),
    })),
  removeAgent: (agentId) =>
    set((state) => ({
      agents: state.agents.filter((a) => a.id !== agentId),
    })),

  setConversations: (conversations) => set({ conversations }),
  addConversation: (conversation) =>
    set((state) => ({
      conversations: [conversation, ...state.conversations],
    })),
  removeConversation: (conversationId) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== conversationId),
    })),

  setGroups: (groups) => set({ groups }),
  addGroup: (group) =>
    set((state) => ({ groups: [group, ...state.groups] })),

  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  removeMessage: (messageId) =>
    set((state) => ({
      messages: state.messages.filter((m) => m.id !== messageId),
    })),
  updateMessageContent: (messageId, content) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, content } : m
      ),
    })),
  finalizeMessage: (message) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === message.id ? message : m
      ),
    })),

  setHistoryRecords: (records) => set({ historyRecords: records }),

  setActiveAgentId: (id) => set({ activeAgentId: id }),
  setActiveConversationId: (id) => set({ activeConversationId: id }),
  setActiveGroupId: (id) => set({ activeGroupId: id }),

  setShowAgentForm: (show) => set({ showAgentForm: show }),
  setEditingAgent: (agent) => set({ editingAgent: agent }),

  setToolExecuting: (exec) => set({ toolExecuting: exec }),
  setIsAiResponding: (responding) => set({ isAiResponding: responding }),
  setLastError: (error) => set({ lastError: error }),

  updateState: null,
  setUpdateState: (updateState) => set({ updateState }),
}));
