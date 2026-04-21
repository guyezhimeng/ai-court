import { useEffect, useState } from 'react';
import { Save, RotateCcw, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '@/api';
import { useStore } from '@/store';

interface AgentConfig {
  model: string;
  api_url: string;
  api_key: string;
  max_tokens: number;
  temperature: number;
}

interface Provider {
  id: string;
  name: string;
  api_url: string;
  models: string[];
  default_model: string;
}

export function SettingsPanel() {
  const { agents, loadAgents } = useStore();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [editConfigs, setEditConfigs] = useState<Record<string, AgentConfig>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    loadAgents();
    api.agents.providers().then(setProviders).catch(() => {});
  }, []);

  useEffect(() => {
    const configs: Record<string, AgentConfig> = {};
    for (const agent of agents) {
      configs[agent.id] = {
        model: agent.config?.model || '',
        api_url: agent.config?.api_url || '',
        api_key: '',
        max_tokens: agent.config?.max_tokens ?? 0,
        temperature: agent.config?.temperature ?? 0.5,
      };
    }
    setEditConfigs(configs);
  }, [agents]);

  const handleSave = async (agentId: string) => {
    const cfg = editConfigs[agentId];
    if (!cfg) return;

    setSaving(agentId);
    try {
      const updateData: Record<string, unknown> = {
        model: cfg.model,
        max_tokens: cfg.max_tokens,
        temperature: cfg.temperature,
      };
      if (cfg.api_url) updateData.api_url = cfg.api_url;
      if (cfg.api_key) updateData.api_key = cfg.api_key;

      await api.agents.updateConfig(agentId, updateData);
      setSaved(agentId);
      setTimeout(() => setSaved(null), 2000);
    } catch (e) {
      console.error('Save failed:', e);
    } finally {
      setSaving(null);
    }
  };

  const updateField = (agentId: string, field: keyof AgentConfig, value: string | number) => {
    setEditConfigs((prev) => ({
      ...prev,
      [agentId]: { ...prev[agentId], [field]: value },
    }));
  };

  const applyProvider = (agentId: string, providerId: string) => {
    const provider = providers.find((p) => p.id === providerId);
    if (!provider) return;
    setEditConfigs((prev) => ({
      ...prev,
      [agentId]: {
        ...prev[agentId],
        model: provider.default_model,
        api_url: provider.api_url,
      },
    }));
  };

  const groupOrder = ['sansheng', 'liubu', null];
  const groupNames: Record<string, string> = {
    sansheng: '三省',
    liubu: '六部',
  };

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 lg:p-8 max-w-4xl mx-auto animate-fadeIn">
      <h2 className="section-title text-xl">
        <span className="text-court-acc">⚙️</span> 配置中心
      </h2>

      <div className="theme-card-static mb-6 p-3">
        <p className="text-xs text-court-muted">
          💡 <strong className="text-court-acc">max_tokens</strong> 控制AI单次回复最大长度。0=不限制，值越大输出越长但消耗更多Token。
          建议太子 300-800，中书省/六部 2000-8000。
        </p>
      </div>

      {groupOrder.map((group) => {
        const groupAgents = agents.filter((a: any) => a.group === group);
        if (groupAgents.length === 0) return null;

        return (
          <div key={group || 'other'} className="mb-6">
            <h3 className="text-xs uppercase tracking-wider text-court-muted mb-3 flex items-center gap-2">
              <span className="w-6 h-px bg-court-acc/30" />
              {groupNames[group || ''] || '其他'}
            </h3>

            <div className="space-y-2">
              {groupAgents.map((agent: any) => {
                const cfg = editConfigs[agent.id];
                if (!cfg) return null;
                const isExpanded = expandedAgent === agent.id;

                return (
                  <div key={agent.id} className="theme-card-static !p-0 overflow-hidden">
                    <button
                      onClick={() => setExpandedAgent(isExpanded ? null : agent.id)}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-court-panel2/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-lg">{agent.icon}</span>
                        <span className="text-sm font-medium text-court-text">{agent.name}</span>
                        <span className="status-badge bg-court-panel2 text-court-muted text-[10px]">
                          {cfg.model || '默认'}
                        </span>
                        <span className="status-badge bg-court-acc/15 text-court-acc text-[10px]">
                          max: {cfg.max_tokens === 0 ? '∞' : cfg.max_tokens}
                        </span>
                      </div>
                      {isExpanded ? <ChevronDown size={16} className="text-court-muted" /> : <ChevronRight size={16} className="text-court-muted" />}
                    </button>

                    {isExpanded && (
                      <div className="px-4 pb-4 space-y-4 border-t border-court-line pt-4 animate-fadeIn">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-[10px] uppercase tracking-wider text-court-muted mb-1.5">模型提供商</label>
                            <select
                              className="input-field"
                              value=""
                              onChange={(e) => applyProvider(agent.id, e.target.value)}
                            >
                              <option value="">-- 快速选择 --</option>
                              {providers.map((p) => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="block text-[10px] uppercase tracking-wider text-court-muted mb-1.5">模型名称</label>
                            <input
                              type="text"
                              className="input-field"
                              value={cfg.model}
                              onChange={(e) => updateField(agent.id, 'model', e.target.value)}
                              placeholder="deepseek-chat"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-[10px] uppercase tracking-wider text-court-muted mb-1.5">API URL</label>
                            <input
                              type="text"
                              className="input-field"
                              value={cfg.api_url}
                              onChange={(e) => updateField(agent.id, 'api_url', e.target.value)}
                              placeholder="留空用全局配置"
                            />
                          </div>
                          <div>
                            <label className="block text-[10px] uppercase tracking-wider text-court-muted mb-1.5">API Key</label>
                            <input
                              type="password"
                              className="input-field"
                              value={cfg.api_key}
                              onChange={(e) => updateField(agent.id, 'api_key', e.target.value)}
                              placeholder="留空用全局配置"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-[10px] uppercase tracking-wider text-court-muted mb-1.5">
                              max_tokens
                            </label>
                            <div className="flex items-center gap-3">
                              <input
                                type="range"
                                min={0}
                                max={8000}
                                step={100}
                                value={cfg.max_tokens}
                                onChange={(e) => updateField(agent.id, 'max_tokens', parseInt(e.target.value))}
                                className="flex-1 accent-[#d4a574]"
                              />
                              <input
                                type="number"
                                min={0}
                                max={8000}
                                step={100}
                                className="w-20 input-field text-center !py-1"
                                value={cfg.max_tokens}
                                onChange={(e) => updateField(agent.id, 'max_tokens', parseInt(e.target.value) || 0)}
                              />
                            </div>
                            <p className="text-[10px] text-court-muted mt-1">
                              {cfg.max_tokens === 0 ? '∞ 不限制' : `≈ ${Math.round(cfg.max_tokens * 0.6)} 字中文`}
                            </p>
                          </div>
                          <div>
                            <label className="block text-[10px] uppercase tracking-wider text-court-muted mb-1.5">
                              temperature
                            </label>
                            <div className="flex items-center gap-3">
                              <input
                                type="range"
                                min={0}
                                max={1}
                                step={0.1}
                                value={cfg.temperature}
                                onChange={(e) => updateField(agent.id, 'temperature', parseFloat(e.target.value))}
                                className="flex-1 accent-[#d4a574]"
                              />
                              <span className="w-10 text-sm text-court-acc text-center font-mono">{cfg.temperature}</span>
                            </div>
                            <p className="text-[10px] text-court-muted mt-1">
                              {cfg.temperature <= 0.3 ? '严谨精确' : cfg.temperature <= 0.6 ? '平衡' : '创意发散'}
                            </p>
                          </div>
                        </div>

                        <div className="flex justify-end gap-2 pt-2">
                          <button
                            onClick={() => {
                              setEditConfigs((prev) => ({
                                ...prev,
                                [agent.id]: { model: '', api_url: '', api_key: '', max_tokens: 0, temperature: 0.5 },
                              }));
                            }}
                            className="btn-ghost btn-sm flex items-center gap-1.5"
                          >
                            <RotateCcw size={14} /> 重置
                          </button>
                          <button
                            onClick={() => handleSave(agent.id)}
                            disabled={saving === agent.id}
                            className="btn-accent btn-sm flex items-center gap-1.5"
                          >
                            <Save size={14} />
                            {saving === agent.id ? '保存中...' : saved === agent.id ? '✓ 已保存' : '保存'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
