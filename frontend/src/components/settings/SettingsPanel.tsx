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

interface AgentInfo {
  id: string;
  name: string;
  group: string | null;
  icon: string;
  config: AgentConfig;
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
        max_tokens: agent.config?.max_tokens || 1500,
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
    <div className="h-full overflow-y-auto p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h3 className="text-lg font-serif font-bold text-court-text mb-1">百官配置</h3>
        <p className="text-sm text-court-muted">为每个官员单独设置模型、API 和输出参数。留空则使用全局默认配置。</p>
      </div>

      <div className="mb-4 p-3 rounded-lg bg-court-panel2 border border-court-line">
        <p className="text-xs text-court-muted">
          💡 <strong>max_tokens</strong> 控制AI单次回复的最大长度。值越大输出越长但消耗更多 Token。
          建议太子 300-800，中书省/六部 2000-8000。设为 0 表示不限制。
        </p>
      </div>

      {groupOrder.map((group) => {
        const groupAgents = agents.filter((a: any) => a.group === group);
        if (groupAgents.length === 0) return null;

        return (
          <div key={group || 'other'} className="mb-6">
            <h4 className="text-sm font-medium text-court-acc2 mb-3 flex items-center gap-2">
              <span className="w-8 h-px bg-court-acc2/30" />
              {groupNames[group || ''] || '其他'}
            </h4>

            <div className="space-y-2">
              {groupAgents.map((agent: any) => {
                const cfg = editConfigs[agent.id];
                if (!cfg) return null;
                const isExpanded = expandedAgent === agent.id;

                return (
                  <div key={agent.id} className="court-card !p-0 overflow-hidden">
                    <button
                      onClick={() => setExpandedAgent(isExpanded ? null : agent.id)}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-court-panel2/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-lg">{agent.icon}</span>
                        <span className="text-sm font-medium text-court-text">{agent.name}</span>
                        <span className="court-badge bg-court-panel2 text-court-muted">
                          {cfg.model || '默认'}
                        </span>
                        <span className="court-badge bg-court-acc/10 text-court-acc text-[10px]">
                          max_tokens: {cfg.max_tokens}
                        </span>
                      </div>
                      {isExpanded ? (
                        <ChevronDown size={16} className="text-court-muted" />
                      ) : (
                        <ChevronRight size={16} className="text-court-muted" />
                      )}
                    </button>

                    {isExpanded && (
                      <div className="px-4 pb-4 space-y-4 border-t border-court-line pt-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs text-court-muted mb-1.5">模型提供商</label>
                            <select
                              className="w-full bg-court-panel2 border border-court-line rounded-lg px-3 py-2 text-sm text-court-text outline-none focus:border-court-acc"
                              value=""
                              onChange={(e) => applyProvider(agent.id, e.target.value)}
                            >
                              <option value="">-- 快速选择 --</option>
                              {providers.map((p) => (
                                <option key={p.id} value={p.id}>
                                  {p.name}
                                </option>
                              ))}
                            </select>
                          </div>

                          <div>
                            <label className="block text-xs text-court-muted mb-1.5">模型名称</label>
                            <input
                              type="text"
                              className="w-full bg-court-panel2 border border-court-line rounded-lg px-3 py-2 text-sm text-court-text outline-none focus:border-court-acc"
                              value={cfg.model}
                              onChange={(e) => updateField(agent.id, 'model', e.target.value)}
                              placeholder="deepseek-chat"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs text-court-muted mb-1.5">API URL（留空用全局）</label>
                            <input
                              type="text"
                              className="w-full bg-court-panel2 border border-court-line rounded-lg px-3 py-2 text-sm text-court-text outline-none focus:border-court-acc"
                              value={cfg.api_url}
                              onChange={(e) => updateField(agent.id, 'api_url', e.target.value)}
                              placeholder="https://api.deepseek.com/v1"
                            />
                          </div>

                          <div>
                            <label className="block text-xs text-court-muted mb-1.5">API Key（留空用全局）</label>
                            <input
                              type="password"
                              className="w-full bg-court-panel2 border border-court-line rounded-lg px-3 py-2 text-sm text-court-text outline-none focus:border-court-acc"
                              value={cfg.api_key}
                              onChange={(e) => updateField(agent.id, 'api_key', e.target.value)}
                              placeholder="sk-..."
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs text-court-muted mb-1.5">
                              max_tokens（最大输出长度）
                            </label>
                            <div className="flex items-center gap-3">
                              <input
                                type="range"
                                min={0}
                                max={8000}
                                step={100}
                                value={cfg.max_tokens}
                                onChange={(e) => updateField(agent.id, 'max_tokens', parseInt(e.target.value))}
                                className="flex-1 accent-court-acc"
                              />
                              <input
                                type="number"
                                min={0}
                                max={8000}
                                step={100}
                                className="w-20 bg-court-panel2 border border-court-line rounded-lg px-2 py-1.5 text-sm text-court-text text-center outline-none focus:border-court-acc"
                                value={cfg.max_tokens}
                                onChange={(e) => updateField(agent.id, 'max_tokens', parseInt(e.target.value) || 0)}
                              />
                            </div>
                            <p className="text-[10px] text-court-muted mt-1">
                              {cfg.max_tokens === 0 ? '不限制' : `约 ${Math.round(cfg.max_tokens * 0.6)} 字中文`}
                            </p>
                          </div>

                          <div>
                            <label className="block text-xs text-court-muted mb-1.5">
                              temperature（创造性）
                            </label>
                            <div className="flex items-center gap-3">
                              <input
                                type="range"
                                min={0}
                                max={1}
                                step={0.1}
                                value={cfg.temperature}
                                onChange={(e) => updateField(agent.id, 'temperature', parseFloat(e.target.value))}
                                className="flex-1 accent-court-acc2"
                              />
                              <span className="w-10 text-sm text-court-text text-center">{cfg.temperature}</span>
                            </div>
                            <p className="text-[10px] text-court-muted mt-1">
                              {cfg.temperature <= 0.3 ? '严谨精确' : cfg.temperature <= 0.6 ? '平衡' : '创意发散'}
                            </p>
                          </div>
                        </div>

                        <div className="flex justify-end gap-2 pt-2">
                          <button
                            onClick={() => {
                              const defaultCfg: AgentConfig = {
                                model: '',
                                api_url: '',
                                api_key: '',
                                max_tokens: 1500,
                                temperature: 0.5,
                              };
                              setEditConfigs((prev) => ({ ...prev, [agent.id]: defaultCfg }));
                            }}
                            className="court-btn-ghost flex items-center gap-1.5 text-xs"
                          >
                            <RotateCcw size={14} />
                            重置
                          </button>
                          <button
                            onClick={() => handleSave(agent.id)}
                            disabled={saving === agent.id}
                            className="court-btn-primary flex items-center gap-1.5 text-xs"
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
