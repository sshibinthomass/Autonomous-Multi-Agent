import { useState, useEffect, useRef, useCallback } from 'react';
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
  tones: string[];
}

// Mirrors the backend's PromptConfig (schemas.py)
interface PromptConfig {
  chatbot_name: string;
  tone: string;
}

// ── localStorage helpers ──────────────────────────────────────────────
// Using localStorage (not sessionStorage) so values survive tab close,
// browser restart, and backend restarts.
const STORAGE_KEYS = {
  threadId: 'agent_thread_id',
  provider: 'agent_provider',
  model: 'agent_model',
  promptConfig: 'agent_prompt_config',
} as const;

const DEFAULT_PROMPT_CONFIG: PromptConfig = {
  chatbot_name: 'Jarvis',
  tone: 'friendly',
};

function loadSetting(key: string, fallback: string): string {
  return localStorage.getItem(key) || fallback;
}

function saveSetting(key: string, value: string): void {
  localStorage.setItem(key, value);
}

function loadPromptConfig(): PromptConfig {
  const raw = localStorage.getItem(STORAGE_KEYS.promptConfig);
  if (raw) {
    try {
      return { ...DEFAULT_PROMPT_CONFIG, ...JSON.parse(raw) };
    } catch { /* corrupted JSON, fall through */ }
  }
  return { ...DEFAULT_PROMPT_CONFIG };
}

function savePromptConfig(config: PromptConfig): void {
  localStorage.setItem(STORAGE_KEYS.promptConfig, JSON.stringify(config));
}

