import { Users } from 'lucide-react';
import { useStore } from '@/store/useStore';

export default function ChatHeader() {
  const activeConversationId = useStore((s) => s.activeConversationId);
  const activeGroupId = useStore((s) => s.activeGroupId);
  const conversations = useStore((s) => s.conversations);
  const groups = useStore((s) => s.groups);
  const agents = useStore((s) => s.agents);
  const wsConnected = useStore((s) => s.wsConnected);

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
    : group
      ? `${group.participants?.length || 0} 人 · ${group.mode === 'discussion' ? '讨论模式' : '任务模式'}`
      : null;
  const isGroup = !!group && !activeConversationId;
  const avatarChar = isGroup ? null : (agent ? agent.name.charAt(0) : conversation ? conversation.title.charAt(0) : '?');

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
        </div>
      </div>

      <div className="flex items-center gap-2">
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
