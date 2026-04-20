import { create } from 'zustand';
import { api } from './api';

export type TabKey = 'chat' | 'board' | 'monitor' | 'officials' | 'memorials' | 'news' | 'settings' | 'regime';

interface AppState {
  activeTab: TabKey;
  setActiveTab: (tab: TabKey) => void;

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
  activeTab: 'chat',
  setActiveTab: (tab) => {
    set({ activeTab: tab });
    const s = get();
    if (tab === 'board' && s.tasks.length === 0) s.loadTasks();
    if (tab === 'settings' && s.agents.length === 0) s.loadAgents();
  },

  currentSessionId: null,
  setCurrentSessionId: (id) => set({ currentSessionId: id }),

  sessions: [],
  loadSessions: async () => {
    try {
      const sessions = await api.chat.listSessions();
      set({ sessions });
    } catch {}
  },

  messages: [],
  loadMessages: async (sessionId) => {
    try {
      const messages = await api.chat.history(sessionId);
      set({ messages });
    } catch {}
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
    } catch {}
  },

  agents: [],
  loadAgents: async () => {
    try {
      const agents = await api.agents.list();
      set({ agents });
    } catch {}
  },

  ws: null,
  connectWs: () => {
    const existing = get().ws;
    if (existing && existing.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'chat.message' || data.event_type === 'message.created') {
          get().addMessage(data.payload || data);
        }
      } catch {}
    };

    ws.onclose = () => {
      setTimeout(() => get().connectWs(), 3000);
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
