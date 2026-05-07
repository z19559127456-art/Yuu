import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '@/store/useStore';
import type { Agent, Conversation, Message, HistoryRecord } from '@/types';

function makeAgent(id = 'a1', name = '测试助手'): Agent {
  return {
    id, name, avatar: '', role: '', system_prompt: '',
    model_provider: 'openai', model_name: 'gpt-4o',
    temperature: 0.7, max_tokens: 4096,
    api_base_url: '', api_key: '',
    personality: { style: '严谨', tone: '专业', verbosity: 'concise' },
    tools_config: {
      cli: { enabled: true, allowed_commands: ['ls'], blocked_commands: [] },
      web: { enabled: false, max_pages: 10, allowed_domains: [], blocked_domains: [] },
      ui_automation: { enabled: false },
      vision: { enabled: false },
    },
    skills: [], memory_config: { mode: 'persistent', max_history_turns: 100, summary_threshold: 50 },
    concurrency_config: { max_parallel_tasks: 3, queue_strategy: 'fifo' },
    is_active: true, tags: [],
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  };
}

function makeConversation(id = 'c1', agentId = 'a1'): Conversation {
  return { id, agent_id: agentId, title: '测试对话', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' };
}

function makeMessage(id = 'm1', role: string = 'user', content = '你好'): Message {
  return {
    id, conversation_id: 'c1', role: role as Message['role'],
    type: 'text', content,
    attachments: [], tool_calls: [], tool_results: [],
    reply_to: '', is_edited: false, edited_from: '',
    is_pinned: false, is_remembered: false,
    status: 'sent', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  };
}

describe('useStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useStore.setState({
      ws: null, wsConnected: false, activeNav: 'chats',
      agents: [], conversations: [], messages: [], historyRecords: [],
      activeAgentId: null, activeConversationId: null,
      showAgentForm: false, editingAgent: null,
      toolExecuting: null, isAiResponding: false, lastError: null,
    });
  });

  describe('initial state', () => {
    it('has correct defaults', () => {
      const state = useStore.getState();
      expect(state.wsConnected).toBe(false);
      expect(state.activeNav).toBe('chats');
      expect(state.agents).toEqual([]);
      expect(state.messages).toEqual([]);
    });
  });

  describe('Agent CRUD', () => {
    it('sets agents list', () => {
      const agents = [makeAgent('a1'), makeAgent('a2', 'Agent2')];
      useStore.getState().setAgents(agents);
      expect(useStore.getState().agents).toHaveLength(2);
    });

    it('adds an agent', () => {
      const agent = makeAgent();
      useStore.getState().addAgent(agent);
      expect(useStore.getState().agents).toHaveLength(1);
      expect(useStore.getState().agents[0].name).toBe('测试助手');
    });

    it('updates an agent', () => {
      useStore.getState().addAgent(makeAgent('a1', '旧名称'));
      useStore.getState().updateAgent(makeAgent('a1', '新名称'));
      expect(useStore.getState().agents[0].name).toBe('新名称');
    });

    it('removes an agent', () => {
      useStore.getState().addAgent(makeAgent('a1'));
      useStore.getState().addAgent(makeAgent('a2', 'Agent2'));
      useStore.getState().removeAgent('a1');
      expect(useStore.getState().agents).toHaveLength(1);
      expect(useStore.getState().agents[0].id).toBe('a2');
    });
  });

  describe('Conversation CRUD', () => {
    it('adds conversation to beginning', () => {
      useStore.getState().addConversation(makeConversation('c1'));
      useStore.getState().addConversation(makeConversation('c2'));
      // New conversations are prepended
      expect(useStore.getState().conversations[0].id).toBe('c2');
    });

    it('removes conversation', () => {
      useStore.getState().addConversation(makeConversation('c1'));
      useStore.getState().addConversation(makeConversation('c2'));
      useStore.getState().removeConversation('c1');
      expect(useStore.getState().conversations).toHaveLength(1);
    });

    it('sets conversations list', () => {
      const convs = [makeConversation('c1'), makeConversation('c2')];
      useStore.getState().setConversations(convs);
      expect(useStore.getState().conversations).toHaveLength(2);
    });
  });

  describe('Message management', () => {
    it('adds message', () => {
      const msg = makeMessage();
      useStore.getState().addMessage(msg);
      expect(useStore.getState().messages).toHaveLength(1);
    });

    it('updates message content (streaming)', () => {
      const msg = makeMessage('m1', 'assistant', 'hel');
      useStore.getState().addMessage(msg);
      useStore.getState().updateMessageContent('m1', 'hello world');
      expect(useStore.getState().messages[0].content).toBe('hello world');
    });

    it('finalizes message', () => {
      const msg = makeMessage('m1', 'assistant', 'hel', );
      useStore.getState().addMessage(msg);
      const final = { ...msg, content: 'hello world', status: 'sent' as const };
      useStore.getState().finalizeMessage(final);
      expect(useStore.getState().messages[0].content).toBe('hello world');
      expect(useStore.getState().messages[0].status).toBe('sent');
    });
  });

  describe('UI State', () => {
    it('sets active nav', () => {
      useStore.getState().setActiveNav('contacts');
      expect(useStore.getState().activeNav).toBe('contacts');
    });

    it('toggles agent form', () => {
      useStore.getState().setShowAgentForm(true);
      expect(useStore.getState().showAgentForm).toBe(true);
    });

    it('sets editing agent', () => {
      const agent = makeAgent();
      useStore.getState().setEditingAgent(agent);
      expect(useStore.getState().editingAgent).toEqual(agent);
    });

    it('sets tool executing status', () => {
      useStore.getState().setToolExecuting({ toolName: 'cli', arguments: 'ls' });
      expect(useStore.getState().toolExecuting?.toolName).toBe('cli');
      useStore.getState().setToolExecuting(null);
      expect(useStore.getState().toolExecuting).toBeNull();
    });

    it('sets AI responding state', () => {
      useStore.getState().setIsAiResponding(true);
      expect(useStore.getState().isAiResponding).toBe(true);
    });

    it('manages last error', () => {
      useStore.getState().setLastError('Something went wrong');
      expect(useStore.getState().lastError).toBe('Something went wrong');
      useStore.getState().setLastError(null);
      expect(useStore.getState().lastError).toBeNull();
    });
  });
});
