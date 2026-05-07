import type { Message } from '@/types';
import dayjs from 'dayjs';
import ReactMarkdown from 'react-markdown';

interface Props {
  message: Message;
}

function TypingDots() {
  return (
    <span className="inline-flex gap-1">
      <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </span>
  );
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isStreaming = message.status === 'sending' && !isUser;
  const isRecalled = message.status === 'cancelled';

  if (isSystem) {
    return (
      <div className="flex justify-center my-3">
        <span className="text-xs text-gray-400 italic bg-gray-50 px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 mb-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-medium flex-shrink-0 ${
          isUser ? 'bg-blue-500' : 'bg-green-500'
        }`}
      >
        {isUser ? '我' : 'AI'}
      </div>

      {/* Bubble */}
      <div className="flex flex-col max-w-[70%]">
        <div
          className={`px-4 py-2.5 text-sm leading-relaxed break-words rounded-2xl ${
            isUser
              ? 'bg-green-500 text-white rounded-tr-md'
              : 'bg-white border border-gray-200 text-gray-800 rounded-tl-md shadow-sm'
          }`}
        >
          {isRecalled ? (
            <span className="italic text-gray-400 text-xs">[消息已撤回]</span>
          ) : isStreaming && !message.content ? (
            <TypingDots />
          ) : isUser ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            <div className="markdown-content">
              <ReactMarkdown
                components={{
                  pre: ({ children }) => (
                    <div className="relative group my-2">
                      <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-xs leading-relaxed">
                        {children}
                      </pre>
                    </div>
                  ),
                  code: ({ className, children, ...props }) => {
                    const isInline = !className;
                    if (isInline) {
                      return (
                        <code className="bg-gray-100 text-pink-600 px-1 py-0.5 rounded text-xs" {...props}>
                          {children}
                        </code>
                      );
                    }
                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                  a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      {children}
                    </a>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp + Status */}
        <div className={`flex items-center gap-2 mt-1 ${isUser ? 'justify-end' : 'justify-start'}`}>
          <span className="text-[11px] text-gray-400">
            {message.created_at ? dayjs(message.created_at).format('HH:mm') : ''}
          </span>
          {message.is_edited && (
            <span className="text-[11px] text-gray-400">[已编辑]</span>
          )}
          {isRecalled && (
            <span className="text-[11px] text-gray-400">已撤回</span>
          )}
          {isStreaming && (
            <span className="text-[11px] text-green-500 font-medium">正在生成...</span>
          )}
          {message.status === 'failed' && (
            <span className="text-[11px] text-red-500">发送失败</span>
          )}
        </div>
      </div>
    </div>
  );
}
