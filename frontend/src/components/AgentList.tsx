import { useState } from 'react';
import { useStore } from '@/store/useStore';
import { Plus, MessageSquare, Trash2, Users } from 'lucide-react';
import dayjs from 'dayjs';
import type { WSClientMessage } from '@/types';
import CreateConversationDialog from './CreateConversationDialog';

export default function AgentList() {
  const conversations = useStore((s) => s.conversations);
  const groups = useStore((s) => s.groups);
  const activeConversationId = useStore((s) => s.activeConversationId);
  const activeGroupId = useStore((s) => s.activeGroupId);
  const setActiveConversationId = useStore((s) => s.setActiveConversationId);
  const setActiveGroupId = useStore((s) => s.setActiveGroupId);
  const activeAgentId = useStore((s) => s.activeAgentId);
  const agents = useStore((s) => s.agents);
  const ws = useStore((s) => s.ws);

  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const activeAgent = agents.find((a) => a.id === activeAgentId);

  const handleDelete = (convId: string) => {
    if (ws) {
      ws.send(JSON.stringify({
        type: 'delete_conversation',
        conversation_id: convId,
      } as WSClientMessage));
      if (activeConversationId === convId) {
        setActiveConversationId(null);
      }
    }
    setConfirmDelete(null);
  };

  return (
    <div className="w-72 flex-shrink-0 flex flex-col bg-white border-r border-gray-200">
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-semibold text-gray-800">消息</h1>
          {activeAgent && (
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
              {activeAgent.name}
            </span>
          )}
        </div>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-green-500 transition-colors"
          title="新建对话"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>

      {/* Search */}
      <div className="px-3 py-2">
        <div className="relative">
          <input
            type="text"
            placeholder="搜索"
            className="w-full h-9 pl-8 pr-3 rounded-lg bg-gray-100 text-sm text-gray-600 placeholder-gray-400 outline-none focus:bg-gray-50 focus:ring-1 focus:ring-gray-300 transition-all"
          />
          <svg
            className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {!activeAgent ? (
          <div className="flex items-center justify-center h-32 text-sm text-gray-400">
            请选择一个 Agent
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-sm text-gray-400 gap-3">
            <MessageSquare className="w-8 h-8 text-gray-300" />
            <span>暂无对话</span>
            <button
              onClick={() => setShowCreateDialog(true)}
              className="px-4 py-1.5 rounded-lg bg-green-500 text-white text-xs hover:bg-green-600 transition-colors"
            >
              新建对话
            </button>
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className="group flex items-start gap-3 px-5 py-3 cursor-pointer transition-colors relative"
            >
              <button
                onClick={() => {
                  setActiveConversationId(conv.id);
                  setActiveGroupId(null);
                  setConfirmDelete(null);
                }}
                className={`flex-1 flex items-start gap-3 text-left ${
                  activeConversationId === conv.id
                    ? 'bg-blue-50 -mx-5 px-5 py-3 -my-3'
                    : ''
                }`}
              >
                {/* Avatar */}
                <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center text-white font-medium text-sm flex-shrink-0">
                  {conv.title.charAt(0)}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-800 truncate">
                      {conv.title}
                    </span>
                    <span className="text-xs text-gray-400 flex-shrink-0 ml-2">
                      {conv.updated_at ? dayjs(conv.updated_at).format('HH:mm') : ''}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 truncate mt-0.5">
                    点击开始对话
                  </p>
                </div>
              </button>

              {/* Hover delete */}
              <div className="hidden group-hover:flex absolute right-2 top-1/2 -translate-y-1/2">
                {confirmDelete === conv.id ? (
                  <button
                    onClick={() => handleDelete(conv.id)}
                    className="w-7 h-7 flex items-center justify-center rounded bg-red-100 text-red-500"
                    title="确认删除"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                ) : (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmDelete(conv.id);
                    }}
                    className="w-7 h-7 flex items-center justify-center rounded hover:bg-gray-200 text-gray-400"
                    title="删除对话"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          ))
        )}

        {/* Group chats */}
        {groups.length > 0 && (
          <>
            <div className="px-5 py-2 text-xs font-medium text-gray-400 uppercase tracking-wide border-t border-gray-100">
              群聊
            </div>
            {groups.map((group) => (
              <button
                key={group.id}
                onClick={() => {
                  setActiveGroupId(group.id);
                  setActiveConversationId(null);
                  setConfirmDelete(null);
                }}
                className={`w-full flex items-start gap-3 px-5 py-3 text-left transition-colors
                  ${
                    activeGroupId === group.id
                      ? 'bg-blue-50'
                      : 'hover:bg-gray-50'
                  }`}
              >
                <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white flex-shrink-0">
                  <Users className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-800 truncate">
                      {group.title}
                    </span>
                    <span className="text-xs text-gray-400 flex-shrink-0 ml-2">
                      {group.updated_at ? dayjs(group.updated_at).format('HH:mm') : ''}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 truncate mt-0.5">
                    {group.participants?.length ? `${group.participants.length} 人 · ` : ''}{group.mode === 'discussion' ? '讨论模式' : '任务模式'}
                  </p>
                </div>
              </button>
            ))}
          </>
        )}
      </div>

      <CreateConversationDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
      />
    </div>
  );
}
