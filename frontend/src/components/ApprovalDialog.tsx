import { useState, useEffect, useRef } from 'react';
import { AlertTriangle, Clock, CheckCircle, XCircle, Edit3 } from 'lucide-react';

interface ApprovalDialogProps {
  requestId: string;
  type: string;
  context: Record<string, unknown>;
  requester: string;
  timeoutSeconds: number;
  dangerous: boolean;
  onRespond: (
    requestId: string,
    response: 'approved' | 'rejected' | 'modified',
    feedback?: string,
    modifiedParams?: Record<string, unknown>
  ) => void;
  // onDismiss is not used directly — dialog auto-closes on respond
}

const TYPE_LABELS: Record<string, string> = {
  tool_execution: '工具执行审批',
  plan_approval: '计划审批',
  final_result: '最终结果审批',
  dangerous_action: '高危操作审批',
};

export default function ApprovalDialog({
  requestId,
  type,
  context,
  requester,
  timeoutSeconds,
  dangerous,
  onRespond,
}: ApprovalDialogProps) {
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [modifiedParams, setModifiedParams] = useState(
    JSON.stringify(context, null, 2)
  );
  const [showModify, setShowModify] = useState(false);
  const [timeLeft, setTimeLeft] = useState(timeoutSeconds);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (timeLeft <= 0) {
      onRespond(requestId, 'rejected', '审批超时，自动拒绝');
      return;
    }
    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          onRespond(requestId, 'rejected', '审批超时，自动拒绝');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [requestId, onRespond]);

  const typeLabel = TYPE_LABELS[type] || type;
  const isUrgent = timeLeft <= 10;

  const handleApprove = () => {
    let finals: Record<string, unknown> | undefined;
    if (showModify) {
      try {
        finals = JSON.parse(modifiedParams);
      } catch {
        finals = { raw: modifiedParams };
      }
    }
    onRespond(requestId, 'approved', feedback || undefined, finals);
  };

  const handleReject = () => {
    onRespond(requestId, 'rejected', feedback || undefined);
  };

  const handleModify = () => {
    try {
      const params = JSON.parse(modifiedParams);
      onRespond(requestId, 'modified', feedback || undefined, params);
    } catch {
      onRespond(requestId, 'modified', feedback || undefined, { raw: modifiedParams });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className={`bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden ${
        dangerous ? 'border-2 border-red-400' : ''
      }`}>
        {/* Header */}
        <div className={`px-6 py-4 flex items-center gap-3 ${
          dangerous ? 'bg-red-50' : 'bg-blue-50'
        }`}>
          {dangerous ? (
            <AlertTriangle className="w-6 h-6 text-red-500" />
          ) : (
            <Clock className="w-6 h-6 text-blue-500" />
          )}
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gray-800">{typeLabel}</h2>
            <p className="text-xs text-gray-500">
              发起者: {requester || '系统'}
              {dangerous && ' · 此操作可能需要您的确认'}
            </p>
          </div>
          <span className={`text-sm font-mono font-bold ${
            isUrgent ? 'text-red-500 animate-pulse' : 'text-gray-500'
          }`}>
            {timeLeft}s
          </span>
        </div>

        {/* Context */}
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
            审批内容
          </h3>
          {type === 'tool_execution' && (
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <code className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded text-xs font-mono">
                  {String(context.tool_name || '未知工具')}
                </code>
              </div>
              <pre className="text-xs text-gray-600 overflow-auto max-h-32">
                {JSON.stringify(context, null, 2)}
              </pre>
            </div>
          )}
          {type === 'plan_approval' && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-sm font-medium text-gray-700">
                {String(context.plan_title || '未命名计划')}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                子任务数: {String(context.subtask_count || '?')}
              </p>
            </div>
          )}
          {type === 'final_result' && (
            <div className="bg-gray-50 rounded-lg p-3 max-h-48 overflow-auto">
              <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                {String(context.result_summary || context.output || '查看结果')}
              </pre>
            </div>
          )}
          {type === 'dangerous_action' && (
            <div className="bg-red-50 rounded-lg p-3 border border-red-200">
              <p className="text-sm text-red-700">{String(context.description || '高危操作')}</p>
            </div>
          )}
        </div>

        {/* Feedback (conditional) */}
        {showFeedback && (
          <div className="px-6 py-3 border-b border-gray-100">
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="输入反馈理由..."
              rows={2}
              className="w-full resize-none rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
            />
          </div>
        )}

        {/* Modify (conditional) */}
        {showModify && (
          <div className="px-6 py-3 border-b border-gray-100">
            <p className="text-xs text-gray-400 mb-1">编辑参数 (JSON 格式)</p>
            <textarea
              value={modifiedParams}
              onChange={(e) => setModifiedParams(e.target.value)}
              rows={4}
              className="w-full resize-none rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-xs font-mono focus:outline-none focus:border-blue-400"
            />
          </div>
        )}

        {/* Actions */}
        <div className="px-6 py-4 flex items-center gap-2">
          <button
            onClick={handleApprove}
            className="flex items-center gap-1.5 px-4 py-2 bg-green-500 text-white rounded-lg text-sm font-medium hover:bg-green-600 transition-colors"
          >
            <CheckCircle className="w-4 h-4" />
            批准
          </button>

          <button
            onClick={handleReject}
            className="flex items-center gap-1.5 px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600 transition-colors"
          >
            <XCircle className="w-4 h-4" />
            拒绝
          </button>

          <button
            onClick={() => { setShowModify(!showModify); if (!showModify) handleModify; }}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              showModify
                ? 'bg-blue-100 text-blue-700'
                : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
            }`}
          >
            <Edit3 className="w-4 h-4" />
            修改
          </button>

          {showModify && (
            <button
              onClick={handleModify}
              className="flex items-center gap-1.5 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors"
            >
              确认修改
            </button>
          )}

          <div className="flex-1" />

          <button
            onClick={() => setShowFeedback(!showFeedback)}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            {showFeedback ? '隐藏反馈' : '添加反馈'}
          </button>
        </div>
      </div>
    </div>
  );
}
