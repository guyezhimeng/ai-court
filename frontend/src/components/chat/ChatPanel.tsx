import { useState, useRef, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Send, Paperclip, Image, X, Upload } from 'lucide-react';
import { api } from '@/api';
import { useStore } from '@/store';

export function ChatPanel() {
  const { currentSessionId, messages, addMessage, loadMessages } = useStore();
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const onDrop = useCallback((accepted: File[]) => {
    setFiles((prev) => [...prev, ...accepted]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    noClick: true,
    multiple: true,
    maxSize: 20 * 1024 * 1024,
  });

  const handleSend = async () => {
    if (!input.trim() && files.length === 0) return;
    if (!currentSessionId) return;

    setSending(true);
    try {
      let attachmentIds: string[] = [];

      if (files.length > 0) {
        setUploading(true);
        for (const file of files) {
          try {
            const result = await api.upload.upload(file);
            attachmentIds.push(result.id);
          } catch (e) {
            console.error('Upload failed:', e);
          }
        }
        setUploading(false);
        setFiles([]);
      }

      const result = await api.chat.send(currentSessionId, input, attachmentIds);
      addMessage({
        role: 'user',
        content: input,
        msg_type: 'text',
        created_at: new Date().toISOString(),
      });

      if (result.type === 'chat') {
        addMessage({
          role: 'agent',
          agent_id: 'taizi',
          content: result.content,
          msg_type: 'text',
          created_at: new Date().toISOString(),
        });
      } else if (result.type === 'decree') {
        addMessage({
          role: 'system',
          content: result.info,
          msg_type: 'task_update',
          created_at: new Date().toISOString(),
        });
      }

      setInput('');
      setTimeout(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight), 100);
    } catch (e) {
      console.error('Send failed:', e);
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
    <div className="flex flex-col h-full" {...getRootProps()}>
      <input {...getInputProps()} />

      {isDragActive && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-court-bg/80 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3 text-court-acc">
            <Upload size={48} />
            <p className="text-lg font-medium">拖放文件到此处上传</p>
          </div>
        </div>
      )}

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-court-muted gap-3">
            <div className="text-4xl">🏛️</div>
            <p className="text-lg font-serif">欢迎来到御书房</p>
            <p className="text-sm">输入消息与朝廷对话，或下旨分配任务</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : msg.role === 'system' ? 'justify-center' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="chat-bubble-user">
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            ) : msg.role === 'system' ? (
              <div className="chat-bubble-system">
                <span>{msg.content}</span>
              </div>
            ) : (
              <div className="flex gap-2 items-start">
                <div className="w-7 h-7 rounded-full bg-court-acc2/20 flex items-center justify-center text-xs shrink-0">
                  {msg.agent_id === 'taizi' ? '🤴' : msg.agent_id === 'zhongshu' ? '📜' : msg.agent_id === 'menxia' ? '🔍' : '⚙️'}
                </div>
                <div className="chat-bubble-agent">
                  <p className="text-xs text-court-acc2 mb-1 font-medium">
                    {msg.agent_id || '系统'}
                  </p>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
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
              {f.type.startsWith('image/') ? <Image size={14} /> : <Paperclip size={14} />}
              <span className="max-w-[120px] truncate">{f.name}</span>
              <span className="text-court-muted">({(f.size / 1024).toFixed(0)}KB)</span>
              <button onClick={() => removeFile(i)} className="text-court-muted hover:text-court-danger">
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="p-4 border-t border-court-line">
        <div className="flex items-end gap-2 bg-court-panel2 rounded-xl border border-court-line p-2">
          <label className="p-2 rounded-lg hover:bg-court-line cursor-pointer text-court-muted hover:text-court-text transition-colors">
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
            className="p-2 rounded-lg bg-court-acc text-white hover:bg-court-acc/80 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
