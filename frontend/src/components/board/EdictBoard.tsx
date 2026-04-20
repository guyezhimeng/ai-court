import { useEffect } from 'react';
import { useStore } from '@/store';
import { api } from '@/api';

const STATE_COLORS: Record<string, string> = {
  Taizi: 'bg-blue-500/20 text-blue-400',
  Zhongshu: 'bg-purple-500/20 text-purple-400',
  Menxia: 'bg-amber-500/20 text-amber-400',
  Assigned: 'bg-cyan-500/20 text-cyan-400',
  Doing: 'bg-green-500/20 text-green-400',
  Review: 'bg-teal-500/20 text-teal-400',
  Done: 'bg-court-ok/20 text-court-ok',
  Blocked: 'bg-red-500/20 text-red-400',
  Cancelled: 'bg-gray-500/20 text-gray-400',
};

const STATE_LABELS: Record<string, string> = {
  Taizi: '太子分拣',
  Zhongshu: '中书起草',
  Menxia: '门下审议',
  Assigned: '尚书派发',
  Doing: '六部执行',
  Review: '审查汇总',
  Done: '已完成',
  Blocked: '已阻塞',
  Cancelled: '已取消',
};

const PIPE = [
  { key: 'Taizi', label: '太子', icon: '🤴' },
  { key: 'Zhongshu', label: '中书省', icon: '📜' },
  { key: 'Menxia', label: '门下省', icon: '🔍' },
  { key: 'Assigned', label: '尚书省', icon: '📮' },
  { key: 'Doing', label: '六部', icon: '⚙️' },
  { key: 'Review', label: '汇总', icon: '🔎' },
  { key: 'Done', label: '完成', icon: '✅' },
];

function MiniPipe({ currentState }: { currentState: string }) {
  const stateOrder = ['Taizi', 'Zhongshu', 'Menxia', 'Assigned', 'Doing', 'Review', 'Done'];
  const currentIdx = stateOrder.indexOf(currentState);

  return (
    <div className="flex items-center gap-1">
      {PIPE.map((step, i) => {
        const isActive = step.key === currentState;
        const isDone = i < currentIdx;
        return (
          <div key={step.key} className="flex items-center gap-1">
            <div
              className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] transition-all ${
                isActive ? 'bg-court-acc text-white scale-110' : isDone ? 'bg-court-ok/30 text-court-ok' : 'bg-court-line text-court-muted'
              }`}
            >
              {isDone ? '✓' : step.icon}
            </div>
            {i < PIPE.length - 1 && (
              <div className={`w-3 h-0.5 ${isDone ? 'bg-court-ok/50' : 'bg-court-line'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function EdictBoard() {
  const { tasks, loadTasks } = useStore();

  useEffect(() => {
    loadTasks();
    const timer = setInterval(loadTasks, 5000);
    return () => clearInterval(timer);
  }, []);

  const activeTasks = tasks.filter((t: any) => !t.is_archived && t.state !== 'Done' && t.state !== 'Cancelled');
  const doneTasks = tasks.filter((t: any) => t.state === 'Done' || t.state === 'Cancelled');

  return (
    <div className="p-4 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-serif font-bold text-court-warn">旨意看板</h2>
        <div className="flex gap-2">
          <span className="court-badge bg-court-acc/15 text-court-acc">
            活跃 {activeTasks.length}
          </span>
          <span className="court-badge bg-court-ok/15 text-court-ok">
            完成 {doneTasks.length}
          </span>
        </div>
      </div>

      {activeTasks.length === 0 && (
        <div className="court-card flex flex-col items-center justify-center py-12 text-court-muted">
          <div className="text-3xl mb-3">📋</div>
          <p>暂无活跃旨意</p>
          <p className="text-xs mt-1">在御书房下旨来创建任务</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {activeTasks.map((task: any) => (
          <div key={task.id} className="court-card space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-xs text-court-muted font-mono">{task.trace_id}</p>
                <p className="text-sm font-medium truncate mt-0.5">{task.title}</p>
              </div>
              <span className={`court-badge shrink-0 ${STATE_COLORS[task.state] || ''}`}>
                {STATE_LABELS[task.state] || task.state}
              </span>
            </div>

            <MiniPipe currentState={task.state} />

            {task.now_summary && (
              <p className="text-xs text-court-muted line-clamp-2">{task.now_summary}</p>
            )}

            {task.subtasks && task.subtasks.length > 0 && (
              <div className="space-y-1">
                {task.subtasks.slice(0, 3).map((st: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div className={`w-1.5 h-1.5 rounded-full ${st.done ? 'bg-court-ok' : 'bg-court-muted'}`} />
                    <span className={st.done ? 'line-through text-court-muted' : ''}>{st.title || st.name}</span>
                  </div>
                ))}
                {task.subtasks.length > 3 && (
                  <p className="text-xs text-court-muted">+{task.subtasks.length - 3} 更多</p>
                )}
              </div>
            )}

            <div className="flex items-center justify-between text-xs text-court-muted pt-2 border-t border-court-line">
              <span>{new Date(task.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
              {task.department && <span>{task.department}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
