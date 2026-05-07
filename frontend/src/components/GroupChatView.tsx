import { useT } from '@/i18n';
import { useState, useRef, useEffect } from 'react';
import { MessageCircle, Users, Send, Plus, Hash } from 'lucide-react';

interface GroupParticipant {
  agent_id: string;
  name: string;
  role: 'moderator' | 'participant' | 'observer';
}

interface GroupMessage {
  id: string;
  agent_id: string;
  agent_name: string;
  content: string;
  created_at: string;
  round_number?: number;
}

interface GroupSession {
  id: string;
  title: string;
  topic?: string;
  mode: 'discussion' | 'task';
  status: 'active' | 'archived';
  participants: GroupParticipant[];
  messages: GroupMessage[];
  current_round?: number;
}

interface Props {
  sessions: GroupSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onCreateSession: () => void;
  onSendMessage: (sessionId: string, content: string) => void;
  onToggleMode?: (sessionId: string) => void;
}

function ParticipantBadge({ participant }: { participant: GroupParticipant }) {
  const { t } = useT();
  const roleLabel = t(`group.role.${participant.role}`);

  return (
    <div className="flex items-center gap-1.5 px-2 py-1 bg-gray-50 rounded-full text-xs">
      <span className="w-4 h-4 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center text-white text-[9px] font-medium">
        {participant.name.charAt(0)}
      </span>
      <span className="text-gray-700 truncate max-w-[80px]">{participant.name}</span>
      <span className={`px-1 rounded text-[10px] font-medium ${
        participant.role === 'moderator'
          ? 'bg-purple-100 text-purple-700'
          : participant.role === 'observer'
            ? 'bg-gray-200 text-gray-500'
            : 'bg-blue-100 text-blue-700'
      }`}>
        {roleLabel}
      </span>
    </div>
  );
}

function MessageBubbleGroup({ message }: { message: GroupMessage }) {
  return (
    <div className="flex gap-2 mb-3">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center text-white text-[10px] font-medium flex-shrink-0 mt-0.5">
        {message.agent_name.charAt(0)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs font-medium text-gray-700">{message.agent_name}</span>
          {message.round_number && (
            <span className="text-[10px] text-gray-400 bg-gray-100 px-1.5 rounded">
              #{message.round_number}
            </span>
          )}
          <span className="text-[10px] text-gray-400 ml-auto">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
        <div className="text-sm text-gray-800 bg-white border border-gray-100 rounded-lg rounded-tl-none px-3 py-2 shadow-sm">
          <span className="whitespace-pre-wrap">{message.content}</span>
        </div>
      </div>
    </div>
  );
}

function SessionSidebar({
  sessions,
  activeSessionId,
  onSelect,
  onCreate,
  t,
}: {
  sessions: GroupSession[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  t: (k: string, p?: Record<string, string | number>) => string;
}) {
  return (
    <div className="w-60 flex-shrink-0 flex flex-col border-r border-gray-200 bg-gray-50/50">
      <div className="h-14 flex items-center justify-between px-4 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-800">{t('group.title')}</h2>
        <button
          onClick={onCreate}
          className="w-7 h-7 rounded-lg bg-blue-500 hover:bg-blue-600 text-white flex items-center justify-center transition-colors"
          title={t('group.create')}
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="px-4 py-8 text-center text-xs text-gray-400">{t('group.empty')}</div>
        ) : (
          <div className="py-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => onSelect(session.id)}
                className={`w-full text-left px-4 py-2.5 transition-colors ${
                  activeSessionId === session.id
                    ? 'bg-blue-50 border-r-2 border-blue-500'
                    : 'hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Hash className={`w-4 h-4 ${activeSessionId === session.id ? 'text-blue-500' : 'text-gray-400'}`} />
                  <span className={`text-sm font-medium truncate ${
                    activeSessionId === session.id ? 'text-blue-700' : 'text-gray-700'
                  }`}>
                    {session.title}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                    session.mode === 'discussion'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-orange-100 text-orange-700'
                  }`}>
                    {t(`group.mode.${session.mode}`)}
                  </span>
                  <span className="text-[10px] text-gray-400">
                    {session.participants.length} {t('group.participants')}
                  </span>
                  {session.current_round && (
                    <span className="text-[10px] text-gray-400">
                      {t('group.round', { n: session.current_round })}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ChatArea({
  session,
  onSendMessage,
  onToggleMode,
  t,
}: {
  session: GroupSession;
  onSendMessage: (sessionId: string, content: string) => void;
  onToggleMode?: (sessionId: string) => void;
  t: (k: string, p?: Record<string, string | number>) => string;
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session.messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    onSendMessage(session.id, text);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <div className="h-14 flex items-center gap-3 px-4 border-b border-gray-200 bg-white">
        <Hash className="w-5 h-5 text-gray-400" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-gray-800 truncate">{session.title}</h2>
            {onToggleMode && (
              <button
                onClick={() => onToggleMode(session.id)}
                className={`text-[10px] px-2 py-0.5 rounded font-medium transition-colors ${
                  session.mode === 'discussion'
                    ? 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                    : 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                }`}
              >
                {t(`group.mode.${session.mode}`)}
              </button>
            )}
          </div>
          {session.topic && (
            <div className="text-xs text-gray-400 truncate">{session.topic}</div>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 bg-gray-50/30">
        {session.messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <MessageCircle className="w-10 h-10 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-400">{t('group.topic')}: {session.topic || '—'}</p>
            </div>
          </div>
        ) : (
          session.messages.map((msg) => (
            <MessageBubbleGroup key={msg.id} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Participants bar */}
      {session.participants.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-100 bg-white">
          <div className="flex items-center gap-2 overflow-x-auto">
            <Users className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
            {session.participants.map((p) => (
              <ParticipantBadge key={p.agent_id} participant={p} />
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="px-4 py-3 border-t border-gray-200 bg-white">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('group.input_placeholder')}
            rows={1}
            className="flex-1 resize-none px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="px-3 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white rounded-lg transition-colors flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function GroupChatView({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onSendMessage,
  onToggleMode,
}: Props) {
  const { t } = useT();
  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;

  return (
    <div className="flex h-full bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Session list sidebar */}
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={onSelectSession}
        onCreate={onCreateSession}
        t={t}
      />

      {/* Chat area */}
      {activeSession ? (
        <ChatArea
          session={activeSession}
          onSendMessage={onSendMessage}
          onToggleMode={onToggleMode}
          t={t}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center bg-gray-50/30">
          <div className="text-center">
            <MessageCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-400">{t('group.empty')}</p>
          </div>
        </div>
      )}
    </div>
  );
}
