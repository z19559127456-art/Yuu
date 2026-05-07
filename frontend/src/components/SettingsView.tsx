import { useState } from 'react';
import { useStore } from '@/store/useStore';
import { Sun, Moon, Terminal, Shield } from 'lucide-react';

export default function SettingsView() {
  const wsConnected = useStore((s) => s.wsConnected);

  // CLI config local state
  const [cliEnabled, setCliEnabled] = useState(true);
  const [allowedCommands, setAllowedCommands] = useState('ls, cat, pwd, echo, git, curl, python, node, npm');
  const [blockedCommands, setBlockedCommands] = useState('rm, sudo, chmod, chown, kill, dd, mkfs, wget');
  const [toolTimeout, setToolTimeout] = useState(60);
  const [cliSaved, setCliSaved] = useState(false);

  const handleSaveCliConfig = () => {
    // TODO(H): persist CLI config to backend via WebSocket or API
    setCliSaved(true);
    setTimeout(() => setCliSaved(false), 2000);
  };

  return (
    <div className="w-72 flex-shrink-0 flex flex-col bg-white border-r border-gray-200">
      {/* Header */}
      <div className="h-16 flex items-center px-5 border-b border-gray-100">
        <h1 className="text-lg font-semibold text-gray-800">设置</h1>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Connection status */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">连接状态</h3>
          <div className="flex items-center gap-2 text-sm">
            <span className={`inline-block w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-400'}`} />
            <span className="text-gray-600">{wsConnected ? '已连接到后端服务' : '未连接'}</span>
          </div>
        </div>

        {/* Theme */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">主题</h3>
          <div className="flex gap-2">
            <button className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 text-sm text-gray-700 hover:bg-gray-200 transition-colors">
              <Sun className="w-4 h-4" />
              浅色
            </button>
            <button className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-100 transition-colors">
              <Moon className="w-4 h-4" />
              深色
            </button>
          </div>
        </div>

        {/* CLI Security Config */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Terminal className="w-4 h-4 text-gray-600" />
            <h3 className="text-sm font-medium text-gray-700">CLI 安全配置</h3>
          </div>
          <div className="space-y-3">
            {/* Enable toggle */}
            <label className="flex items-center justify-between text-sm text-gray-600">
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5" />
                启用 CLI 工具
              </span>
              <button
                onClick={() => setCliEnabled(!cliEnabled)}
                className={`relative w-9 h-5 rounded-full transition-colors ${
                  cliEnabled ? 'bg-green-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                    cliEnabled ? 'translate-x-4' : 'translate-x-0'
                  }`}
                />
              </button>
            </label>

            {/* Allowed commands */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">允许的命令（逗号分隔）</label>
              <textarea
                value={allowedCommands}
                onChange={(e) => setAllowedCommands(e.target.value)}
                rows={2}
                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-700 outline-none focus:border-gray-400 focus:bg-white transition-colors resize-none"
                placeholder="ls, cat, pwd, ..."
              />
            </div>

            {/* Blocked commands */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">阻止的命令（逗号分隔）</label>
              <textarea
                value={blockedCommands}
                onChange={(e) => setBlockedCommands(e.target.value)}
                rows={2}
                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-700 outline-none focus:border-gray-400 focus:bg-white transition-colors resize-none"
                placeholder="rm, sudo, chmod, ..."
              />
            </div>

            {/* Timeout */}
            <div>
              <label className="block text-xs text-gray-500 mb-1">命令超时（秒）</label>
              <input
                type="number"
                value={toolTimeout}
                onChange={(e) => setToolTimeout(Math.max(5, Math.min(300, Number(e.target.value))))}
                min={5}
                max={300}
                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-700 outline-none focus:border-gray-400 focus:bg-white transition-colors"
              />
            </div>

            {/* Save button */}
            <button
              onClick={handleSaveCliConfig}
              className={`w-full py-1.5 rounded-lg text-xs font-medium transition-all ${
                cliSaved
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-800 text-white hover:bg-gray-700 active:scale-[0.98]'
              }`}
            >
              {cliSaved ? '✓ 已保存' : '保存配置'}
            </button>
          </div>
        </div>

        {/* About */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">关于</h3>
          <div className="text-sm text-gray-500 space-y-1">
            <p>vx版Agent集合体</p>
            <p>版本: 0.5.0</p>
            <p>AI Agent Messenger OS</p>
          </div>
        </div>
      </div>
    </div>
  );
}
