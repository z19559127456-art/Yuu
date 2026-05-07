import { useState, useRef, useCallback, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { AtSign } from 'lucide-react';
import type { WSClientMessage, Agent } from '@/types';

interface Props {
  sendJson: (msg: WSClientMessage) => void;
}

export default function ChatInput({ sendJson }: Props) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const activeConversationId = useStore((s) => s.activeConversationId);
  const activeGroupId = useStore((s) => s.activeGroupId);
  const wsConnected = useStore((s) => s.wsConnected);
  const agents = useStore((s) => s.agents);
  const groups = useStore((s) => s.groups);

  const toolExecuting = useStore((s) => s.toolExecuting);
  const isAiResponding = useStore((s) => s.isAiResponding);
  const lastError = useStore((s) => s.lastError);
  const setLastError = useStore((s) => s.setLastError);

  // @mention state
  const [showMentions, setShowMentions] = useState(false);
  const [mentionFilter, setMentionFilter] = useState('');
  const [mentionStart, setMentionStart] = useState(-1);

  const group = groups.find((g) => g.id === activeGroupId);
  const groupAgents: Agent[] = group?.participants
    ? agents.filter((a) => group.participants!.some((p) => p.agent_id === a.id))
    : [];

  const filteredAgents = groupAgents.filter((a) =>
    mentionFilter ? a.name.toLowerCase().includes(mentionFilter.toLowerCase()) : true
  );

  const canSend = text.trim().length > 0 && (activeConversationId || activeGroupId) && wsConnected;

  // Detect @ typing
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setText(val);

    // Check for @ trigger
    const cursorPos = e.target.selectionStart || 0;
    const textBeforeCursor = val.slice(0, cursorPos);
    const atMatch = textBeforeCursor.match(/@([^\s@]*)$/);

    if (atMatch && activeGroupId) {
      setMentionStart(cursorPos - atMatch[0].length);
      setMentionFilter(atMatch[1]);
      setShowMentions(true);
    } else {
      setShowMentions(false);
      setMentionStart(-1);
      setMentionFilter('');
    }

    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  const insertMention = (agentName: string) => {
    if (mentionStart >= 0) {
      const before = text.slice(0, mentionStart);
      const after = text.slice(textareaRef.current?.selectionStart || 0);
      setText(before + `@${agentName} ` + after);
    } else {
      setText(text + `@${agentName} `);
    }
    setShowMentions(false);
    setMentionStart(-1);
    textareaRef.current?.focus();
  };

  const toggleMention = () => {
    if (activeGroupId && groupAgents.length > 0) {
      setShowMentions(!showMentions);
      setMentionFilter('');
      setMentionStart(-1);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showMentions) {
      if (e.key === 'Escape') {
        setShowMentions(false);
        e.preventDefault();
        return;
      }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        return; // Keep focus on textarea, handled via tabIndex on mentions
      }
    }
    if (e.key === 'Enter' && !e.shiftKey && !showMentions) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = useCallback(() => {
    if (!canSend) return;
    if (activeConversationId) {
      sendJson({
        type: 'send_message',
        conversation_id: activeConversationId,
        content: text.trim(),
      });
    } else if (activeGroupId) {
      sendJson({
        type: 'group_send',
        group_id: activeGroupId,
        content: text.trim(),
      });
    }
    setText('');
    setShowMentions(false);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [canSend, activeConversationId, activeGroupId, text, sendJson]);

  // Close mentions on outside click
  useEffect(() => {
    if (!showMentions) return;
    const handler = () => setShowMentions(false);
    document.addEventListener('click', handler, { once: true });
    return () => document.removeEventListener('click', handler);
  }, [showMentions]);

  return (
    <div className="border-t border-gray-200 bg-white px-6 py-3 flex-shrink-0">
      {/* Status bar */}
      <div className="mb-2 flex items-center gap-2 min-h-[24px]">
        {/* AI responding indicator */}
        {isAiResponding && !toolExecuting && (
          <div className="flex items-center gap-1.5 text-sm text-blue-600">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
            </span>
            <span>AI 正在回复...</span>
          </div>
        )}

        {/* Tool executing indicator */}
        {toolExecuting && (
          <div className="flex items-center gap-1.5 text-sm text-amber-600">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span>
              正在执行: <code className="bg-amber-50 px-1 rounded text-xs">{toolExecuting.toolName}</code>
              {toolExecuting.arguments && (
                <span className="text-amber-500 ml-1">{toolExecuting.arguments}</span>
              )}
            </span>
          </div>
        )}

        {/* Connection status */}
        {!wsConnected && (
          <div className="flex items-center gap-1.5 text-sm text-red-500">
            <span className="inline-block w-2 h-2 rounded-full bg-red-400" />
            <span>未连接到服务器</span>
          </div>
        )}
      </div>

      {/* Error banner */}
      {lastError && (
        <div className="mb-2 flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="flex-1">{lastError}</span>
          <button
            onClick={() => setLastError(null)}
            className="flex-shrink-0 text-red-400 hover:text-red-600 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="relative">
        {/* @mention dropdown */}
        {showMentions && filteredAgents.length > 0 && (
          <div className="absolute bottom-full left-0 mb-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden z-10">
            {filteredAgents.map((agent) => (
              <button
                key={agent.id}
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  insertMention(agent.name);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-blue-50 transition-colors"
              >
                <span className="w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-xs font-medium flex-shrink-0">
                  {agent.name.charAt(0)}
                </span>
                <span className="text-gray-700 truncate">{agent.name}</span>
              </button>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2">
          {/* @ button (group mode only) */}
          {activeGroupId && (
            <button
              type="button"
              onClick={toggleMention}
              className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-colors
                ${showMentions ? 'bg-blue-100 text-blue-500' : 'hover:bg-gray-100 text-gray-400'}`}
              title="@提及 Agent"
            >
              <AtSign className="w-5 h-5" />
            </button>
          )}

          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={activeGroupId ? '输入消息，输入 @ 提及 Agent...' : '输入消息...'}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-300 bg-gray-50 px-4 py-2.5 text-sm text-gray-800 placeholder-gray-400 outline-none focus:border-gray-400 focus:bg-white transition-colors"
            style={{ maxHeight: '160px' }}
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all
              ${
                canSend
                  ? 'bg-green-500 text-white hover:bg-green-600 active:scale-95'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19V5m0 0l-7 7m7-7l7 7"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
