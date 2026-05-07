import { useT } from '@/i18n';
import { useState, useMemo } from 'react';
import { CheckCircle, XCircle, Loader2, Clock, Search } from 'lucide-react';

interface TaskExecutionRecord {
  id: string;
  task_type: string;
  status: 'running' | 'success' | 'failed' | 'cancelled';
  duration_ms?: number;
  start_time?: string;
  end_time?: string;
  error_message?: string;
  created_at?: string;
}

interface Props {
  records: TaskExecutionRecord[];
  maxHeight?: string;
}

type FilterType = 'all' | 'success' | 'failed' | 'running';

const statusConfig: Record<string, { icon: React.ReactNode; bg: string; text: string }> = {
  success: { icon: <CheckCircle className="w-4 h-4" />, bg: 'bg-green-50 border-green-200', text: 'text-green-700' },
  failed: { icon: <XCircle className="w-4 h-4" />, bg: 'bg-red-50 border-red-200', text: 'text-red-700' },
  running: { icon: <Loader2 className="w-4 h-4 animate-spin" />, bg: 'bg-blue-50 border-blue-200', text: 'text-blue-700' },
  cancelled: { icon: <Clock className="w-4 h-4" />, bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-700' },
};

export default function TaskHistoryPanel({ records, maxHeight = '400px' }: Props) {
  const { t } = useT();
  const [filter, setFilter] = useState<FilterType>('all');
  const [searchText, setSearchText] = useState('');

  const filtered = useMemo(() => {
    let result = records;
    if (filter !== 'all') {
      result = result.filter((r) => r.status === filter);
    }
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      result = result.filter((r) => r.task_type.toLowerCase().includes(q));
    }
    return result.sort((a, b) => {
      const da = a.created_at || a.start_time || '';
      const db = b.created_at || b.start_time || '';
      return db.localeCompare(da);
    });
  }, [records, filter, searchText]);

  const filters: FilterType[] = ['all', 'success', 'failed', 'running'];

  return (
    <div className="flex flex-col border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-800 mb-2">{t('history.title')}</h3>

        {/* Search */}
        <div className="relative mb-2">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder={t('common.search') + '...'}
            className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1">
          {filters.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                filter === f
                  ? 'bg-blue-500 text-white'
                  : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-100'
              }`}
            >
              {f === 'all' ? t('history.all') : t(`history.${f}`)}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="overflow-y-auto" style={{ maxHeight }}>
        {filtered.length === 0 ? (
          <div className="px-4 py-8 text-center text-xs text-gray-400">
            {t('history.empty')}
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filtered.map((record) => {
              const cfg = statusConfig[record.status] || statusConfig.failed;
              return (
                <div
                  key={record.id}
                  className={`px-4 py-2.5 ${cfg.bg} border-l-2 ${
                    record.status === 'success'
                      ? 'border-l-green-500'
                      : record.status === 'failed'
                        ? 'border-l-red-500'
                        : record.status === 'running'
                          ? 'border-l-blue-500'
                          : 'border-l-yellow-500'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={cfg.text}>{cfg.icon}</span>
                    <span className={`text-sm font-medium ${cfg.text} truncate`}>
                      {record.task_type}
                    </span>
                    <span className="ml-auto text-xs text-gray-400 flex-shrink-0">
                      {record.duration_ms ? `${record.duration_ms}ms` : '—'}
                    </span>
                  </div>
                  {record.error_message && (
                    <div className="text-xs text-red-600 mt-1 pl-6">{record.error_message}</div>
                  )}
                  <div className="text-xs text-gray-400 mt-0.5 pl-6">
                    {record.start_time
                      ? new Date(record.start_time).toLocaleString()
                      : record.created_at
                        ? new Date(record.created_at).toLocaleString()
                        : '—'}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
