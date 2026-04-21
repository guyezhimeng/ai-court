import { create } from 'zustand';
import { api } from './api';

export type TabKey = 'chat' | 'board' | 'monitor' | 'officials' | 'memorials' | 'news' | 'settings' | 'regime';

export type RegimeKey = 'tang-sansheng' | 'ming-neige' | 'modern-ceo';

export const REGIME_INFO: Record<RegimeKey, { name: string; desc: string; icon: string }> = {
  'tang-sansheng': { name: '唐朝三省制', desc: '中书省拟旨 → 门下省审核 → 尚书省执行 → 六部落实', icon: '🏛️' },
  'ming-neige': { name: '明朝内阁制', desc: '司礼监批红 → 内阁票拟 → 都察院监察 → 六部执行', icon: '🏯' },
  'modern-ceo': { name: '现代企业制', desc: 'CEO决策 → COO协调 → CTO/CFO/CMO执行 → 部门落实', icon: '🏢' },
};

interface AppState {
  currentRegime: RegimeKey;
  setRegime: (regime: RegimeKey) => void;

  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;

  sessions: any[];
  loadSessions: () => Promise<void>;

  messages: any[];
  loadMessages: (sessionId: string) => Promise<void>;
  addMessage: (msg: any) => void;
  updateLastAgentMessage: (content: string) => void;

  tasks: any[];
  taskSummary: any;
  loadTasks: () => Promise<void>;

  agents: any[];
  loadAgents: () => Promise<void>;

  ws: WebSocket | null;
  connectWs: () => void;
  disconnectWs: () => void;

  sidebarOpen: boolean;
  toggleSidebar: () => void;
}

export const useStore = create<AppState>((set, get) => ({
  currentRegime: 'tang-sansheng',
  setRegime: (regime) => set({ currentRegime: regime }),

  currentSessionId: null,
  setCurrentSessionId: (id) => set({ currentSessionId: id }),

  sessions: [],
  loadSessions: async () => {
    try {
      const sessions = await api.chat.listSessions();
      set({ sessions });
    } catch (e) {
      console.error('Failed to load sessions:', e);
    }
  },

  messages: [],
  loadMessages: async (sessionId) => {
    try {
      const messages = await api.chat.history(sessionId);
      set({ messages });
    } catch (e) {
      console.error('Failed to load messages:', e);
    }
  },
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateLastAgentMessage: (content) => set((s) => {
    const msgs = [...s.messages];
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'agent') {
        msgs[i] = { ...msgs[i], content, _streaming: false };
        break;
      }
    }
    return { messages: msgs };
  }),

  tasks: [],
  taskSummary: null,
  loadTasks: async () => {
    try {
      const [tasks, summary] = await Promise.all([api.tasks.list(), api.tasks.summary()]);
      set({ tasks, taskSummary: summary });
    } catch (e) {
      console.error('Failed to load tasks:', e);
    }
  },

  agents: [],
  loadAgents: async () => {
    try {
      const agents = await api.agents.list();
      set({ agents });
    } catch (e) {
      console.error('Failed to load agents:', e);
    }
  },

  ws: null,
  connectWs: () => {
    const existing = get().ws;
    if (existing && existing.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    let retryCount = 0;

    ws.onopen = () => {
      retryCount = 0;
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);

        if (data.type === 'task_progress') {
          set((s) => ({
            tasks: s.tasks.map(t =>
              t.id === data.task_id
                ? { ...t, state: data.new_state, last_progress: data.response }
                : t
            ),
          }));
        }

        if (data.type === 'chat.message' || data.event_type === 'message.created') {
          get().addMessage(data.payload || data);
        }
      } catch (e) {
        console.error('WS message parse error:', e);
      }
    };

    ws.onclose = () => {
      const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
      retryCount++;
      console.warn(`WebSocket closed, retrying in ${delay}ms (attempt ${retryCount})`);
      setTimeout(() => get().connectWs(), delay);
    };

    set({ ws });
  },
  disconnectWs: () => {
    const ws = get().ws;
    if (ws) {
      ws.onclose = null;
      ws.close();
      set({ ws: null });
    }
  },

  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}));
