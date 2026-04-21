import { cn } from '@/lib/utils';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  MessageSquare, LayoutDashboard, Activity, Users,
  ScrollText, Newspaper, Settings, RefreshCw, PanelLeftClose, PanelLeft,
} from 'lucide-react';
import { useStore } from '@/store';

const TAB_ROUTES: Record<string, string> = {
  chat: '/',
  board: '/board',
  monitor: '/monitor',
  officials: '/officials',
  memorials: '/memorials',
  news: '/news',
  settings: '/settings',
  regime: '/regime',
};

const navItems = [
  { key: 'chat', label: '御书房', icon: MessageSquare },
  { key: 'board', label: '旨意看板', icon: LayoutDashboard },
  { key: 'monitor', label: '省部调度', icon: Activity },
  { key: 'officials', label: '官员总览', icon: Users },
  { key: 'memorials', label: '奏折阁', icon: ScrollText },
  { key: 'news', label: '天下要闻', icon: Newspaper },
  { key: 'settings', label: '配置中心', icon: Settings },
  { key: 'regime', label: '制度切换', icon: RefreshCw },
];

export function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useStore();
  const navigate = useNavigate();
  const location = useLocation();

  const activeTab = Object.entries(TAB_ROUTES).find(
    ([_, path]) => location.pathname === path
  )?.[0] || 'chat';

  return (
    <aside
      className={cn(
        'flex flex-col h-screen bg-court-sidebar border-r border-court-line transition-all duration-300',
        sidebarOpen ? 'w-56' : 'w-16'
      )}
    >
      <div className="flex items-center justify-between h-14 px-3 border-b border-court-line">
        {sidebarOpen && (
          <h1 className="text-base font-serif font-bold text-court-acc tracking-wide">
            AI 朝廷
          </h1>
        )}
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg hover:bg-court-panel2 text-court-muted hover:text-court-text transition-colors"
        >
          {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
        </button>
      </div>

      <nav className="flex-1 py-2 space-y-0.5 px-2">
        {navItems.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => navigate(TAB_ROUTES[key])}
            className={cn(
              'flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm transition-all duration-200',
              activeTab === key
                ? 'bg-court-acc/15 text-court-acc font-medium accent-border-left'
                : 'text-court-muted hover:text-court-text hover:bg-court-panel2'
            )}
          >
            <Icon size={18} className="shrink-0" />
            {sidebarOpen && <span>{label}</span>}
          </button>
        ))}
      </nav>

      <div className="p-3 border-t border-court-line">
        {sidebarOpen && (
          <div className="text-xs text-court-muted text-center">
            三省六部 v3.0
          </div>
        )}
      </div>
    </aside>
  );
}
