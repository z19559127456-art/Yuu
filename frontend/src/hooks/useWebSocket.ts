import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import type { WSServerMessage, WSClientMessage } from '@/types';

const WS_URL = 'ws://localhost:7890/ws';
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 10000];

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const handleMsgRef = useRef<(data: WSServerMessage) => void>(() => {});

  const {
    setWs,
    setWsConnected,
    setAgents,
    addAgent,
    updateAgent,
    removeAgent,
    setConversations,
    setMessages,
    addMessage,
    updateMessageContent,
    finalizeMessage,
    addConversation,
    removeConversation,
    addGroup,
    setGroups,
    setHistoryRecords,
    setActiveAgentId,
    setActiveConversationId,
    setActiveGroupId,
    setIsAiResponding,
    setToolExecuting,
    activeConversationId,
    activeGroupId,
  } = useStore();

  const scheduleReconnect = useCallback(() => {
    if (!mountedRef.current) return;
    const attempt = reconnectAttemptRef.current;
    const delay = RECONNECT_DELAYS[Math.min(attempt, RECONNECT_DELAYS.length - 1)];
    reconnectAttemptRef.current = attempt + 1;

    reconnectTimerRef.current = setTimeout(() => {
      if (mountedRef.current) connect();
    }, delay);
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    setWs(ws);

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close();
        return;
      }
      setWsConnected(true);
      reconnectAttemptRef.current = 0;

      // Fetch agents and groups on connect
      ws.send(JSON.stringify({ type: 'get_agents' } as WSClientMessage));
      ws.send(JSON.stringify({ type: 'get_groups' } as WSClientMessage));
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data: WSServerMessage = JSON.parse(event.data);
        handleMsgRef.current(data);
      } catch {
        console.error('Failed to parse WS message:', event.data);
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setWsConnected(false);
      scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  const handleServerMessage = useCallback(
    (data: WSServerMessage) => {
      switch (data.type) {
        case 'pong':
          break;

        // Agent CRUD
        case 'agent_list':
          setAgents(data.agents);
          if (data.agents.length > 0) {
            const first = data.agents[0];
            setActiveAgentId(first.id);
            const ws = wsRef.current;
            if (ws) {
              ws.send(
                JSON.stringify({
                  type: 'create_conversation',
                  agent_id: first.id,
                } as WSClientMessage)
              );
            }
          }
          break;

        case 'agent_created':
          addAgent(data.agent);
          break;

        case 'agent_updated':
          updateAgent(data.agent);
          break;

        case 'agent_deleted':
          removeAgent(data.agent_id);
          break;

        // Conversations
        case 'conversation_list':
          setConversations(data.conversations);
          break;

        case 'conversation_created':
          addConversation(data.conversation);
          setActiveConversationId(data.conversation.id);
          setActiveGroupId(null);
          setMessages([]);
          break;

        case 'conversation_deleted':
          removeConversation(data.conversation_id);
          break;

        // Messages
        case 'message_list':
          setMessages(data.messages);
          break;

        case 'new_message':
          addMessage(data.message);
          if (data.message.role === 'assistant' && data.message.status === 'sending') {
            setIsAiResponding(true);
          }
          break;

        case 'message_update':
          updateMessageContent(data.message_id, data.content);
          break;

        case 'message_final':
          finalizeMessage(data.message);
          setIsAiResponding(false);
          break;

        // Tool results
        case 'tool_executing':
          setToolExecuting({ toolName: data.tool_name, arguments: JSON.stringify(data.arguments) });
          break;

        case 'tool_result':
          setToolExecuting(null);
          break;

        // Plans
        case 'plan_list':
          break;

        case 'plan_created':
          break;

        case 'plan_updated':
          break;

        // Group messages
        case 'group_list':
          if (data.groups) setGroups(data.groups);
          break;

        case 'group_created':
          if (data.group) {
            addGroup(data.group);
            setActiveGroupId(data.group.id);
            setActiveConversationId(null);
            setMessages([]);
          }
          break;

        case 'group_message':
          if (data.message && activeGroupId && data.message.group_id === activeGroupId) {
            const isUser = data.message.sender_name === '你';
            const prefix = data.message.sender_name ? `**${data.message.sender_name}**: ` : '';
            addMessage({
              id: `gm-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
              conversation_id: '',
              role: isUser ? 'user' : 'assistant',
              type: 'text',
              content: prefix + data.message.content,
              attachments: [],
              tool_calls: [],
              tool_results: [],
              reply_to: '',
              is_edited: false,
              edited_from: '',
              is_pinned: false,
              is_remembered: false,
              status: 'sent',
              created_at: data.message.timestamp || new Date().toISOString(),
              updated_at: data.message.timestamp || new Date().toISOString(),
            });
          }
          break;

        // Memory
        case 'memory_result':
          break;

        // History
        case 'history_list':
          setHistoryRecords(data.records);
          break;

        // Message operations
        case 'message_edited':
          finalizeMessage(data.message);
          break;

        case 'message_recalled':
          finalizeMessage(data.message);
          break;

        case 'error':
          console.error('Server error:', data.message);
          useStore.getState().setLastError(data.message);
          break;
      }
    },
    [
      setAgents, addAgent, updateAgent, removeAgent,
      addConversation, removeConversation, setConversations,
      setMessages, addMessage, updateMessageContent,
      finalizeMessage, setHistoryRecords, setActiveAgentId,
      setActiveConversationId, setActiveGroupId, setIsAiResponding, setToolExecuting,
      activeGroupId, activeConversationId, addGroup, setGroups,
    ]
  );

  // Keep ref in sync so the WebSocket onmessage callback always calls the latest handler
  handleMsgRef.current = handleServerMessage;

  const sendJson = useCallback((msg: WSClientMessage) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  useEffect(() => {
    if (activeConversationId) {
      sendJson({ type: 'get_messages', conversation_id: activeConversationId });
    }
  }, [activeConversationId, sendJson]);

  return { sendJson };
}