function App() {
  // ── Modal Popup Open/Closed state ───────────────────────────────────
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'agent' | 'prompt'>('agent');

  const toggleModal = useCallback(() => {
    setIsModalOpen(prev => !prev);
  }, []);

  // ── Thread session state ────────────────────────────────────────────
  const [threadId, setThreadId] = useState<string>(() => {
    let tid = loadSetting(STORAGE_KEYS.threadId, '');
    if (!tid) {
      tid = `thread-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
      saveSetting(STORAGE_KEYS.threadId, tid);
    }
    return tid;
  });

  // ── Chat state ─────────────────────────────────────────────────────
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', content: 'You are a helpful and efficient assistant.' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // ── Settings & LLM selection state ─────────────────────────────────
  // All values are initialised from localStorage so they survive
  // page refreshes, backend restarts, and tab re-opens.
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({});
  const [availableTones, setAvailableTones] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>(
    () => loadSetting(STORAGE_KEYS.provider, 'openai')
  );
  const [selectedModel, setSelectedModel] = useState<string>(
    () => loadSetting(STORAGE_KEYS.model, 'gpt-4o-mini')
  );

  // Prompt configuration as a single dict — mirrors backend PromptConfig
  const [promptConfig, setPromptConfig] = useState<PromptConfig>(loadPromptConfig);

  // Staging state for prompt configuration
  const [tempPromptConfig, setTempPromptConfig] = useState<PromptConfig>(DEFAULT_PROMPT_CONFIG);
  const [isSavedSuccessfully, setIsSavedSuccessfully] = useState<boolean>(false);

  // Synchronise temporary prompt config when modal opens
  useEffect(() => {
    if (isModalOpen) {
      setTempPromptConfig(promptConfig);
      setIsSavedSuccessfully(false);
    }
  }, [isModalOpen, promptConfig]);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // ── Wrapped setters that always persist to localStorage ────────────
  const updateProvider = useCallback((value: string) => {
    setSelectedProvider(value);
    saveSetting(STORAGE_KEYS.provider, value);
  }, []);

  const updateModel = useCallback((value: string) => {
    setSelectedModel(value);
    saveSetting(STORAGE_KEYS.model, value);
  }, []);

  // Update a single key inside promptConfig while persisting the whole dict
  const updatePromptConfig = useCallback((patch: Partial<PromptConfig>) => {
    setPromptConfig(prev => {
      const next = { ...prev, ...patch };
      savePromptConfig(next);
      return next;
    });
  }, []);

  // ── Fetch provider catalog on mount (StrictMode-safe) ──────────────
  // This ONLY populates the provider dropdown. It never overwrites
  // the user's selected provider/model.
  useEffect(() => {
    let cancelled = false;

    const fetchProviderCatalog = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8080/api/settings');
        if (!response.ok) throw new Error('Failed to load settings');
        const data: SettingsResponse = await response.json();
        if (cancelled) return;

        setProviders(data.providers);
        setAvailableTones(data.tones || []);

        // Only pick a default if the user has NEVER selected a provider
        // (i.e. localStorage has no saved provider at all).
        const savedProvider = localStorage.getItem(STORAGE_KEYS.provider);
        if (!savedProvider) {
          const available = Object.keys(data.providers);
          if (available.length > 0) {
            const first = available[0];
            updateProvider(first);
            updateModel(data.providers[first].models[0] || '');
          }
        }
      } catch (err: any) {
        if (cancelled) return;
        console.error('Error fetching settings:', err);
        setErrorMsg('Could not connect to FastAPI server. Make sure the backend is running on port 8080.');
      }
    };

    fetchProviderCatalog();
    return () => { cancelled = true; };
  }, [updateProvider, updateModel]);

  // ── Fetch chat history when thread changes ─────────────────────────
  const fetchHistory = useCallback(async (customPromptConfig?: PromptConfig) => {
    const provider = loadSetting(STORAGE_KEYS.provider, 'openai');
    const model = loadSetting(STORAGE_KEYS.model, 'gpt-4o-mini');
    const pc = customPromptConfig || loadPromptConfig();

    if (!provider || !model || !threadId) return;

    try {
      const response = await fetch(
        `http://127.0.0.1:8080/api/chat/${threadId}/history?provider=${provider}&model=${model}&chatbot_name=${encodeURIComponent(pc.chatbot_name)}&tone=${encodeURIComponent(pc.tone)}`
      );
      if (!response.ok) throw new Error('Failed to load history');
      const data = await response.json();
      setMessages(data.messages || []);
    } catch (err: any) {
      console.error('Error fetching chat history:', err);
    }
  }, [threadId]);

  useEffect(() => {
    fetchHistory();
  }, [threadId, fetchHistory]);

  // ── Auto-fix model when provider changes ───────────────────────────
  // Only resets the model if the currently-selected model is not valid
  // for the newly-selected provider.
  useEffect(() => {
    const availableModels = providers[selectedProvider]?.models || [];
    if (availableModels.length > 0 && !availableModels.includes(selectedModel)) {
      updateModel(availableModels[0]);
    }
  }, [selectedProvider, providers, selectedModel, updateModel]);

  // ── Scroll to bottom of chat ───────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // ── Send message handler ───────────────────────────────────────────
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
          prompt_config: promptConfig,
          messages: [userMessage],
          provider: selectedProvider,
          model: selectedModel,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to get agent response');
      }

      const data = await response.json();
      setMessages(data.messages || []);
    } catch (err: any) {
      console.error('Chat error:', err);
      setErrorMsg(err.message || 'An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  // ── Clear chat history ─────────────────────────────────────────────
  const handleClearHistory = async () => {
    setErrorMsg(null);
    try {
      const response = await fetch(`http://127.0.0.1:8080/api/chat/${threadId}/clear`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to clear session on backend');
      
      // Start a fresh thread (settings are NOT cleared — only messages)
      const newTid = `thread-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
      saveSetting(STORAGE_KEYS.threadId, newTid);
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
      {/* Main Chat Interface */}
      <main className="chat-main">
        <header className="chat-header">
          <h1>Autonomous Agent Playground</h1>
          <div className="chat-header-actions">
            <div className="status-indicator">
              <span className="dot active"></span>
              Active Model: <strong style={{ marginLeft: '4px' }}>{selectedProvider.toUpperCase()} / {selectedModel}</strong>
            </div>
            <button 
              className={`sidebar-toggle-btn ${isModalOpen ? 'active' : ''}`}
              onClick={toggleModal}
              aria-label="Open Settings"
              title="Open Settings"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon-gear">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </button>
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
          {messages
            .filter(msg => msg.role !== 'system')
            .map((msg, index) => {
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

      {/* Modal Popup & Backdrop Overlay */}
      {isModalOpen && (
        <div className="modal-backdrop" onClick={toggleModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Agent Settings</h2>
              <button 
                type="button"
                className="modal-close-btn"
                onClick={toggleModal}
                aria-label="Close"
                title="Close Settings"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="icon-close">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>

            {/* Tab selection switcher */}
            <div className="modal-tabs">
              <button 
                type="button"
                className={`tab-btn ${activeTab === 'agent' ? 'active' : ''}`}
                onClick={() => setActiveTab('agent')}
              >
                Agent Configuration
              </button>
              <button 
                type="button"
                className={`tab-btn ${activeTab === 'prompt' ? 'active' : ''}`}
                onClick={() => setActiveTab('prompt')}
              >
                Prompt Configuration
              </button>
            </div>

            <div className="modal-body">
              {activeTab === 'agent' && (
                <div className="tab-pane">
                  <div className="setting-group">
                    <label>Provider</label>
                    <select 
                      value={selectedProvider} 
                      onChange={(e) => updateProvider(e.target.value)}
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
                      onChange={(e) => updateModel(e.target.value)}
                    >
                      {providers[selectedProvider]?.models.map(m => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {activeTab === 'prompt' && (
                <div className="tab-pane">
                  <div className="setting-group">
                    <label>Chatbot Name</label>
                    <input 
                      type="text" 
                      value={tempPromptConfig.chatbot_name} 
                      onChange={(e) => setTempPromptConfig(prev => ({ ...prev, chatbot_name: e.target.value }))}
                      placeholder="e.g. Jarvis"
                      className="name-input"
                    />
                  </div>

                  <div className="setting-group">
                    <label>Assistant Tone</label>
                    <select 
                      value={tempPromptConfig.tone} 
                      onChange={(e) => setTempPromptConfig(prev => ({ ...prev, tone: e.target.value }))}
                    >
                      {availableTones.map(t => (
                        <option key={t} value={t}>
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="save-action-row">
                    <button 
                      type="button" 
                      className="prompt-save-btn"
                      onClick={async () => {
                        updatePromptConfig(tempPromptConfig);
                        await fetchHistory(tempPromptConfig);
                        setIsSavedSuccessfully(true);
                        setTimeout(() => setIsSavedSuccessfully(false), 3000);
                      }}
                    >
                      Save Changes
                    </button>
                    {isSavedSuccessfully && (
                      <span className="save-success-badge">
                        ✓ Saved & updated dynamically!
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button 
                type="button"
                className="clear-btn secondary" 
                onClick={() => {
                  handleClearHistory();
                  toggleModal();
                }}
              >
                Reset Chat History
              </button>
              <button 
                type="button"
                className="modal-action-btn primary" 
                onClick={toggleModal}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

