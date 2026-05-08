import { useStore } from '@/store/useStore';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import PlanView from './PlanView';
import TaskProgress from './TaskProgress';
import type { WSClientMessage } from '@/types';

interface Props {
  sendJson: (msg: WSClientMessage) => void;
}

export default function ChatArea({ sendJson }: Props) {
  const activeConversationId = useStore((s) => s.activeConversationId);
  const activeGroupId = useStore((s) => s.activeGroupId);
  const currentPlan = useStore((s) => s.currentPlan);
  const groups = useStore((s) => s.groups);

  const group = groups.find((g) => g.id === activeGroupId);
  const isTaskMode = group?.mode === 'task';

  if (!activeConversationId && !activeGroupId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-200 flex items-center justify-center">
            <svg
              className="w-10 h-10 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
          </div>
          <p className="text-base text-gray-400">选择一个对话开始聊天</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-white">
      <ChatHeader sendJson={sendJson} />
      {isTaskMode && currentPlan && (
        <div className="border-b border-gray-200 bg-gray-50/50 px-4 py-2">
          <PlanView plan={currentPlan} />
        </div>
      )}
      {isTaskMode && currentPlan && (
        <TaskProgress tasks={currentPlan.subtasks.map((st) => ({ id: st.id, title: st.title, status: st.status }))} />
      )}
      <MessageList />
      <ChatInput sendJson={sendJson} />
    </div>
  );
}
