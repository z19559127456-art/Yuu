import { useState } from 'react';
import { useStore } from '@/store/useStore';
import { Plus, Trash2, Edit3, ChevronRight } from 'lucide-react';
import type { WSClientMessage } from '@/types';

interface Props {
  sendJson: (msg: WSClientMessage) => void;
}

export default function ContactsView({ sendJson }: Props) {
  const agents = useStore((s) => s.agents);
  const setShowAgentForm = useStore((s) => s.setShowAgentForm);
  const setEditingAgent = useStore((s) => s.setEditingAgent);
  const setActiveNav = useStore((s) => s.setActiveNav);
  const setActiveAgentId = useStore((s) => s.setActiveAgentId);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  function handleCreate() {
    setEditingAgent(null);
    setShowAgentForm(true);
  }

  function handleEdit(agent: any) {
    setEditingAgent(agent);
    setShowAgentForm(true);
  }

  function handleDelete(agentId: string) {
    sendJson({ type: 'delete_agent', agent_id: agentId });
    setConfirmDelete(null);
  }

  function handleStartChat(agent: any) {
    setActiveAgentId(agent.id);
    sendJson({ type: 'create_conversation', agent_id: agent.id });
    setActiveNav('chats');
  }

  return (
    <div className="w-72 flex-shrink-0 flex flex-col bg-white border-r border-gray-200">
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-5 border-b border-gray-100">
        <h1 className="text-lg font-semibold text-gray-800">通讯录</h1>
        <button
          onClick={handleCreate}
          className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-green-500 hover:text-green-600 transition-colors"
          title="新建 Agent"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>

      {/* Agent list */}
      <div className="flex-1 overflow-y-auto">
        {agents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-sm text-gray-400 gap-3">
            <span>还没有 Agent</span>
            <button
              onClick={handleCreate}
              className="px-4 py-2 rounded-lg bg-green-500 text-white text-sm hover:bg-green-600 transition-colors"
            >
              创建第一个 Agent
            </button>
          </div>
        ) : (
          agents.map((agent) => (
            <div
              key={agent.id}
              className="group flex items-center gap-3 px-5 py-3 hover:bg-gray-50 transition-colors"
            >
              {/* Avatar */}
              <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center text-white font-medium text-sm flex-shrink-0">
                {agent.name.charAt(0)}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-800 truncate">
                    {agent.name}
                  </span>
                  <span className="text-[11px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                    {agent.model_provider}
                  </span>
                </div>
                <p className="text-xs text-gray-400 truncate mt-0.5">
                  {agent.role || agent.model_name}
                </p>
              </div>

              {/* Actions */}
              <div className="hidden group-hover:flex items-center gap-1">
                <button
                  onClick={() => handleEdit(agent)}
                  className="w-7 h-7 flex items-center justify-center rounded hover:bg-gray-200 text-gray-500"
                  title="编辑"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
                {confirmDelete === agent.id ? (
                  <button
                    onClick={() => handleDelete(agent.id)}
                    className="w-7 h-7 flex items-center justify-center rounded bg-red-100 text-red-500"
                    title="确认删除"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                ) : (
                  <button
                    onClick={() => setConfirmDelete(agent.id)}
                    className="w-7 h-7 flex items-center justify-center rounded hover:bg-gray-200 text-gray-500"
                    title="删除"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
                <button
                  onClick={() => handleStartChat(agent)}
                  className="w-7 h-7 flex items-center justify-center rounded hover:bg-gray-200 text-gray-500"
                  title="开始对话"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
