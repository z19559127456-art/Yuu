import { useState, useEffect } from 'react';
import { Users, ChevronDown, Play, Square } from 'lucide-react';
import { useStore } from '@/store/useStore';
import type { GroupMode, WSClientMessage } from '@/types';

interface Props {
  sendJson?: (msg: WSClientMessage) => void;
}

const MODE_LABELS: Record<GroupMode, string> = {
  discussion: '讨论模式',
  task: '任务模式',
  free_dialogue: '自由对话',
};

export default function ChatHeader({ sendJson }: Props) {
  const activeConversationId = useStore((s) => s.activeConversationId);
  const activeGroupId = useStore((s) => s.activeGroupId);
  const conversations = useStore((s) => s.conversations);
  const groups = useStore((s) => s.groups);
  const agents = useStore((s) => s.agents);
  const wsConnected = useStore((s) => s.wsConnected);
  const freeDialogueActive = useStore((s) => s.freeDialogueActive);
  const setFreeDialogueActive = useStore((s) => s.setFreeDialogueActive);

  const [showModeMenu, setShowModeMenu] = useState(false);

  const isDialogueRunning = activeGroupId ? freeDialogueActive[activeGroupId] || false : false;

  const conversation = conversations.find((c) => c.id === activeConversationId);
  const group = groups.find((g) => g.id === activeGroupId);
  const agent = conversation
    ? agents.find((a) => a.id === conversation.agent_id)
    : null;

  const title = (activeConversationId && (agent?.name || conversation?.title))
    || group?.title
    || '请选择对话';
  const subtitle = activeConversationId && agent
    ? `${agent.model_provider} · ${agent.model_name}`
    : null;
  const isGroup = !!group && !activeConversationId;
  const avatarChar = isGroup ? null : (agent ? agent.name.charAt(0) : conversation ? conversation.title.charAt(0) : '?');

  const handleSwitchMode = (mode: GroupMode) => {
    if (!sendJson || !activeGroupId) return;
    sendJson({ type: 'switch_group_mode', group_id: activeGroupId, mode });
    setShowModeMenu(false);
  };

  const handleStartDialogue = () => {
    if (!sendJson || !activeGroupId) return;
    sendJson({ type: 'start_free_dialogue', group_id: activeGroupId, topic: group?.topic || '' });
    setFreeDialogueActive(activeGroupId, true);
  };

  const handleStopDialogue = () => {
    if (!sendJson || !activeGroupId) return;
    sendJson({ type: 'stop_free_dialogue', group_id: activeGroupId });
    setFreeDialogueActive(activeGroupId, false);
  };

  // Close mode menu on outside click
  useEffect(() => {
    if (!showModeMenu) return;
    const handler = () => setShowModeMenu(false);
    document.addEventListener('click', handler, { once: true });
    return () => document.removeEventListener('click', handler);
  }, [showModeMenu]);

  return (
    <div className="h-16 flex items-center justify-between px-6 border-b border-gray-200 bg-white flex-shrink-0">
      <div className="flex items-center gap-3">
        <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white font-medium text-sm
          ${isGroup ? 'bg-blue-500' : 'bg-green-500'}`}
        >
          {isGroup ? <Users className="w-4.5 h-4.5" /> : avatarChar}
        </div>
        <div className="flex flex-col">
          <span className="text-base font-medium text-gray-800 leading-tight">
            {title}
          </span>
          {subtitle && (
            <span className="text-[11px] text-gray-400">
              {subtitle}
            </span>
          )}
          {isGroup && group && (
            <div className="relative">
              <button
                onClick={() => setShowModeMenu(!showModeMenu)}
                className="flex items-center gap-0.5 text-[11px] text-blue-500 hover:text-blue-600 transition-colors"
              >
                {MODE_LABELS[group.mode] || group.mode}
                <ChevronDown className="w-3 h-3" />
              </button>
              {showModeMenu && (
                <div className="absolute top-full left-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 z-20 py-1 min-w-[100px]">
                  {(Object.keys(MODE_LABELS) as GroupMode[]).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => handleSwitchMode(mode)}
                      className={`w-full text-left px-3 py-1.5 text-xs hover:bg-blue-50 transition-colors ${
                        group.mode === mode ? 'text-blue-600 font-medium' : 'text-gray-600'
                      }`}
                    >
                      {MODE_LABELS[mode]}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Free Dialogue Start/Stop Button */}
        {isGroup && group?.mode === 'free_dialogue' && (
          isDialogueRunning ? (
            <button
              onClick={handleStopDialogue}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 transition-colors"
            >
              <Square className="w-3 h-3" />
              停止对话
            </button>
          ) : (
            <button
              onClick={handleStartDialogue}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-green-50 text-green-600 border border-green-200 hover:bg-green-100 transition-colors"
            >
              <Play className="w-3 h-3" />
              开始对话
            </button>
          )
        )}
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            wsConnected ? 'bg-green-500' : 'bg-red-400'
          }`}
        />
        <span className="text-xs text-gray-400">
          {wsConnected ? '已连接' : '未连接'}
        </span>
      </div>
    </div>
  );
}
