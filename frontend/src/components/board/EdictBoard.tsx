import { useEffect, useState } from 'react';
import { LayoutDashboard, Clock, CheckCircle, XCircle, ArrowRight, RefreshCw } from 'lucide-react';
import { api } from '@/api';
import { useStore } from '@/store';

const STATE_INFO: Record<string, { label: string; color: string }> = {
  Taizi: { label: '太子分拣', color: 'border-l-yellow-500' },
  Zhongshu: { label: '中书拟旨', color: 'border-l-blue-500' },
  Menxia: { label: '门下审核', color: 'border-l-purple-500' },
  Shangshu: { label: '尚书执行', color: 'border-l-orange-500' },
  Hubu: { label: '户部', color: 'border-l-green-500' },
  Libu: { label: '礼部', color: 'border-l-pink-500' },
  Bingbu: { label: '兵部', color: 'border-l-red-500' },
  Xingbu: { label: '刑部', color: 'border-l-amber-500' },
  Gongbu: { label: '工部', color: 'border-l-cyan-500' },
  Done: { label: '已完成', color: 'border-l-green-500' },
  Rejected: { label: '已驳回', color: 'border-l-red-500' },
};

export function EdictBoard() {
  const { tasks, loadTasks } = useStore();
  const [view, setView] = useState<'kanban' | 'list'>('kanban');

  useEffect(() => {
    loadTasks();
  }, []);

  const columns = ['Taizi', 'Zhongshu', 'Menxia', 'Shangshu', 'Done'];
  const columnTasks: Record<string, any[]> = {};
  for (const col of columns) {
    columnTasks[col] = tasks.filter((t: any) => t.state === col);
  }
  const otherTasks = tasks.filter((t: any) => !columns.includes(t.state) && t.state !== 'Rejected');
  const rejectedTasks = tasks.filter((t: any) => t.state === 'Rejected');

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 lg:p-8 animate-fadeIn">
      <div className="flex items-center justify-between mb-6">
        <h2 className="section-title text-xl mb-0">
          <span className="text-court-acc">📋</span> 旨意看板
        </h2>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <button onClick={() => setView('kanban')} className={view === 'kanban' ? 'filter-btn-active' : 'filter-btn'}>
              看板
            </button>
            <button onClick={() => setView('list')} className={view === 'list' ? 'filter-btn-active' : 'filter-btn'}>
              列表
            </button>
          </div>
          <button onClick={loadTasks} className="btn-ghost btn-sm flex items-center gap-1.5">
            <RefreshCw size={14} /> 刷新
          </button>
        </div>
      </div>

      {view === 'kanban' ? (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {columns.map((col) => {
            const info = STATE_INFO[col] || { label: col, color: 'border-l-gray-500' };
            const colTasks = columnTasks[col];
            return (
              <div key={col} className="min-w-[260px] flex-1">
                <div className="flex items-center gap-2 mb-3 px-1">
                  <div className={`w-2 h-2 rounded-full ${info.color.replace('border-l-', 'bg-')}`} />
                  <span className="text-xs font-medium text-court-text uppercase tracking-wider">{info.label}</span>
                  <span className="text-xs text-court-muted ml-auto">{colTasks.length}</span>
                </div>
                <div className="space-y-2">
                  {colTasks.length === 0 ? (
                    <div className="theme-card-static text-center py-6 text-court-muted text-xs opacity-50">
                      暂无
                    </div>
                  ) : (
                    colTasks.map((task: any) => (
                      <div key={task.id} className={`theme-card border-l-4 ${info.color}`}>
                        <div className="text-sm font-medium text-court-text mb-1">{task.title || '旨意'}</div>
                        <div className="text-[10px] font-mono text-court-muted">{task.trace_id}</div>
                        {task.description && (
                          <p className="text-xs text-court-muted mt-2 line-clamp-2">{task.description}</p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
          {otherTasks.length > 0 && (
            <div className="min-w-[260px] flex-1">
              <div className="flex items-center gap-2 mb-3 px-1">
                <ArrowRight size={12} className="text-court-acc" />
                <span className="text-xs font-medium text-court-text uppercase tracking-wider">执行中</span>
                <span className="text-xs text-court-muted ml-auto">{otherTasks.length}</span>
              </div>
              <div className="space-y-2">
                {otherTasks.map((task: any) => {
                  const info = STATE_INFO[task.state] || { label: task.state, color: 'border-l-gray-500' };
                  return (
                    <div key={task.id} className={`theme-card border-l-4 ${info.color}`}>
                      <div className="text-sm font-medium text-court-text mb-1">{task.title || '旨意'}</div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-court-muted">{task.trace_id}</span>
                        <span className="status-badge bg-court-panel2 text-court-muted text-[10px]">{info.label}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {rejectedTasks.length > 0 && (
            <div className="min-w-[260px] flex-1">
              <div className="flex items-center gap-2 mb-3 px-1">
                <XCircle size={12} className="text-court-danger" />
                <span className="text-xs font-medium text-court-danger uppercase tracking-wider">已驳回</span>
                <span className="text-xs text-court-muted ml-auto">{rejectedTasks.length}</span>
              </div>
              <div className="space-y-2">
                {rejectedTasks.map((task: any) => (
                  <div key={task.id} className="theme-card border-l-4 border-l-red-500 opacity-60">
                    <div className="text-sm font-medium text-court-text mb-1">{task.title || '旨意'}</div>
                    <div className="text-[10px] font-mono text-court-muted">{task.trace_id}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {tasks.length === 0 ? (
            <div className="text-center py-16 text-court-muted">
              <LayoutDashboard size={48} className="mx-auto mb-3 opacity-30" />
              <p>暂无旨意记录</p>
            </div>
          ) : (
            tasks.map((task: any) => {
              const info = STATE_INFO[task.state] || { label: task.state, color: 'border-l-gray-500' };
              return (
                <div key={task.id} className={`theme-card border-l-4 ${info.color}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-court-text">{task.title || '旨意'}</div>
                      <div className="text-[10px] font-mono text-court-muted mt-0.5">{task.trace_id}</div>
                    </div>
                    <span className="status-badge bg-court-panel2 text-court-muted text-[10px]">{info.label}</span>
                  </div>
                  {task.description && (
                    <p className="text-xs text-court-muted mt-2 line-clamp-2">{task.description}</p>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
