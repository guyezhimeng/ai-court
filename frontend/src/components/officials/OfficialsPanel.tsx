import { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, Cpu, Zap, Clock } from 'lucide-react';
import { api } from '@/api';
import { useStore } from '@/store';

interface AgentDetail {
  id: string;
  name: string;
  group: string | null;
  icon: string;
  soul_loaded: boolean;
  model: string;
  has_custom_api: boolean;
  soul?: string;
  config: {
    model: string;
    api_url: string;
    has_api_key: boolean;
    max_tokens: number;
    temperature: number;
    effective_api_url: string;
    effective_model: string;
  };
}

export function OfficialsPanel() {
  const { agents, loadAgents } = useStore();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [agentDetails, setAgentDetails] = useState<Record<string, AgentDetail>>({});

  useEffect(() => {
    loadAgents();
  }, []);

  const loadDetail = async (agentId: string) => {
    if (agentDetails[agentId]) return;
    try {
      const detail = await api.agents.get(agentId);
      setAgentDetails((prev) => ({ ...prev, [agentId]: detail }));
    } catch {}
  };

  const toggleExpand = (agentId: string) => {
    if (expandedId === agentId) {
      setExpandedId(null);
    } else {
      setExpandedId(agentId);
      loadDetail(agentId);
    }
  };

  const groupOrder = ['sansheng', 'liubu', null];
  const groupNames: Record<string, string> = {
    sansheng: '三省',
    liubu: '六部',
  };

  const onlineCount = agents.filter((a: any) => a.soul_loaded).length;
  const customApiCount = agents.filter((a: any) => a.has_custom_api).length;

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 lg:p-8 max-w-5xl mx-auto animate-fadeIn">
      <h2 className="section-title text-xl">
        <span className="text-court-acc">👥</span> 官员总览
      </h2>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div className="stat-card">
          <div className="stat-label">总官员</div>
          <div className="stat-value">{agents.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">已就任</div>
          <div className="stat-value text-court-ok">{onlineCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">独立API</div>
          <div className="stat-value text-court-info">{customApiCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">默认模型</div>
          <div className="stat-value text-sm">{agents[0]?.model || 'deepseek-chat'}</div>
        </div>
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
                const isExpanded = expandedId === agent.id;
                const detail = agentDetails[agent.id];

                return (
                  <div key={agent.id} className="theme-card-static !p-0 overflow-hidden">
                    <button
                      onClick={() => toggleExpand(agent.id)}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-court-panel2/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{agent.icon}</span>
                        <div className="text-left">
                          <div className="text-sm font-medium text-court-text">{agent.name}</div>
                          <div className="text-xs text-court-muted">
                            {agent.model || '默认模型'} · max_tokens: {detail?.config?.max_tokens || '—'}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {agent.soul_loaded ? (
                          <span className="status-online">就任</span>
                        ) : (
                          <span className="status-offline">空缺</span>
                        )}
                        {isExpanded ? <ChevronDown size={16} className="text-court-muted" /> : <ChevronRight size={16} className="text-court-muted" />}
                      </div>
                    </button>

                    {isExpanded && detail && (
                      <div className="px-4 pb-4 border-t border-court-line pt-3 space-y-3 animate-fadeIn">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-court-muted mb-1">生效模型</div>
                            <div className="text-sm font-mono text-court-acc">{detail.config.effective_model}</div>
                          </div>
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-court-muted mb-1">API 端点</div>
                            <div className="text-xs text-court-muted truncate">{detail.config.effective_api_url}</div>
                          </div>
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-court-muted mb-1">max_tokens</div>
                            <div className="text-sm font-mono text-court-text">
                              {detail.config.max_tokens === 0 ? '不限制' : detail.config.max_tokens}
                            </div>
                          </div>
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-court-muted mb-1">temperature</div>
                            <div className="text-sm font-mono text-court-text">{detail.config.temperature}</div>
                          </div>
                        </div>

                        {detail.soul && (
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-court-muted mb-1">人设摘要</div>
                            <div className="text-xs text-court-muted bg-court-bg rounded-lg p-3 line-clamp-3">
                              {detail.soul}
                            </div>
                          </div>
                        )}

                        <div className="flex items-center gap-2 text-xs text-court-muted">
                          <Cpu size={12} />
                          <span>独立API: {detail.config.has_api_key ? '✓ 是' : '✗ 使用全局'}</span>
                          <span className="mx-1">·</span>
                          <Zap size={12} />
                          <span>人设: {detail.soul_loaded ? '已加载' : '未加载'}</span>
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
