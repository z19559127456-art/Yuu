import { useT } from '@/i18n';

interface TaskItem {
  id: string;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
}

interface Props {
  tasks: TaskItem[];
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const ANIMATION_DELAY_PER_ITEM = 80;

export default function TaskProgress({ tasks, showLabel = true, size = 'md' }: Props) {
  const { t } = useT();

  const total = tasks.length;
  const completed = tasks.filter((t) => t.status === 'completed' || t.status === 'skipped').length;
  const running = tasks.filter((t) => t.status === 'running').length;
  const failed = tasks.filter((t) => t.status === 'failed').length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  const barHeight = size === 'sm' ? 'h-1.5' : size === 'lg' ? 'h-3' : 'h-2';

  return (
    <div className="space-y-2">
      {/* Header */}
      {showLabel && (
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">{t('progress.title')}</span>
          <span className="text-xs text-gray-500">{t('progress.percent', { p: percent })}</span>
        </div>
      )}

      {/* Progress Bar */}
      <div className={`w-full bg-gray-100 rounded-full overflow-hidden ${barHeight}`}>
        {failed > 0 && (
          <div
            className="h-full bg-red-400 float-left transition-all duration-700"
            style={{ width: `${(failed / total) * 100}%` }}
          />
        )}
        <div
          className={`h-full bg-green-500 transition-all duration-1000 ease-out ${failed > 0 ? 'float-left' : ''}`}
          style={{
            width: `${percent}%`,
            transitionDelay: `${Math.min(failed, total - 1) * ANIMATION_DELAY_PER_ITEM}ms`,
          }}
        />
      </div>

      {/* Stats */}
      {showLabel && (
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
            {t('progress.completed')} {completed}
          </span>
          {running > 0 && (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse inline-block" />
              {t('progress.remaining')} {running}
            </span>
          )}
          {failed > 0 && (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
              {t('common.error')} {failed}
            </span>
          )}
          <span className="ml-auto">
            {t('progress.total')} {total}
          </span>
        </div>
      )}

      {/* Per-task mini progress */}
      {tasks.length > 0 && (
        <div className="space-y-1">
          {tasks.map((task) => (
            <div key={task.id} className="flex items-center gap-2">
              <span
                className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                  task.status === 'completed' || task.status === 'skipped'
                    ? 'bg-green-500'
                    : task.status === 'running'
                      ? 'bg-blue-500 animate-pulse'
                      : task.status === 'failed'
                        ? 'bg-red-500'
                        : 'bg-gray-300'
                }`}
              />
              <span
                className={`text-xs truncate ${
                  task.status === 'completed' || task.status === 'skipped'
                    ? 'text-gray-500 line-through'
                    : task.status === 'running'
                      ? 'text-blue-700 font-medium'
                      : task.status === 'failed'
                        ? 'text-red-600'
                        : 'text-gray-400'
                }`}
              >
                {task.title}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
