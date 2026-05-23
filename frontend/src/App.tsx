import { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import type { Message, ProviderInfo, SettingsResponse, PromptConfig } from './types';
import {
  STORAGE_KEYS,
  loadSetting,
  saveSetting,
  loadPromptConfig,
  savePromptConfig,
} from './utils/storage';
import { ChatHeader } from './components/ChatHeader';
import { MessageList } from './components/MessageList';
import { ChatInput } from './components/ChatInput';
import { SettingsModal } from './components/SettingsModal';

function App() {
  // ── Modal Popup Open/Closed state ───────────────────────────────────
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

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

  const chatEndRef = useRef<HTMLDivElement | null>(null);

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

  // ── Save prompt config and dynamic update ─────────────────────────
  const handlePromptConfigSave = async (newConfig: PromptConfig) => {
    updatePromptConfig(newConfig);
    await fetchHistory(newConfig);
  };

  return (
    <div className="app-container">
      {/* Main Chat Interface */}
      <main className="chat-main">
        <ChatHeader
          selectedProvider={selectedProvider}
          selectedModel={selectedModel}
          isModalOpen={isModalOpen}
          onToggleModal={toggleModal}
        />

        {/* Error banner */}
        {errorMsg && (
          <div className="error-banner">
            <span>{errorMsg}</span>
            <button className="close-error" onClick={() => setErrorMsg(null)}>×</button>
          </div>
        )}

        {/* Chat message history container */}
        <MessageList
          messages={messages}
          isLoading={isLoading}
          chatEndRef={chatEndRef}
        />

        {/* Message Input Box */}
        <ChatInput
          inputValue={inputValue}
          onInputChange={setInputValue}
          onSend={handleSendMessage}
          isLoading={isLoading}
          placeholder={`Send a message to the ${selectedModel} assistant...`}
        />
      </main>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isModalOpen}
        onClose={toggleModal}
        providers={providers}
        availableTones={availableTones}
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        onProviderChange={updateProvider}
        onModelChange={updateModel}
        promptConfig={promptConfig}
        onPromptConfigSave={handlePromptConfigSave}
        onClearHistory={handleClearHistory}
      />
    </div>
  );
}

export default App;
