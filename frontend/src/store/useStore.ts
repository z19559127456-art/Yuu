import { create } from 'zustand';
import type { Agent, Conversation, Message, NavItem, HistoryRecord, GroupConversation, UpdateState, Plan, SubTask, GroupMode } from '@/types';

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

  // Free dialogue
  freeDialogueActive: Record<string, boolean>;
  typingAgents: Record<string, string[]>;
  consensusResult: { group_id: string; summary: string; dissenting: string[] } | null;

  // Task dispatch
  currentPlan: Plan | null;

  // Approval
  pendingApproval: { request_id: string; type: string; approval_type: string; context: Record<string, unknown>; requester: string; timeout_seconds: number; dangerous: boolean } | null;

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

  setFreeDialogueActive: (groupId: string, active: boolean) => void;
  setTypingAgents: (groupId: string, agents: string[]) => void;
  setConsensusResult: (result: { group_id: string; summary: string; dissenting: string[] } | null) => void;
  setCurrentPlan: (plan: Plan | null) => void;
  updateSubtask: (subtaskId: string, updates: Partial<{ status: SubTask['status']; result: Record<string, unknown> }>) => void;
  setPendingApproval: (approval: { request_id: string; type: string; approval_type: string; context: Record<string, unknown>; requester: string; timeout_seconds: number; dangerous: boolean } | null) => void;
  updateGroupMode: (groupId: string, mode: GroupMode) => void;
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

  freeDialogueActive: {},
  typingAgents: {},
  consensusResult: null,
  currentPlan: null,
  pendingApproval: null,

  setFreeDialogueActive: (groupId, active) =>
    set((state) => ({
      freeDialogueActive: { ...state.freeDialogueActive, [groupId]: active },
    })),
  setTypingAgents: (groupId, agents) =>
    set((state) => ({
      typingAgents: { ...state.typingAgents, [groupId]: agents },
    })),
  setConsensusResult: (result) => set({ consensusResult: result }),
  setCurrentPlan: (plan) => set({ currentPlan: plan }),
  updateSubtask: (subtaskId, updates) =>
    set((state) => ({
      currentPlan: state.currentPlan
        ? {
            ...state.currentPlan,
            subtasks: state.currentPlan.subtasks.map((st) =>
              st.id === subtaskId ? { ...st, ...updates } : st
            ),
          }
        : null,
    })),
  setPendingApproval: (approval) => set({ pendingApproval: approval }),
  updateGroupMode: (groupId, mode) =>
    set((state) => ({
      groups: state.groups.map((g) =>
        g.id === groupId ? { ...g, mode } : g
      ),
    })),
}));
