import { useEffect } from 'react';
import { useStore, TabKey } from './store';
import { Sidebar } from './components/layout/Sidebar';
import { ChatPanel } from './components/chat/ChatPanel';
import { EdictBoard } from './components/board/EdictBoard';
import { api } from './api';

function Topbar() {
  const { activeTab } = useStore();

  const titles: Record<TabKey, string> = {
    chat: '御书房',
    board: '旨意看板',
    monitor: '省部调度',
    officials: '官员总览',
    memorials: '奏折阁',
    news: '天下要闻',
    settings: '配置中心',
    regime: '制度切换',
  };

  return (
    <header className="h-14 flex items-center justify-between px-6 border-b border-court-line bg-court-panel/50 backdrop-blur-sm">
      <h2 className="text-base font-serif font-bold text-court-text">{titles[activeTab]}</h2>
      <div className="flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-court-ok animate-pulse" />
        <span className="text-xs text-court-muted">系统运行中</span>
      </div>
    </header>
  );
}

function PlaceholderPage({ name }: { name: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-court-muted gap-3">
      <div className="text-4xl">🚧</div>
      <p className="text-lg font-serif">{name}</p>
      <p className="text-sm">功能开发中...</p>
    </div>
  );
}

function SessionSelector() {
  const { sessions, currentSessionId, setCurrentSessionId, loadMessages, loadSessions } = useStore();

  useEffect(() => {
    loadSessions();
  }, []);

  const handleNewSession = async () => {
    try {
      const session = await api.chat.createSession();
      await loadSessions();
      setCurrentSessionId(session.id);
      loadMessages(session.id);
    } catch (e) {
      console.error('Create session failed:', e);
    }
  };

  const handleSelectSession = (id: string) => {
    setCurrentSessionId(id);
    loadMessages(id);
  };

  return (
    <div className="p-3 border-b border-court-line">
      <button
        onClick={handleNewSession}
        className="w-full court-btn-primary text-center"
      >
        新建会话
      </button>
      <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
        {sessions.map((s: any) => (
          <button
            key={s.id}
            onClick={() => handleSelectSession(s.id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
              currentSessionId === s.id
                ? 'bg-court-acc/15 text-court-acc'
                : 'text-court-muted hover:bg-court-panel2 hover:text-court-text'
            }`}
          >
            <p className="truncate">{s.title || '新会话'}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

function MainContent() {
  const { activeTab, currentSessionId } = useStore();

  switch (activeTab) {
    case 'chat':
      return currentSessionId ? (
        <ChatPanel />
      ) : (
        <div className="flex flex-col items-center justify-center h-full text-court-muted gap-4">
          <div className="text-5xl">🏛️</div>
          <p className="text-xl font-serif">欢迎来到御书房</p>
          <p className="text-sm">创建或选择一个会话开始对话</p>
        </div>
      );
    case 'board':
      return <EdictBoard />;
    case 'monitor':
      return <PlaceholderPage name="省部调度" />;
    case 'officials':
      return <PlaceholderPage name="官员总览" />;
    case 'memorials':
      return <PlaceholderPage name="奏折阁" />;
    case 'news':
      return <PlaceholderPage name="天下要闻" />;
    case 'settings':
      return <PlaceholderPage name="配置中心" />;
    case 'regime':
      return <PlaceholderPage name="制度切换" />;
    default:
      return null;
  }
}

export default function App() {
  const { connectWs, disconnectWs, setCurrentSessionId, loadMessages, loadSessions } = useStore();

  useEffect(() => {
    connectWs();
    loadSessions().then(() => {
      const sessions = useStore.getState().sessions;
      if (sessions.length > 0) {
        const latest = sessions[0];
        setCurrentSessionId(latest.id);
        loadMessages(latest.id);
      }
    });
    return () => disconnectWs();
  }, []);

  return (
    <div className="flex h-screen bg-court-bg overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <div className="flex-1 flex min-h-0">
          <div className="flex-1 min-w-0">
            <MainContent />
          </div>
          {useStore.getState().activeTab === 'chat' && (
            <div className="w-56 border-l border-court-line bg-court-panel hidden lg:block">
              <SessionSelector />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
