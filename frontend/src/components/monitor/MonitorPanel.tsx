import { useEffect, useState } from 'react';
import { Activity, ArrowRight, Clock, CheckCircle, XCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { api } from '@/api';
import { useStore } from '@/store';

const STATE_LABELS: Record<string, { label: string; color: string; icon: any }> = {
  Taizi: { label: '太子分拣', color: 'text-yellow-400 bg-yellow-500/20', icon: Clock },
  Zhongshu: { label: '中书拟旨', color: 'text-blue-400 bg-blue-500/20', icon: Activity },
  Menxia: { label: '门下审核', color: 'text-purple-400 bg-purple-500/20', icon: AlertCircle },
  Shangshu: { label: '尚书执行', color: 'text-orange-400 bg-orange-500/20', icon: ArrowRight },
  Hubu: { label: '户部', color: 'text-green-400 bg-green-500/20', icon: CheckCircle },
  Libu: { label: '礼部', color: 'text-pink-400 bg-pink-500/20', icon: CheckCircle },
  Bingbu: { label: '兵部', color: 'text-red-400 bg-red-500/20', icon: CheckCircle },
  Xingbu: { label: '刑部', color: 'text-amber-400 bg-amber-500/20', icon: CheckCircle },
  Gongbu: { label: '工部', color: 'text-cyan-400 bg-cyan-500/20', icon: CheckCircle },
  Done: { label: '已完成', color: 'text-green-400 bg-green-500/20', icon: CheckCircle },
  Rejected: { label: '已驳回', color: 'text-red-400 bg-red-500/20', icon: XCircle },
};

export function MonitorPanel() {
  const { tasks, taskSummary, loadTasks } = useStore();
  const [filter, setFilter] = useState<string>('all');
  const [selectedTask, setSelectedTask] = useState<string | null>(null);

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 15000);
    return () => clearInterval(interval);
  }, []);

  const filteredTasks = filter === 'all' ? tasks : tasks.filter((t: any) => t.state === filter);
  const stateCounts: Record<string, number> = {};
  for (const t of tasks) {
    stateCounts[t.state] = (stateCounts[t.state] || 0) + 1;
  }

  const activeCount = tasks.filter((t: any) => !['Done', 'Rejected'].includes(t.state)).length;
  const doneCount = stateCounts['Done'] || 0;
  const rejectedCount = stateCounts['Rejected'] || 0;

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 lg:p-8 max-w-5xl mx-auto animate-fadeIn">
      <div className="flex items-center justify-between mb-6">
        <h2 className="section-title text-xl mb-0">
          <span className="text-court-acc">⚡</span> 省部调度
        </h2>
        <button onClick={loadTasks} className="btn-ghost btn-sm flex items-center gap-1.5">
          <RefreshCw size={14} /> 刷新
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <div className="stat-card">
          <div className="stat-label">总旨意</div>
          <div className="stat-value">{tasks.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">进行中</div>
          <div className="stat-value text-yellow-400">{activeCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">已完成</div>
          <div className="stat-value text-court-ok">{doneCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">已驳回</div>
          <div className="stat-value text-court-danger">{rejectedCount}</div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <button onClick={() => setFilter('all')} className={filter === 'all' ? 'filter-btn-active' : 'filter-btn'}>
          全部 ({tasks.length})
        </button>
        {Object.entries(stateCounts).map(([state, count]) => {
          const info = STATE_LABELS[state];
          if (!info) return null;
          return (
            <button key={state} onClick={() => setFilter(state)} className={filter === state ? 'filter-btn-active' : 'filter-btn'}>
              {info.label} ({count})
            </button>
          );
        })}
      </div>

      {filteredTasks.length === 0 ? (
        <div className="text-center py-16 text-court-muted">
          <Activity size={48} className="mx-auto mb-3 opacity-30" />
          <p>暂无旨意记录</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredTasks.map((task: any) => {
            const stateInfo = STATE_LABELS[task.state] || { label: task.state, color: 'text-gray-400 bg-gray-500/20', icon: Clock };
            const StateIcon = stateInfo.icon;

            return (
              <div key={task.id} className="theme-card cursor-pointer" onClick={() => setSelectedTask(selectedTask === task.id ? null : task.id)}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <StateIcon size={16} className={stateInfo.color.split(' ')[0]} />
                    <div>
                      <div className="text-sm font-medium text-court-text">{task.title || task.trace_id}</div>
                      <div className="text-xs text-court-muted font-mono">{task.trace_id}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`status-badge ${stateInfo.color}`}>{stateInfo.label}</span>
                  </div>
                </div>

                {selectedTask === task.id && (
                  <div className="mt-3 pt-3 border-t border-court-line space-y-2 animate-fadeIn">
                    {task.description && (
                      <div>
                        <div className="text-[10px] uppercase tracking-wider text-court-muted mb-1">旨意内容</div>
                        <div className="text-sm text-court-text bg-court-bg rounded-lg p-3">{task.description}</div>
                      </div>
                    )}
                    <div className="grid grid-cols-3 gap-3 text-xs">
                      <div>
                        <span className="text-court-muted">当前环节</span>
                        <div className="font-medium text-court-acc mt-0.5">{stateInfo.label}</div>
                      </div>
                      <div>
                        <span className="text-court-muted">创建时间</span>
                        <div className="text-court-text mt-0.5">{new Date(task.created_at).toLocaleString('zh-CN')}</div>
                      </div>
                      <div>
                        <span className="text-court-muted">更新时间</span>
                        <div className="text-court-text mt-0.5">{task.updated_at ? new Date(task.updated_at).toLocaleString('zh-CN') : '—'}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
