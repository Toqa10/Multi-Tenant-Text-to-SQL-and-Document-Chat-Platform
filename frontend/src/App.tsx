import React, { useState, useRef, useEffect } from 'react';
import { Database, FileText, Settings, Send, Bot, User, Menu, Plus, Server } from 'lucide-react';
import './App.css';

interface Message {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: Date;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'ai',
      content: 'Hello! I am your AI assistant for Text-to-SQL and Document Chat. How can I help you today?',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isDbModalOpen, setIsDbModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Simulate API call to backend
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: `I received your query: "${userMessage.content}". This is a placeholder response from the frontend UI. The backend integration can be configured in api.ts.`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="gradient-text font-bold">
            <Bot size={28} color="var(--accent-primary)" />
            AI Platform
          </h1>
        </div>
        
        <div className="sidebar-content">
          <button className="btn btn-primary w-full justify-center">
            <Plus size={18} />
            New Chat
          </button>
          
          <div className="flex-col gap-2">
            <h3 className="text-xs font-bold text-muted" style={{textTransform: 'uppercase', marginBottom: '8px', color: 'var(--text-muted)'}}>Data Sources</h3>
            <button 
              className="btn btn-ghost w-full" style={{justifyContent: 'flex-start'}}
              onClick={() => setIsDbModalOpen(true)}
            >
              <Database size={18} />
              Connect Database
            </button>
            <button className="btn btn-ghost w-full" style={{justifyContent: 'flex-start'}}>
              <FileText size={18} />
              Upload Documents
            </button>
          </div>
          
          <div style={{marginTop: 'auto'}}>
            <button className="btn btn-ghost w-full" style={{justifyContent: 'flex-start'}}>
              <Settings size={18} />
              Settings
            </button>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="main-content">
        <div className="chat-container">
          <div className="chat-history">
            {messages.map((msg) => (
              <div key={msg.id} className={`message-wrapper ${msg.role}`}>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start'}}>
                  {msg.role === 'user' ? (
                    <>
                      <span className="text-xs text-muted">You</span>
                      <User size={14} color="var(--accent-primary)" />
                    </>
                  ) : (
                    <>
                      <Bot size={14} color="var(--accent-secondary)" />
                      <span className="text-xs text-muted">AI Assistant</span>
                    </>
                  )}
                </div>
                <div className="message-bubble">
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message-wrapper ai">
                <div className="message-bubble animate-pulse-glow" style={{display: 'flex', gap: '4px', alignItems: 'center', padding: '16px'}}>
                  <div style={{width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-primary)', animation: 'bounce 1.4s infinite ease-in-out both'}} />
                  <div style={{width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-primary)', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.2s'}} />
                  <div style={{width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-primary)', animation: 'bounce 1.4s infinite ease-in-out both', animationDelay: '0.4s'}} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="chat-input-container" onSubmit={handleSend}>
            <textarea
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your database or documents..."
              rows={1}
            />
            <button 
              type="submit" 
              className="send-button"
              disabled={!input.trim() || isLoading}
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </main>

      {/* Database Connection Modal */}
      {isDbModalOpen && (
        <div className="modal-overlay" onClick={() => setIsDbModalOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setIsDbModalOpen(false)}>✕</button>
            <h2 className="gradient-text font-bold" style={{fontSize: '1.5rem', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px'}}>
              <Server size={24} />
              Connect Database
            </h2>
            
            <form onSubmit={e => { e.preventDefault(); setIsDbModalOpen(false); }}>
              <div className="form-group">
                <label>Connection Name</label>
                <input type="text" className="input-field" placeholder="e.g. Production PostgreSQL" required />
              </div>
              
              <div className="form-group">
                <label>Database Type</label>
                <select className="input-field" required>
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="sqlserver">SQL Server</option>
                  <option value="oracle">Oracle</option>
                </select>
              </div>

              <div style={{display: 'flex', gap: '16px'}}>
                <div className="form-group" style={{flex: 2}}>
                  <label>Host</label>
                  <input type="text" className="input-field" placeholder="localhost" required />
                </div>
                <div className="form-group" style={{flex: 1}}>
                  <label>Port</label>
                  <input type="number" className="input-field" placeholder="5432" required />
                </div>
              </div>

              <div className="form-group">
                <label>Database Name</label>
                <input type="text" className="input-field" placeholder="postgres" required />
              </div>

              <div style={{display: 'flex', gap: '16px'}}>
                <div className="form-group" style={{flex: 1}}>
                  <label>Username</label>
                  <input type="text" className="input-field" required />
                </div>
                <div className="form-group" style={{flex: 1}}>
                  <label>Password</label>
                  <input type="password" className="input-field" required />
                </div>
              </div>

              <div style={{display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '32px'}}>
                <button type="button" className="btn btn-ghost" onClick={() => setIsDbModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Connect & Sync Schema</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
