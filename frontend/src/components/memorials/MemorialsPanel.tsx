import { useEffect, useState } from 'react';
import { ScrollText, Search, Filter, Clock, User, Bot, RefreshCw } from 'lucide-react';
import { api } from '@/api';

interface MemorialMessage {
  id: string;
  session_id: string;
  role: string;
  agent_id: string | null;
  content: string;
  msg_type: string;
  metadata: any;
  created_at: string;
}

export function MemorialsPanel() {
  const [messages, setMessages] = useState<MemorialMessage[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [sessionMessages, setSessionMessages] = useState<MemorialMessage[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const sess = await api.chat.listSessions();
      setSessions(sess);
      const allMsgs: MemorialMessage[] = [];
      for (const s of sess.slice(0, 10)) {
        try {
          const msgs = await api.chat.history(s.id, 20);
          allMsgs.push(...msgs);
        } catch {}
      }
      allMsgs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setMessages(allMsgs);
    } catch {} finally {
      setLoading(false);
    }
  };

  const loadSessionDetail = async (sessionId: string) => {
    if (selectedSession === sessionId) {
      setSelectedSession(null);
      return;
    }
    setSelectedSession(sessionId);
    try {
      const msgs = await api.chat.history(sessionId, 100);
      setSessionMessages(msgs);
    } catch {}
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredMessages = messages.filter((m) => {
    if (filter === 'decree' && m.msg_type !== 'task_update') return false;
    if (filter === 'chat' && m.msg_type === 'task_update') return false;
    if (search && !m.content.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const decreeCount = messages.filter((m) => m.msg_type === 'task_update').length;
  const chatCount = messages.filter((m) => m.msg_type !== 'task_update').length;

  const relTime = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return '刚刚';
    if (mins < 60) return `${mins}分钟前`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}小时前`;
    return `${Math.floor(hours / 24)}天前`;
  };

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 lg:p-8 max-w-5xl mx-auto animate-fadeIn">
      <div className="flex items-center justify-between mb-6">
        <h2 className="section-title text-xl mb-0">
          <span className="text-court-acc">📜</span> 奏折阁
        </h2>
        <button onClick={loadData} className="btn-ghost btn-sm flex items-center gap-1.5" disabled={loading}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> 刷新
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
        <div className="stat-card">
          <div className="stat-label">总会话</div>
          <div className="stat-value">{sessions.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">旨意记录</div>
          <div className="stat-value text-court-acc">{decreeCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">对话记录</div>
          <div className="stat-value text-court-info">{chatCount}</div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex gap-1">
          <button onClick={() => setFilter('all')} className={filter === 'all' ? 'filter-btn-active' : 'filter-btn'}>
            全部
          </button>
          <button onClick={() => setFilter('decree')} className={filter === 'decree' ? 'filter-btn-active' : 'filter-btn'}>
            旨意
          </button>
          <button onClick={() => setFilter('chat')} className={filter === 'chat' ? 'filter-btn-active' : 'filter-btn'}>
            对话
          </button>
        </div>
        <div className="flex-1 min-w-[200px] relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-court-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索奏折内容..."
            className="input-field pl-9"
          />
        </div>
      </div>

      {selectedSession && (
        <div className="theme-card-static mb-4 animate-fadeIn">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-court-acc">会话详情</h3>
            <button onClick={() => setSelectedSession(null)} className="text-court-muted hover:text-court-text text-xs">关闭</button>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {sessionMessages.map((msg) => (
              <div key={msg.id} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] px-3 py-2 rounded-lg text-xs ${
                  msg.role === 'user' ? 'bg-court-acc/20 text-court-text' :
                  msg.role === 'system' ? 'bg-court-acc/10 text-court-acc text-center' :
                  'bg-court-panel2 text-court-text'
                }`}>
                  {msg.role !== 'user' && msg.role !== 'system' && (
                    <div className="text-[10px] text-court-acc mb-1">{msg.agent_id || '系统'}</div>
                  )}
                  {msg.content}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        {filteredMessages.length === 0 ? (
          <div className="text-center py-16 text-court-muted">
            <ScrollText size={48} className="mx-auto mb-3 opacity-30" />
            <p>暂无奏折记录</p>
          </div>
        ) : (
          filteredMessages.slice(0, 50).map((msg) => (
            <div key={msg.id} className="theme-card cursor-pointer" onClick={() => loadSessionDetail(msg.session_id)}>
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  {msg.role === 'user' ? <User size={14} className="text-court-acc" /> :
                   msg.role === 'system' ? <ScrollText size={14} className="text-court-warn" /> :
                   <Bot size={14} className="text-court-info" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-court-text">
                      {msg.role === 'user' ? '皇上' :
                       msg.role === 'system' ? '系统' :
                       msg.agent_id || '官员'}
                    </span>
                    {msg.msg_type === 'task_update' && (
                      <span className="status-badge bg-court-acc/20 text-court-acc text-[10px]">旨意</span>
                    )}
                    <span className="text-[10px] text-court-muted ml-auto">{relTime(msg.created_at)}</span>
                  </div>
                  <p className="text-sm text-court-muted line-clamp-2">{msg.content}</p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
