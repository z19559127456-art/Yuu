import { useT } from '@/i18n';
import { CheckCircle, XCircle, Loader2, Clock, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

interface ToolCallDisplay {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

interface ToolResultDisplay {
  tool_call_id: string;
  result: unknown;
  status: 'success' | 'error';
}

interface Props {
  toolCalls?: ToolCallDisplay[];
  toolResults?: ToolResultDisplay[];
  isStreaming?: boolean;
}

function ToolCallCard({ call, result, t }: { call: ToolCallDisplay; result?: ToolResultDisplay; t: (k: string, p?: Record<string, string | number>) => string }) {
  const [expanded, setExpanded] = useState(false);

  const statusIcon = !result ? (
    <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
  ) : result.status === 'success' ? (
    <CheckCircle className="w-4 h-4 text-green-500" />
  ) : (
    <XCircle className="w-4 h-4 text-red-500" />
  );

  const statusText = !result
    ? t('tool.status.running')
    : result.status === 'success'
      ? t('tool.status.success')
      : t('tool.status.error');

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        {expanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
        <span className="text-xs font-medium text-gray-700">{call.name}</span>
        <span className="ml-auto flex items-center gap-1.5 text-xs">
          {statusIcon}
          <span className={
            !result ? 'text-blue-600' : result.status === 'success' ? 'text-green-600' : 'text-red-600'
          }>{statusText}</span>
        </span>
      </button>

      {expanded && (
        <div className="px-3 py-2 border-t border-gray-200 space-y-2">
          <div>
            <span className="text-xs font-medium text-gray-500">{t('tool.args')}</span>
            <pre className="mt-1 bg-gray-900 text-gray-100 rounded p-2 text-xs overflow-x-auto">
              {JSON.stringify(call.arguments, null, 2)}
            </pre>
          </div>
          {result && (
            <div>
              <span className="text-xs font-medium text-gray-500">{t('tool.result')}</span>
              <pre className={`mt-1 rounded p-2 text-xs overflow-x-auto ${
                result.status === 'success' ? 'bg-gray-900 text-gray-100' : 'bg-red-50 text-red-700'
              }`}>
                {typeof result.result === 'string' ? result.result : JSON.stringify(result.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ToolOutput({ toolCalls, toolResults, isStreaming }: Props) {
  const { t } = useT();

  if ((!toolCalls || toolCalls.length === 0) && (!toolResults || toolResults.length === 0)) {
    return null;
  }

  const resultsMap = new Map<string, ToolResultDisplay>();
  toolResults?.forEach((r) => resultsMap.set(r.tool_call_id, r));

  return (
    <div className="space-y-2 my-2">
      <div className="flex items-center gap-2">
        <Clock className="w-4 h-4 text-gray-400" />
        <span className="text-xs font-medium text-gray-500">{t('tool.title')}</span>
        {isStreaming && <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />}
      </div>
      {toolCalls?.map((call) => (
        <ToolCallCard
          key={call.id}
          call={call}
          result={resultsMap.get(call.id)}
          t={t}
        />
      ))}
    </div>
  );
}
