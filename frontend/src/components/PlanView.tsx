import { useT } from '@/i18n';
import { useState } from 'react';

interface SubTaskData {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  depends_on?: string[];
  order_index?: number;
  assigned_agent_id?: string;
}

interface PlanData {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  subtasks: SubTaskData[];
  created_at?: string;
  updated_at?: string;
}

interface Props {
  plan: PlanData;
}

const statusStyles: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600',
  running: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-yellow-100 text-yellow-700',
  skipped: 'bg-gray-100 text-gray-400',
};

const statusIcons: Record<string, string> = {
  pending: '○',
  running: '◌',
  completed: '●',
  failed: '✕',
  cancelled: '—',
  skipped: '·',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${statusStyles[status] || statusStyles.pending}`}>
      <span>{statusIcons[status] || '?'}</span>
      <span>{status}</span>
    </span>
  );
}

function SubTaskNode({ subtask, depth }: { subtask: SubTaskData; depth: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="select-none">
      <div
        className={`flex items-center gap-2 py-1.5 px-2 rounded hover:bg-gray-50 cursor-pointer transition-colors`}
        style={{ paddingLeft: `${12 + depth * 20}px` }}
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-xs text-gray-400 font-mono w-5 flex-shrink-0">
          {subtask.order_index !== undefined ? subtask.order_index + 1 : '·'}
        </span>
        <span className="text-sm text-gray-800 flex-1 truncate">{subtask.title}</span>
        <StatusBadge status={subtask.status} />
        {subtask.depends_on && subtask.depends_on.length > 0 && (
          <span className="text-xs text-gray-400" title={`Depends on: ${subtask.depends_on.join(', ')}`}>
            ⤴
          </span>
        )}
      </div>
      {expanded && subtask.description && (
        <div
          className="text-xs text-gray-500 py-1 px-2"
          style={{ paddingLeft: `${36 + depth * 20}px` }}
        >
          {subtask.description}
        </div>
      )}
    </div>
  );
}

export default function PlanView({ plan }: Props) {
  const { t } = useT();
  const [collapsed, setCollapsed] = useState(false);

  const sortedSubtasks = [...(plan.subtasks || [])].sort(
    (a, b) => (a.order_index ?? 0) - (b.order_index ?? 0)
  );

  const completedCount = sortedSubtasks.filter((s) => s.status === 'completed').length;
  const totalCount = sortedSubtasks.length;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <span className={`text-xs text-gray-400 transition-transform ${collapsed ? '' : 'rotate-90'}`}>▶</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-800 truncate">{plan.title}</span>
            <StatusBadge status={plan.status} />
          </div>
          {totalCount > 0 && (
            <span className="text-xs text-gray-400">
              {completedCount}/{totalCount} {t('plan.subtask')}
            </span>
          )}
        </div>
      </button>

      {/* Body */}
      {!collapsed && (
        <div className="border-t border-gray-200">
          {/* Description */}
          {plan.description && (
            <div className="px-4 py-2 text-xs text-gray-500 bg-gray-50/50 border-b border-gray-100">
              {plan.description}
            </div>
          )}

          {/* Subtask list */}
          {sortedSubtasks.length === 0 ? (
            <div className="px-4 py-6 text-center text-xs text-gray-400">{t('common.empty')}</div>
          ) : (
            <div className="py-1">
              <div className="px-3 py-1 text-xs font-medium text-gray-400 uppercase tracking-wider">
                {t('plan.subtask')} ({totalCount})
              </div>
              {sortedSubtasks.map((sub) => (
                <SubTaskNode key={sub.id} subtask={sub} depth={0} />
              ))}
            </div>
          )}

          {/* Timeline */}
          {plan.created_at && (
            <div className="px-4 py-2 border-t border-gray-100 flex items-center gap-2 text-xs text-gray-400">
              <span>{t('plan.create_time')}:</span>
              <span>{new Date(plan.created_at).toLocaleString()}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
