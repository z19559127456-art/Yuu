import { useState } from 'react';
import { useStore } from '@/store/useStore';
import { X, Users, UserPlus } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function CreateConversationDialog({ open, onClose }: Props) {
  const agents = useStore((s) => s.agents);
  const ws = useStore((s) => s.ws);
  const setActiveAgentId = useStore((s) => s.setActiveAgentId);

  const [name, setName] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  if (!open) return null;

  const isGroup = selectedIds.size >= 2;

  const toggleAgent = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const handleSubmit = () => {
    if (!ws || selectedIds.size === 0) return;

    const ids = Array.from(selectedIds);
    const title = name.trim() || `新${isGroup ? '群聊' : '对话'}`;

    if (isGroup) {
      ws.send(JSON.stringify({
        type: 'create_group',
        title,
        topic: '',
        mode: 'discussion',
        participant_ids: ids,
      }));
    } else {
      const agentId = ids[0];
      ws.send(JSON.stringify({
        type: 'create_conversation',
        agent_id: agentId,
      }));
      setActiveAgentId(agentId);
    }

    // Reset
    setName('');
    setSelectedIds(new Set());
    onClose();
  };

  const handleClose = () => {
    setName('');
    setSelectedIds(new Set());
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-[440px] max-h-[70vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            {isGroup ? (
              <Users className="w-5 h-5 text-blue-500" />
            ) : (
              <UserPlus className="w-5 h-5 text-green-500" />
            )}
            <h2 className="text-lg font-semibold text-gray-800">
              {isGroup ? '创建群聊' : '新建对话'}
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              对话名称
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={isGroup ? '输入群聊名称...' : '输入对话名称（可选）'}
              className="w-full h-10 px-3 rounded-lg border border-gray-300 text-sm outline-none focus:border-blue-500"
              autoFocus
            />
          </div>

          {/* Agent list */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              选择 Agent
              <span className="text-gray-400 font-normal ml-1">
                {isGroup ? '(已选 {0} 个 — 群聊)'.replace('{0}', String(selectedIds.size)) : '(单选 = 私聊，多选 = 群聊)'}
              </span>
            </label>
            <div className="space-y-1 max-h-64 overflow-y-auto border border-gray-200 rounded-lg p-2">
              {agents.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">
                  暂无 Agent，请先创建
                </p>
              ) : (
                agents.filter(a => a.is_active).map((agent) => {
                  const checked = selectedIds.has(agent.id);
                  return (
                    <label
                      key={agent.id}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors
                        ${checked ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50 border border-transparent'}`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleAgent(agent.id)}
                        className="w-4 h-4 rounded border-gray-300 text-blue-500 focus:ring-blue-400"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">
                          {agent.name}
                        </p>
                        <p className="text-xs text-gray-400 truncate">
                          {agent.model_provider} / {agent.model_name}
                        </p>
                      </div>
                    </label>
                  );
                })
              )}
            </div>
          </div>

          {/* Hint */}
          <p className="text-xs text-gray-400">
            选中 1 个 Agent = 私聊对话；选中 2 个及以上 = 群聊讨论
          </p>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
          <button
            onClick={handleClose}
            className="px-5 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={selectedIds.size === 0}
            className={`px-5 py-2 rounded-lg text-sm text-white transition-colors
              ${selectedIds.size === 0
                ? 'bg-gray-300 cursor-not-allowed'
                : isGroup
                  ? 'bg-blue-500 hover:bg-blue-600'
                  : 'bg-green-500 hover:bg-green-600'
              }`}
          >
            {isGroup ? '创建群聊' : '开始对话'}
          </button>
        </div>
      </div>
    </div>
  );
}
