import { useState, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { X } from 'lucide-react';
import type { WSClientMessage } from '@/types';

interface Props {
  sendJson: (msg: WSClientMessage) => void;
}

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'custom', label: '自定义 (OpenAI 兼容)' },
];

const MODEL_SUGGESTIONS: Record<string, string[]> = {
  openai: ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4', 'gpt-4.1'],
  anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-sonnet-4-6', 'claude-haiku-4-5'],
  custom: ['deepseek-chat', 'deepseek-reasoner', 'qwen-plus', 'qwen-max', 'glm-4', 'llama3', 'mixtral-8x7b'],
};

const PERSONALITY_STYLES = ['严谨', '活泼', '简洁', '友好', '专业'];
const PERSONALITY_TONES = ['专业', '轻松', '正式', '幽默', '温暖'];

export default function AgentCreatePanel({ sendJson }: Props) {
  const showAgentForm = useStore((s) => s.showAgentForm);
  const editingAgent = useStore((s) => s.editingAgent);
  const setShowAgentForm = useStore((s) => s.setShowAgentForm);
  const setEditingAgent = useStore((s) => s.setEditingAgent);

  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('gpt-4o');
  const [temperature, setTemperature] = useState(0.7);
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [style, setStyle] = useState('严谨');
  const [tone, setTone] = useState('专业');
  const [cliEnabled, setCliEnabled] = useState(false);
  const [webEnabled, setWebEnabled] = useState(false);
  const [visionEnabled, setVisionEnabled] = useState(false);

  useEffect(() => {
    if (editingAgent) {
      setName(editingAgent.name);
      setRole(editingAgent.role);
      setSystemPrompt(editingAgent.system_prompt);
      setProvider(editingAgent.model_provider);
      setModel(editingAgent.model_name);
      setTemperature(editingAgent.temperature);
      setStyle(editingAgent.personality?.style || '严谨');
      setTone(editingAgent.personality?.tone || '专业');
      setApiBaseUrl(editingAgent.api_base_url || '');
      setApiKey(editingAgent.api_key || '');
      setCliEnabled(editingAgent.tools_config?.cli?.enabled || false);
      setWebEnabled(editingAgent.tools_config?.web?.enabled || false);
      setVisionEnabled(editingAgent.tools_config?.vision?.enabled || false);
    } else {
      resetForm();
    }
  }, [editingAgent, showAgentForm]);

  function resetForm() {
    setName('');
    setRole('');
    setSystemPrompt('');
    setProvider('openai');
    setModel('gpt-4o');
    setTemperature(0.7);
    setApiBaseUrl('');
    setApiKey('');
    setStyle('严谨');
    setTone('专业');
    setCliEnabled(false);
    setWebEnabled(false);
    setVisionEnabled(false);
  }

  function handleClose() {
    setShowAgentForm(false);
    setEditingAgent(null);
  }

  function handleSubmit() {
    const basePayload = {
      name,
      role,
      system_prompt: systemPrompt,
      model_provider: provider,
      model_name: model,
      temperature,
      api_base_url: apiBaseUrl,
      api_key: apiKey,
      personality: { style, tone, verbosity: 'concise' },
      tools_config: {
        cli: { enabled: cliEnabled, allowed_commands: [], blocked_commands: [] },
        web: { enabled: webEnabled, max_pages: 10, allowed_domains: [], blocked_domains: [] },
        ui_automation: { enabled: false },
        vision: { enabled: visionEnabled },
      },
      skills: [],
    };

    const msg: WSClientMessage = editingAgent
      ? { type: 'update_agent', agent_id: editingAgent.id, ...basePayload }
      : { type: 'create_agent', ...basePayload };

    sendJson(msg);
    handleClose();
  }

  if (!showAgentForm) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-[520px] max-h-[85vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">
            {editingAgent ? '编辑 Agent' : '新建 Agent'}
          </h2>
          <button
            onClick={handleClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Agent 名称"
              className="w-full h-10 px-3 rounded-lg border border-gray-300 text-sm outline-none focus:border-gray-500"
            />
          </div>

          {/* Role */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">角色描述</label>
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="例如：程序开发助手、数据分析师"
              className="w-full h-10 px-3 rounded-lg border border-gray-300 text-sm outline-none focus:border-gray-500"
            />
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">系统提示</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="你是一个有用的AI助手..."
              rows={4}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-gray-500 resize-none"
            />
          </div>

          {/* LLM Provider & Model */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">LLM 提供商</label>
              <select
                value={provider}
                onChange={(e) => {
                  setProvider(e.target.value);
                  setModel(MODEL_SUGGESTIONS[e.target.value]?.[0] || 'gpt-4o');
                }}
                className="w-full h-10 px-3 rounded-lg border border-gray-300 text-sm outline-none focus:border-gray-500"
              >
                {PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">模型</label>
              <input
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="输入模型名或选择..."
                list="model-suggestions"
                className="w-full h-10 px-3 rounded-lg border border-gray-300 text-sm outline-none focus:border-gray-500"
              />
              <datalist id="model-suggestions">
                {(MODEL_SUGGESTIONS[provider] || []).map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            </div>
          </div>

          {/* Custom Base URL & API Key */}
          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Base URL <span className="text-gray-400 font-normal">(可选)</span>
              </label>
              <input
                value={apiBaseUrl}
                onChange={(e) => setApiBaseUrl(e.target.value)}
                placeholder={provider === 'openai' ? 'https://api.openai.com/v1' : provider === 'anthropic' ? 'https://api.anthropic.com' : 'https://api.deepseek.com/v1'}
                className="w-full h-10 px-3 rounded-lg border border-gray-300 text-sm outline-none focus:border-gray-500 font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key <span className="text-gray-400 font-normal">(可选，覆盖服务端配置)</span>
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full h-10 px-3 rounded-lg border border-gray-300 text-sm outline-none focus:border-gray-500 font-mono"
              />
            </div>
          </div>

          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              温度 (Temperature): {temperature.toFixed(1)}
            </label>
            <input
              type="range"
              min={0}
              max={2}
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>

          {/* Personality */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">风格</label>
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                className="w-full h-10 px-3 rounded-lg border border-gray-300 text-sm outline-none focus:border-gray-500"
              >
                {PERSONALITY_STYLES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">语气</label>
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                className="w-full h-10 px-3 rounded-lg border border-gray-300 text-sm outline-none focus:border-gray-500"
              >
                {PERSONALITY_TONES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Tools */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">工具授权</label>
            <div className="space-y-2">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={cliEnabled}
                  onChange={(e) => setCliEnabled(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">CLI (命令行)</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={webEnabled}
                  onChange={(e) => setWebEnabled(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">Web (网页抓取)</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={visionEnabled}
                  onChange={(e) => setVisionEnabled(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">Vision (视觉识别)</span>
              </label>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
          <button
            onClick={handleClose}
            className="px-5 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100 transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim()}
            className="px-5 py-2 rounded-lg text-sm text-white bg-green-500 hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {editingAgent ? '保存' : '创建'}
          </button>
        </div>
      </div>
    </div>
  );
}
