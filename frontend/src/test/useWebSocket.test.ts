import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStore } from '@/store/useStore';
import type { WSServerMessage, Agent, Conversation, Message, HistoryRecord } from '@/types';

// ---------------------------------------------------------------------------
// Fake WebSocket class — fully standalone, no prototype extension
// ---------------------------------------------------------------------------

const instances: FakeWebSocket[] = [];

class FakeWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  send = vi.fn();
  close = vi.fn();
  addEventListener = vi.fn();
  removeEventListener = vi.fn();

  // Expose readyState as a mutable property
  private _readyState = 0;
  get readyState() { return this._readyState; }
  set readyState(v: number) { this._readyState = v; }

  binaryType: BinaryType = 'blob';
  bufferedAmount = 0;
  extensions = '';
  protocol = '';
  CONNECTING = 0;
  OPEN = 1;
  CLOSING = 2;
  CLOSED = 3;

  constructor(url: string) {
    this.url = url;
    this._readyState = 0;
    instances.push(this);
  }
}

function latestWs() {
  return instances[instances.length - 1];
}

function openWs(ws: FakeWebSocket) {
  act(() => {
    ws.readyState = 1; // WebSocket.OPEN
    ws.onopen!(new Event('open'));
  });
}

function closeWs(ws: FakeWebSocket) {
  act(() => {
    ws.readyState = 3; // WebSocket.CLOSED
    ws.onclose!(new CloseEvent('close'));
  });
}

// ---------------------------------------------------------------------------
// Test data helpers
// ---------------------------------------------------------------------------

