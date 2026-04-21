import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useStore } from './store';
import { Sidebar } from './components/layout/Sidebar';
import { ChatPanel } from './components/chat/ChatPanel';
import { EdictBoard } from './components/board/EdictBoard';
import { MonitorPanel } from './components/monitor/MonitorPanel';
import { OfficialsPanel } from './components/officials/OfficialsPanel';
import { MemorialsPanel } from './components/memorials/MemorialsPanel';
import { NewsPanel } from './components/news/NewsPanel';
import { SettingsPanel } from './components/settings/SettingsPanel';
import { RegimePanel } from './components/regime/RegimePanel';

function AppLayout() {
  const { connectWs, disconnectWs } = useStore();

  useEffect(() => {
    connectWs();
    return () => disconnectWs();
  }, []);

  return (
    <div className="flex h-screen bg-court-bg text-court-text font-sans overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-hidden animate-slideIn">
        <Routes>
          <Route path="/" element={<ChatPanel />} />
          <Route path="/chat" element={<ChatPanel />} />
          <Route path="/board" element={<EdictBoard />} />
          <Route path="/monitor" element={<MonitorPanel />} />
          <Route path="/officials" element={<OfficialsPanel />} />
          <Route path="/memorials" element={<MemorialsPanel />} />
          <Route path="/news" element={<NewsPanel />} />
          <Route path="/settings" element={<SettingsPanel />} />
          <Route path="/regime" element={<RegimePanel />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
