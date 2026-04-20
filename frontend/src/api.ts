const API_BASE = import.meta.env.VITE_API_URL || '';

async function fetchJ<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API ${res.status}: ${url}`);
  return res.json();
}

async function postJ<T>(url: string, data?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: data ? JSON.stringify(data) : undefined,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${url}`);
  return res.json();
}

export const api = {
  chat: {
    createSession: (userId = 'default_user', regime = 'tang-sansheng') =>
      postJ<{ id: string; title: string; type: string }>(`${API_BASE}/api/chat/sessions`, { user_id: userId, regime }),
    listSessions: (userId = 'default_user') =>
      fetchJ<any[]>(`${API_BASE}/api/chat/sessions?user_id=${userId}`),
    send: (sessionId: string, content: string, attachments?: string[]) =>
      postJ(`${API_BASE}/api/chat/send`, { session_id: sessionId, content, attachments }),
    history: (sessionId: string, limit = 50, before?: string) =>
      fetchJ<any[]>(`${API_BASE}/api/chat/history/${sessionId}?limit=${limit}${before ? `&before=${before}` : ''}`),
    search: (query: string) =>
      postJ(`${API_BASE}/api/chat/search`, { query }),
  },
  upload: {
    upload: async (file: File, messageId?: string) => {
      const form = new FormData();
      form.append('file', file);
      if (messageId) form.append('message_id', messageId);
      const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form });
      if (!res.ok) throw new Error('Upload failed');
      return res.json();
    },
    get: (id: string) => fetchJ<any>(`${API_BASE}/api/upload/${id}`),
  },
  tasks: {
    list: (state?: string, archived = false) =>
      fetchJ<any[]>(`${API_BASE}/api/tasks?${state ? `state=${state}&` : ''}is_archived=${archived}`),
    summary: () => fetchJ<any>(`${API_BASE}/api/tasks/summary`),
    get: (id: string) => fetchJ<any>(`${API_BASE}/api/tasks/${id}`),
    transition: (id: string, newState: string, agentId?: string, comment?: string) =>
      postJ(`${API_BASE}/api/tasks/${id}/transition`, { new_state: newState, agent_id: agentId, comment }),
    archive: (id: string) => postJ(`${API_BASE}/api/tasks/${id}/archive`),
    dispatch: (id: string, agentId: string, message?: string) =>
      postJ(`${API_BASE}/api/tasks/${id}/dispatch`, { agent_id: agentId, message }),
  },
  agents: {
    list: () => fetchJ<any[]>(`${API_BASE}/api/agents`),
    get: (id: string) => fetchJ<any>(`${API_BASE}/api/agents/${id}`),
  },
  health: () => fetchJ<any>(`${API_BASE}/api/health`),
  liveStatus: () => fetchJ<any>(`${API_BASE}/api/live-status`),
};
