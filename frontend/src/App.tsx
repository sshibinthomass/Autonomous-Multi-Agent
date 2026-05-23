import { useState, useEffect, useRef } from 'react';
import './App.css';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface ProviderInfo {
  models: string[];
}

interface SettingsResponse {
  providers: {
    [key: string]: ProviderInfo;
  };
}

function App() {
  // Thread session state
  const [threadId, setThreadId] = useState<string>(() => {
    let tid = sessionStorage.getItem('agent_thread_id');
    if (!tid) {
      tid = `thread-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
      sessionStorage.setItem('agent_thread_id', tid);
    }
    return tid;
  });

  // Chat state
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', content: 'You are a helpful and efficient assistant.' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Settings & LLM selection state
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({});
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedModel, setSelectedModel] = useState('gpt-4o-mini');

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Fetch backend settings on mount
  useEffect(() => {
    fetchSettings();
  }, []);

  // Fetch existing chat history from backend
  const fetchHistory = async (provider: string, model: string, tid: string) => {
    if (!provider || !model || !tid) return;
    try {
      const response = await fetch(`http://127.0.0.1:8080/api/chat/${tid}/history?provider=${provider}&model=${model}`);
      if (!response.ok) throw new Error('Failed to load history');
      const data: Message[] = await response.json();
      setMessages(data);
    } catch (err: any) {
      console.error('Error fetching chat history:', err);
    }
  };

  // Sync history whenever model or thread changes
  useEffect(() => {
    fetchHistory(selectedProvider, selectedModel, threadId);
  }, [selectedModel, threadId]);

  // Fetch settings from FastAPI
  const fetchSettings = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8080/api/settings');
      if (!response.ok) throw new Error('Failed to load settings');
      const data: SettingsResponse = await response.json();
      setProviders(data.providers);

      // Pick the first provider as default
      const availableProviders = Object.keys(data.providers);
      if (availableProviders.length > 0) {
        const active = availableProviders[0];
        setSelectedProvider(active);
        setSelectedModel(data.providers[active].models[0] || '');
      }
    } catch (err: any) {
      console.error('Error fetching settings:', err);
      setErrorMsg('Could not connect to FastAPI server. Make sure the backend is running on port 8080.');
    }
  };

  // Update selected model when provider changes
  useEffect(() => {
    if (providers[selectedProvider]) {
      setSelectedModel(providers[selectedProvider].models[0] || '');
    }
  }, [selectedProvider, providers]);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Send message handler
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    setErrorMsg(null);
    const userMessage: Message = { role: 'user', content: inputValue.trim() };
    
    // Optimistically update the local chat for responsiveness
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8080/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          thread_id: threadId,
          messages: [userMessage], // Send only the new user message
          provider: selectedProvider,
          model: selectedModel,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to get agent response');
      }

      const updatedHistory: Message[] = await response.json();
      setMessages(updatedHistory);
    } catch (err: any) {
      console.error('Chat error:', err);
      setErrorMsg(err.message || 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  // Clear chat history
  const handleClearHistory = async () => {
    setErrorMsg(null);
    try {
      const response = await fetch(`http://127.0.0.1:8080/api/chat/${threadId}/clear`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to clear session on backend');
      
      // Start a fresh thread
      const newTid = `thread-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
      sessionStorage.setItem('agent_thread_id', newTid);
      setThreadId(newTid);
      setMessages([{ role: 'system', content: 'You are a helpful and efficient assistant.' }]);
    } catch (err: any) {
      console.error('Error clearing history:', err);
      setErrorMsg('Could not reset history on backend. Local chat has been reset.');
      setMessages([{ role: 'system', content: 'You are a helpful and efficient assistant.' }]);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar / Settings Panel */}
      <aside className="settings-sidebar">
        <div className="sidebar-header">
          <h2>Agent Settings</h2>
          <p className="subtitle">Configure your language model</p>
        </div>

        <div className="setting-group">
          <label>Provider</label>
          <select 
            value={selectedProvider} 
            onChange={(e) => setSelectedProvider(e.target.value)}
          >
            {Object.keys(providers).map(p => (
              <option key={p} value={p}>
                {p.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <div className="setting-group">
          <label>Model</label>
          <select 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            {providers[selectedProvider]?.models.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div className="sidebar-footer">
          <button className="clear-btn" onClick={handleClearHistory}>
            Reset Chat History
          </button>
        </div>
      </aside>

      {/* Main Chat Interface */}
      <main className="chat-main">
        <header className="chat-header">
          <h1>Autonomous Agent Playground</h1>
          <div className="status-indicator">
            <span className="dot active"></span>
            Active Model: <strong style={{ marginLeft: '4px' }}>{selectedProvider.toUpperCase()} / {selectedModel}</strong>
          </div>
        </header>

        {/* Error banner */}
        {errorMsg && (
          <div className="error-banner">
            <span>{errorMsg}</span>
            <button className="close-error" onClick={() => setErrorMsg(null)}>×</button>
          </div>
        )}

        {/* Chat message history container */}
        <div className="messages-container">
          {messages.map((msg, index) => {
            if (msg.role === 'system') {
              return (
                <div key={index} className="system-msg-wrapper">
                  <span className="system-badge">System Prompt</span>
                  <div className="system-msg">{msg.content}</div>
                </div>
              );
            }
            return (
              <div 
                key={index} 
                className={`message-row ${msg.role === 'user' ? 'user-row' : 'bot-row'}`}
              >
                <div className="avatar">
                  {msg.role === 'user' ? 'U' : 'AI'}
                </div>
                <div className="message-bubble">
                  {msg.content}
                </div>
              </div>
            );
          })}
          
          {/* Loading Indicator */}
          {isLoading && (
            <div className="message-row bot-row">
              <div className="avatar">AI</div>
              <div className="message-bubble loading-bubble">
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={chatEndRef} />
        </div>

        {/* Message Input Box */}
        <footer className="chat-input-footer">
          <form onSubmit={handleSendMessage} className="input-form">
            <input
              type="text"
              placeholder={`Send a message to the ${selectedModel} assistant...`}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={isLoading}
            />
            <button type="submit" disabled={!inputValue.trim() || isLoading}>
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </form>
        </footer>
      </main>
    </div>
  );
}

export default App;