function makeAgent(id = 'a1', name = '测试助手'): Agent {
  return {
    id, name, avatar: '', role: '测试', system_prompt: '你是测试助手',
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

function makeMessage(id = 'm1', role: string = 'user', content = 'Hello'): Message {
  return {
    id, conversation_id: 'c1', role: role as Message['role'],
    type: 'text', content,
    attachments: [], tool_calls: [], tool_results: [],
    reply_to: '', is_edited: false, edited_from: '',
    is_pinned: false, is_remembered: false,
    status: 'sent', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
  };
}

function makeHistoryRecord(id = 'h1'): HistoryRecord {
  return {
    id, agent_id: 'a1', conversation_id: 'c1', plan_id: '', subtask_id: '',
    task_type: 'tool_cli', input: {}, output: {},
    status: 'success', error_message: '',
    start_time: '2026-01-01T00:00:00Z', end_time: '2026-01-01T00:00:01Z',
    duration_ms: 1000, created_at: '2026-01-01T00:00:00Z',
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useWebSocket', () => {
  beforeEach(() => {
    instances.length = 0;
    (globalThis as any).WebSocket = FakeWebSocket;

    useStore.setState({
      ws: null, wsConnected: false, activeNav: 'chats',
      agents: [], conversations: [], messages: [], historyRecords: [],
      activeAgentId: null, activeConversationId: null,
      showAgentForm: false, editingAgent: null,
      toolExecuting: null, isAiResponding: false, lastError: null,
    });

    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // -----------------------------------------------------------------------
  // Connection
  // -----------------------------------------------------------------------

  describe('connection', () => {
    it('creates WebSocket on mount', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      renderHook(() => useWebSocket());
      expect(instances.length).toBeGreaterThanOrEqual(1);
    });

    it('sets wsConnected on open', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      renderHook(() => useWebSocket());

      const ws = latestWs();
      openWs(ws);

      expect(useStore.getState().wsConnected).toBe(true);
    });

    it('sends get_agents on connect', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      renderHook(() => useWebSocket());

      const ws = latestWs();
      openWs(ws);

      expect(ws.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'get_agents' })
      );
    });

    it('sets wsConnected false on close', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      renderHook(() => useWebSocket());

      const ws = latestWs();
      openWs(ws);
      expect(useStore.getState().wsConnected).toBe(true);

      closeWs(ws);
      expect(useStore.getState().wsConnected).toBe(false);
    });

    it('closes ws on error', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      renderHook(() => useWebSocket());

      const ws = latestWs();
      act(() => { ws.onerror!(new Event('error')); });

      expect(ws.close).toHaveBeenCalled();
    });
  });

  // -----------------------------------------------------------------------
  // Reconnection
  // -----------------------------------------------------------------------

  describe('reconnection', () => {
    it('schedules reconnect after close', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      renderHook(() => useWebSocket());

      const ws = latestWs();
      closeWs(ws);
      act(() => { vi.advanceTimersByTime(1100); });

      expect(instances.length).toBeGreaterThanOrEqual(2);
    });

    it('uses exponential backoff', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      const { unmount } = renderHook(() => useWebSocket());

      for (let i = 0; i < 3; i++) {
        const ws = latestWs();
        closeWs(ws);
        const delay = [1000, 2000, 4000][i];
        act(() => { vi.advanceTimersByTime(delay + 100); });
      }

      expect(instances.length).toBe(4);
      unmount();
    });

    it('resets reconnect attempts on successful connection', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      renderHook(() => useWebSocket());

      // First close → reconnect
      const ws1 = latestWs();
      act(() => { ws1.onclose!(new CloseEvent('close')); });
      act(() => { vi.advanceTimersByTime(1100); });

      const ws2 = latestWs();
      act(() => { ws2.onopen!(new Event('open')); });

      // Close again — should start at first delay
      act(() => { ws2.onclose!(new CloseEvent('close')); });
      act(() => { vi.advanceTimersByTime(1100); });

      expect(instances.length).toBeGreaterThanOrEqual(3);
    });
  });

  // -----------------------------------------------------------------------
  // Server message handling
  // -----------------------------------------------------------------------

  describe('server messages', () => {
    async function setupHook() {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      renderHook(() => useWebSocket());
      const ws = latestWs();
      openWs(ws);
      return ws;
    }

    function sendMessage(ws: FakeWebSocket, data: WSServerMessage) {
      act(() => {
        ws.onmessage!(new MessageEvent('message', { data: JSON.stringify(data) }));
      });
    }

    it('handles agent_list and sets active agent', async () => {
      const ws = await setupHook();
      sendMessage(ws, { type: 'agent_list', agents: [makeAgent('a1', 'Agent1')] });

      expect(useStore.getState().agents).toHaveLength(1);
      expect(useStore.getState().activeAgentId).toBe('a1');
      expect(ws.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'create_conversation', agent_id: 'a1' })
      );
    });

    it('handles agent_created', async () => {
      const ws = await setupHook();
      const agent = makeAgent('a2', 'New Agent');
      sendMessage(ws, { type: 'agent_created', agent });
      expect(useStore.getState().agents).toHaveLength(1);
      expect(useStore.getState().agents[0].name).toBe('New Agent');
    });

    it('handles agent_updated', async () => {
      const ws = await setupHook();
      useStore.getState().addAgent(makeAgent('a1', 'Old Name'));
      sendMessage(ws, { type: 'agent_updated', agent: makeAgent('a1', 'Updated Name') });
      expect(useStore.getState().agents[0].name).toBe('Updated Name');
    });

    it('handles agent_deleted', async () => {
      const ws = await setupHook();
      useStore.getState().addAgent(makeAgent('a1'));
      sendMessage(ws, { type: 'agent_deleted', agent_id: 'a1' });
      expect(useStore.getState().agents).toHaveLength(0);
    });

    it('handles conversation_list', async () => {
      const ws = await setupHook();
      sendMessage(ws, { type: 'conversation_list', conversations: [makeConversation('c1'), makeConversation('c2')] });
      expect(useStore.getState().conversations).toHaveLength(2);
    });

    it('handles conversation_created', async () => {
      const ws = await setupHook();
      sendMessage(ws, { type: 'conversation_created', conversation: makeConversation('c3') });
      expect(useStore.getState().conversations).toHaveLength(1);
      expect(useStore.getState().activeConversationId).toBe('c3');
    });

    it('handles conversation_deleted', async () => {
      const ws = await setupHook();
      useStore.getState().addConversation(makeConversation('c1'));
      sendMessage(ws, { type: 'conversation_deleted', conversation_id: 'c1' });
      expect(useStore.getState().conversations).toHaveLength(0);
    });

    it('handles message_list', async () => {
      const ws = await setupHook();
      const msgs = [makeMessage('m1', 'user', '你好'), makeMessage('m2', 'assistant', '你好!')];
      sendMessage(ws, { type: 'message_list', messages: msgs });
      expect(useStore.getState().messages).toHaveLength(2);
    });

    it('handles new_message with sending status', async () => {
      const ws = await setupHook();
      const assistantMsg = { ...makeMessage('m1', 'assistant', ''), status: 'sending' as const };
      sendMessage(ws, { type: 'new_message', message: assistantMsg });
      expect(useStore.getState().isAiResponding).toBe(true);
    });

    it('handles message_update (streaming)', async () => {
      const ws = await setupHook();
      useStore.getState().addMessage(makeMessage('m1', 'assistant', 'H'));
      sendMessage(ws, { type: 'message_update', message_id: 'm1', content: 'Hello World' });
      expect(useStore.getState().messages[0].content).toBe('Hello World');
    });

    it('handles message_final and clears isAiResponding', async () => {
      const ws = await setupHook();
      useStore.getState().addMessage({ ...makeMessage('m1', 'assistant', 'partial'), status: 'sending' });
      useStore.getState().setIsAiResponding(true);

      const final = { ...makeMessage('m1', 'assistant', 'complete response'), status: 'sent' as const };
      sendMessage(ws, { type: 'message_final', message: final });

      expect(useStore.getState().messages[0].content).toBe('complete response');
      expect(useStore.getState().isAiResponding).toBe(false);
    });

    it('handles tool_executing', async () => {
      const ws = await setupHook();
      sendMessage(ws, { type: 'tool_executing', tool_name: 'cli', arguments: { command: 'ls' } });
      expect(useStore.getState().toolExecuting?.toolName).toBe('cli');
    });

    it('handles tool_result and clears toolExecuting', async () => {
      const ws = await setupHook();
      useStore.getState().setToolExecuting({ toolName: 'cli', arguments: 'ls' });
      sendMessage(ws, { type: 'tool_result', tool_call_id: 'cli', result: 'file list', status: 'success' });
      expect(useStore.getState().toolExecuting).toBeNull();
    });

    it('handles history_list', async () => {
      const ws = await setupHook();
      const records = [makeHistoryRecord('h1'), makeHistoryRecord('h2')];
      sendMessage(ws, { type: 'history_list', records });
      expect(useStore.getState().historyRecords).toHaveLength(2);
    });

    it('handles error message', async () => {
      const ws = await setupHook();
      sendMessage(ws, { type: 'error', message: '服务器错误' });
      expect(useStore.getState().lastError).toBe('服务器错误');
    });

    it('handles message_edited', async () => {
      const ws = await setupHook();
      useStore.getState().addMessage(makeMessage('m1', 'user', 'original'));
      const edited = { ...makeMessage('m1', 'user', 'modified'), is_edited: true };
      sendMessage(ws, { type: 'message_edited', message: edited });
      expect(useStore.getState().messages[0].content).toBe('modified');
    });

    it('handles message_recalled', async () => {
      const ws = await setupHook();
      useStore.getState().addMessage(makeMessage('m1', 'user', 'to recall'));
      const recalled = { ...makeMessage('m1', 'user', '[消息已撤回]'), status: 'cancelled' as const };
      sendMessage(ws, { type: 'message_recalled', message: recalled });
      expect(useStore.getState().messages[0].content).toBe('[消息已撤回]');
    });
  });

  // -----------------------------------------------------------------------
  // sendJson
  // -----------------------------------------------------------------------

  describe('sendJson', () => {
    it('sends JSON message when connected', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      const { result } = renderHook(() => useWebSocket());

      const ws = instances[0]; // first (and only) ws the hook created
      openWs(ws);

      // Hook sends get_agents on connect — verify that then send a custom message
      const getAgentsCall = ws.send.mock.calls.find(
        (c: any) => JSON.parse(c[0]).type === 'get_agents'
      );
      expect(getAgentsCall).toBeTruthy();

      act(() => {
        result.current.sendJson({ type: 'ping' });
      });

      const pingCall = ws.send.mock.calls.find(
        (c: any) => JSON.parse(c[0]).type === 'ping'
      );
      expect(pingCall).toBeTruthy();
    });

    it('does not send when not connected', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      const { result } = renderHook(() => useWebSocket());

      // Not connected — readyState is still 0 (CONNECTING)
      const beforeCount = instances[0].send.mock.calls.length;

      act(() => {
        result.current.sendJson({ type: 'ping' });
      });

      // No additional calls should have been made
      expect(instances[0].send.mock.calls.length).toBe(beforeCount);
    });
  });

  // -----------------------------------------------------------------------
  // Cleanup
  // -----------------------------------------------------------------------

  describe('cleanup', () => {
    it('cleans up on unmount', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      const { unmount } = renderHook(() => useWebSocket());

      const ws = latestWs();
      openWs(ws);

      unmount();
      expect(ws.close).toHaveBeenCalled();
    });

    it('does not reconnect after unmount', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      const { unmount } = renderHook(() => useWebSocket());

      unmount();
      act(() => { vi.advanceTimersByTime(20000); });

      expect(instances.length).toBe(1);
    });
  });

  // -----------------------------------------------------------------------
  // activeConversationId change triggers get_messages
  // -----------------------------------------------------------------------

  describe('activeConversationId watcher', () => {
    it('fetches messages when activeConversationId changes', async () => {
      const { useWebSocket } = await import('@/hooks/useWebSocket');
      renderHook(() => useWebSocket());

      const ws = instances[0];
      openWs(ws);

      act(() => {
        useStore.getState().setActiveConversationId('conv-456');
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      const getMsgCall = ws.send.mock.calls.find(
        (c: any) => {
          try { return JSON.parse(c[0]).type === 'get_messages'; } catch { return false; }
        }
      );
      expect(getMsgCall).toBeTruthy();
      expect(JSON.parse(getMsgCall[0]).conversation_id).toBe('conv-456');
    });
  });
});
