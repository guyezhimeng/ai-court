import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { Send, Paperclip, Image, X, Upload, Plus } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { api } from '@/api';
import { useStore } from '@/store';

function TaskProgressBar({ task }: { task: any }) {
  const STEPS = [
    { state: 'Taizi', label: '太子分拣', icon: '🤴' },
    { state: 'Zhongshu', label: '中书拟旨', icon: '📜' },
    { state: 'Menxia', label: '门下审核', icon: '🔍' },
    { state: 'Assigned', label: '尚书分配', icon: '📋' },
    { state: 'Doing', label: '六部执行', icon: '⚙️' },
    { state: 'Review', label: '尚书审核', icon: '✅' },
    { state: 'Done', label: '已完成', icon: '🎉' },
  ];

  const currentIdx = STEPS.findIndex(s => s.state === task.state);

  return (
    <div className="flex items-center gap-1 my-3 p-3 bg-court-panel rounded-xl">
      {STEPS.map((step, i) => (
        <React.Fragment key={step.state}>
          <div className={`flex items-center gap-1 text-[10px] ${
            i <= currentIdx ? 'text-court-acc' : 'text-court-dim'
          }`}>
            <span>{step.icon}</span>
            <span className="hidden sm:inline">{step.label}</span>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`flex-1 h-px ${
              i < currentIdx ? 'bg-court-acc' : 'bg-court-line'
            }`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export function ChatPanel() {
  const {
    currentSessionId, setCurrentSessionId,
    messages, addMessage, updateLastAgentMessage, loadMessages,
    sessions, loadSessions,
  } = useStore();
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [showSessionList, setShowSessionList] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!currentSessionId) {
      api.chat.createSession().then((s) => {
        setCurrentSessionId(s.id);
      }).catch((e) => {
        console.error('Failed to create session:', e);
      });
    } else {
      loadMessages(currentSessionId);
    }
    loadSessions();
  }, [currentSessionId]);

  const onDrop = useCallback((accepted: File[]) => {
    setFiles((prev) => [...prev, ...accepted]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    noClick: true,
    multiple: true,
    maxSize: 20 * 1024 * 1024,
  });

  const scrollToBottom = () => {
    setTimeout(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight), 50);
  };

  const createNewSession = async () => {
    try {
      const s = await api.chat.createSession();
      setCurrentSessionId(s.id);
      loadSessions();
    } catch (e) {
      console.error('Failed to create session:', e);
    }
  };

  const switchSession = (id: string) => {
    setCurrentSessionId(id);
    setShowSessionList(false);
  };

  const handleSend = async () => {
    if (!input.trim() && files.length === 0) return;

    if (!currentSessionId) {
      try {
        const s = await api.chat.createSession();
        setCurrentSessionId(s.id);
      } catch {
        return;
      }
    }

    const sessionId = useStore.getState().currentSessionId;
    if (!sessionId) return;

    setSending(true);
    try {
      let attachmentIds: string[] = [];

      if (files.length > 0) {
        for (const file of files) {
          try {
            const result = await api.upload.upload(file);
            attachmentIds.push(result.id);
          } catch (e) {
            console.error('Upload failed:', e);
          }
        }
        setFiles([]);
      }

      addMessage({
        role: 'user',
        content: input,
        msg_type: 'text',
        created_at: new Date().toISOString(),
      });

      const userContent = input;
      setInput('');
      scrollToBottom();

      addMessage({
        role: 'agent',
        agent_id: 'taizi',
        content: '',
        msg_type: 'text',
        created_at: new Date().toISOString(),
        _streaming: true,
      });
      setStreaming(true);
      scrollToBottom();

      try {
        let fullContent = '';

        for await (const event of api.chat.sendStream(sessionId, userContent, attachmentIds)) {
          if (event.type === 'chat_start') {
            // stream started
          } else if (event.type === 'chat_chunk' && event.content) {
            fullContent += event.content as string;
            updateLastAgentMessage(fullContent);
            scrollToBottom();
          } else if (event.type === 'chat_end') {
            updateLastAgentMessage(fullContent);
          } else if (event.type === 'decree') {
            updateLastAgentMessage('');
            addMessage({
              role: 'system',
              content: (event.info as string) || '旨意已下达，太子正在分拣...',
              msg_type: 'task_update',
              created_at: new Date().toISOString(),
              task_id: event.task_id,
              state: 'Taizi',
            });
            scrollToBottom();
          }
        }
      } catch (streamErr) {
        console.error('Stream failed, falling back:', streamErr);
        try {
          const result = await api.chat.send(sessionId, userContent, attachmentIds) as any;
          if (result.type === 'chat') {
            updateLastAgentMessage(result.content);
          } else if (result.type === 'decree') {
            updateLastAgentMessage('');
            addMessage({
              role: 'system',
              content: result.info,
              msg_type: 'task_update',
              created_at: new Date().toISOString(),
            });
          }
        } catch (fallbackErr) {
          updateLastAgentMessage('臣暂无法回应，请稍后再试。');
        }
      }

      setStreaming(false);
    } catch (e) {
      console.error('Send failed:', e);
      setStreaming(false);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  return (
    <div className="flex h-full" {...getRootProps()}>
      <input {...getInputProps()} />

      {isDragActive && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-court-bg/80 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3 text-court-acc">
            <Upload size={48} />
            <p className="text-lg font-medium">拖放文件到此处上传</p>
          </div>
        </div>
      )}

      {showSessionList && (
        <div className="w-56 border-r border-court-line overflow-y-auto bg-court-sidebar">
          <div className="p-2">
            <button
              onClick={createNewSession}
              className="flex items-center justify-center gap-1 w-full px-3 py-2 rounded-lg text-xs text-court-acc hover:bg-court-acc/10 transition-colors"
            >
              <Plus size={14} />
              新对话
            </button>
          </div>
          {sessions.map((s: any) => (
            <button
              key={s.id}
              onClick={() => switchSession(s.id)}
              className={`w-full text-left px-3 py-2 text-xs truncate transition-colors ${
                currentSessionId === s.id
                  ? 'bg-court-acc/15 text-court-acc'
                  : 'text-court-muted hover:text-court-text hover:bg-court-panel2'
              }`}
            >
              {s.title || '新对话'}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col flex-1">
        <div className="px-4 py-3 border-b border-court-line flex items-center gap-2">
          <button
            onClick={() => setShowSessionList(!showSessionList)}
            className="p-1.5 rounded-lg hover:bg-court-panel2 text-court-muted hover:text-court-text transition-colors"
          >
            <Paperclip size={16} />
          </button>
          <h2 className="text-sm font-serif font-bold text-court-acc">御书房</h2>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-court-muted gap-3">
              <div className="text-5xl">🏛️</div>
              <p className="text-base font-serif text-court-acc">欢迎来到御书房</p>
              <p className="text-xs">输入消息与朝廷对话，或下旨分配任务</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id || msg.created_at} className={`flex ${msg.role === 'user' ? 'justify-end' : msg.role === 'system' ? 'justify-center' : 'justify-start'} animate-fadeIn`}>
              {msg.role === 'user' ? (
                <div className="chat-bubble-user">
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                </div>
              ) : msg.role === 'system' ? (
                <div className="w-full max-w-lg">
                  <div className="chat-bubble-system">
                    <span className="text-xs">{msg.content}</span>
                  </div>
                  {msg.task_id && msg.state && (
                    <TaskProgressBar task={msg} />
                  )}
                </div>
              ) : (
                <div className="flex gap-2 items-start">
                  <div className="w-7 h-7 rounded-full bg-court-acc/20 flex items-center justify-center text-xs shrink-0">
                    {msg.agent_id === 'taizi' ? '🤴' : msg.agent_id === 'zhongshu' ? '📜' : msg.agent_id === 'menxia' ? '🔍' : '⚙️'}
                  </div>
                  <div className="chat-bubble-agent">
                    <p className="text-[10px] text-court-acc mb-1 font-medium uppercase tracking-wider">
                      {msg.agent_id || '系统'}
                    </p>
                    <div className="prose prose-invert prose-sm max-w-none
                                    prose-headings:text-court-text prose-p:text-court-text
                                    prose-code:text-court-acc prose-pre:bg-court-bg
                                    prose-a:text-court-acc">
                      {msg.content ? (
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      ) : (
                        <span className="text-court-muted text-xs">
                          {msg._streaming && streaming ? '思考中...' : ''}
                        </span>
                      )}
                      {msg._streaming && streaming && msg.content && (
                        <span className="inline-block w-1.5 h-4 bg-court-acc/60 animate-pulse ml-0.5 align-middle" />
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {files.length > 0 && (
          <div className="px-4 py-2 border-t border-court-line flex gap-2 flex-wrap">
            {files.map((f, i) => (
              <div key={i} className="flex items-center gap-1.5 bg-court-panel2 rounded-lg px-2 py-1 text-xs">
                {f.type.startsWith('image/') ? <Image size={14} className="text-court-acc" /> : <Paperclip size={14} className="text-court-muted" />}
                <span className="max-w-[120px] truncate text-court-text">{f.name}</span>
                <span className="text-court-muted">({(f.size / 1024).toFixed(0)}KB)</span>
                <button onClick={() => removeFile(i)} className="text-court-muted hover:text-court-danger">
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="p-4 border-t border-court-line">
          <div className="flex items-end gap-2 bg-court-panel rounded-xl border border-court-line p-2">
            <label className="p-2 rounded-lg hover:bg-court-panel2 cursor-pointer text-court-muted hover:text-court-acc transition-colors">
              <Paperclip size={18} />
              <input
                type="file"
                className="hidden"
                multiple
                onChange={(e) => {
                  const newFiles = Array.from(e.target.files || []);
                  setFiles((prev) => [...prev, ...newFiles]);
                }}
              />
            </label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息或下旨..."
              rows={1}
              className="flex-1 bg-transparent resize-none outline-none text-sm text-court-text placeholder:text-court-muted py-2 max-h-32"
            />
            <button
              onClick={handleSend}
              disabled={sending || (!input.trim() && files.length === 0)}
              className="p-2 rounded-lg bg-gradient-to-r from-court-acc to-court-acc2 text-court-bg hover:shadow-lg hover:shadow-court-acc/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
