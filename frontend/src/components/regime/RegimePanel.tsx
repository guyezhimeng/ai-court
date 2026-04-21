import { useState } from 'react';
import { Check, ArrowRight, RotateCcw } from 'lucide-react';
import { useStore, REGIME_INFO, RegimeKey } from '@/store';

const REGIME_AGENTS: Record<RegimeKey, { groups: { name: string; agents: { id: string; name: string; icon: string }[] }[] }> = {
  'tang-sansheng': {
    groups: [
      {
        name: '三省',
        agents: [
          { id: 'zhongshu', name: '中书省', icon: '📜' },
          { id: 'menxia', name: '门下省', icon: '🔍' },
          { id: 'shangshu', name: '尚书省', icon: '📮' },
        ],
      },
      {
        name: '六部',
        agents: [
          { id: 'hubu', name: '户部', icon: '💰' },
          { id: 'libu', name: '礼部', icon: '🎭' },
          { id: 'bingbu', name: '兵部', icon: '⚔️' },
          { id: 'xingbu', name: '刑部', icon: '⚖️' },
          { id: 'gongbu', name: '工部', icon: '🔨' },
          { id: 'libu_hr', name: '吏部', icon: '📋' },
        ],
      },
    ],
  },
  'ming-neige': {
    groups: [
      {
        name: '中枢',
        agents: [
          { id: 'silijian', name: '司礼监', icon: '🏮' },
          { id: 'neige', name: '内阁', icon: '📜' },
          { id: 'duchayuan', name: '都察院', icon: '🔍' },
        ],
      },
      {
        name: '六部',
        agents: [
          { id: 'hubu', name: '户部', icon: '💰' },
          { id: 'libu', name: '礼部', icon: '🎭' },
          { id: 'bingbu', name: '兵部', icon: '⚔️' },
          { id: 'xingbu', name: '刑部', icon: '⚖️' },
          { id: 'gongbu', name: '工部', icon: '🔨' },
          { id: 'libu_hr', name: '吏部', icon: '📋' },
        ],
      },
    ],
  },
  'modern-ceo': {
    groups: [
      {
        name: 'C-Suite',
        agents: [
          { id: 'ceo', name: 'CEO', icon: '👔' },
          { id: 'coo', name: 'COO', icon: '📊' },
          { id: 'cto', name: 'CTO', icon: '💻' },
        ],
      },
      {
        name: '部门',
        agents: [
          { id: 'cfo', name: 'CFO·财务', icon: '💰' },
          { id: 'cmo', name: 'CMO·市场', icon: '📢' },
          { id: 'chro', name: 'CHRO·人力', icon: '👥' },
          { id: 'clo', name: 'CLO·法务', icon: '⚖️' },
          { id: 'cpo', name: 'CPO·产品', icon: '🔨' },
          { id: 'cso', name: 'CSO·战略', icon: '🎯' },
        ],
      },
    ],
  },
};

const REGIME_FLOW: Record<RegimeKey, string[]> = {
  'tang-sansheng': ['皇帝下旨', '太子分拣', '中书省拟旨', '门下省审核', '尚书省执行', '六部落实'],
  'ming-neige': ['皇帝下旨', '司礼监批红', '内阁票拟', '都察院监察', '六部执行'],
  'modern-ceo': ['CEO决策', 'COO协调', 'CTO/CFO/CMO执行', '部门落实'],
};

export function RegimePanel() {
  const { currentRegime, setRegime } = useStore();
  const [confirmRegime, setConfirmRegime] = useState<RegimeKey | null>(null);
  const [switched, setSwitched] = useState(false);

  const handleSwitch = (regime: RegimeKey) => {
    if (regime === currentRegime) return;
    setConfirmRegime(regime);
  };

  const confirmSwitch = () => {
    if (!confirmRegime) return;
    setRegime(confirmRegime);
    setConfirmRegime(null);
    setSwitched(true);
    setTimeout(() => setSwitched(false), 2000);
  };

  const regimeData = REGIME_AGENTS[currentRegime];
  const flow = REGIME_FLOW[currentRegime];

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 lg:p-8 max-w-5xl mx-auto animate-fadeIn">
      <h2 className="section-title text-xl">
        <span className="text-court-acc">🔄</span> 制度切换
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {(Object.entries(REGIME_INFO) as [RegimeKey, typeof REGIME_INFO[RegimeKey]][]).map(([key, info]) => (
          <div
            key={key}
            onClick={() => handleSwitch(key)}
            className={`theme-card cursor-pointer transition-all duration-300 ${
              currentRegime === key
                ? 'ring-2 ring-court-acc shadow-lg shadow-court-acc/10'
                : 'hover:ring-1 hover:ring-court-acc/30'
            }`}
          >
            <div className="text-3xl mb-2">{info.icon}</div>
            <h3 className="text-sm font-serif font-bold text-court-text mb-1">{info.name}</h3>
            <p className="text-xs text-court-muted leading-relaxed">{info.desc}</p>
            {currentRegime === key && (
              <div className="mt-2 inline-flex items-center gap-1 text-xs text-court-acc">
                <Check size={12} /> 当前制度
              </div>
            )}
          </div>
        ))}
      </div>

      {confirmRegime && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setConfirmRegime(null)}>
          <div className="theme-card-static max-w-md w-full mx-4 animate-fadeIn" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-base font-serif font-bold text-court-text mb-2">确认切换制度</h3>
            <p className="text-sm text-court-muted mb-4">
              将从 <strong className="text-court-acc">{REGIME_INFO[currentRegime].name}</strong> 切换为{' '}
              <strong className="text-court-acc">{REGIME_INFO[confirmRegime].name}</strong>，官员架构将重新调整。
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setConfirmRegime(null)} className="btn-ghost btn-sm">取消</button>
              <button onClick={confirmSwitch} className="btn-accent btn-sm">确认切换</button>
            </div>
          </div>
        </div>
      )}

      {switched && (
        <div className="fixed top-4 right-4 bg-court-ok/20 text-court-ok px-4 py-2 rounded-lg text-sm animate-fadeIn z-50">
          ✅ 制度切换成功
        </div>
      )}

      <div className="mb-8">
        <h3 className="text-sm font-medium text-court-text mb-3 flex items-center gap-2">
          <span className="text-court-acc">▸</span> 当前流程
        </h3>
        <div className="flex flex-wrap items-center gap-2">
          {flow.map((step, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="px-3 py-1.5 rounded-lg bg-court-panel2 text-xs text-court-text font-medium">
                {step}
              </span>
              {i < flow.length - 1 && <ArrowRight size={14} className="text-court-acc/50" />}
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-sm font-medium text-court-text mb-3 flex items-center gap-2">
          <span className="text-court-acc">▸</span> 官员架构
        </h3>
        <div className="space-y-4">
          {regimeData.groups.map((group) => (
            <div key={group.name}>
              <div className="text-[10px] uppercase tracking-wider text-court-muted mb-2">{group.name}</div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                {group.agents.map((agent) => (
                  <div key={agent.id} className="theme-card-static flex items-center gap-2.5 !p-3">
                    <span className="text-lg">{agent.icon}</span>
                    <div>
                      <div className="text-sm font-medium text-court-text">{agent.name}</div>
                      <div className="text-[10px] text-court-muted font-mono">{agent.id}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
