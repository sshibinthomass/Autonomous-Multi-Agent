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
import { SessionsSidebar, type Session } from './components/SessionsSidebar';

function App() {
  // ── Modal Popup Open/Closed state ───────────────────────────────────
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const toggleModal = useCallback(() => {
    setIsModalOpen(prev => !prev);
  }, []);

  // ── Sessions & Sidebar State ───────────────────────────────────────
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isSessionsSidebarOpen, setIsSessionsSidebarOpen] = useState<boolean>(true);

  // ── Thread session state ────────────────────────────────────────────
  const [threadId, setThreadId] = useState<string>(() => {
    let tid = loadSetting(STORAGE_KEYS.threadId, '');
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
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({});
  const [availableTones, setAvailableTones] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>(
    () => loadSetting(STORAGE_KEYS.provider, 'openai')
  );
  const [selectedModel, setSelectedModel] = useState<string>(
    () => loadSetting(STORAGE_KEYS.model, 'gpt-4o-mini')
  );

  // Prompt configuration as a single dict
  const [promptConfig, setPromptConfig] = useState<PromptConfig>(loadPromptConfig);

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  // ── Fetch session list from backend ──────────────────────────────
  const fetchSessions = useCallback(async () => {
    try {
      const response = await fetch('http://127.0.0.1:8080/api/sessions');
      if (!response.ok) throw new Error('Failed to load sessions');
      const data = await response.json();
      setSessions(data || []);
      return data || [];
    } catch (err) {
      console.error('Error fetching sessions:', err);
      return [];
    }
  }, []);

  // ── Wrapped setters that sync with local storage & backend ──────────
  const updateProvider = useCallback(async (value: string) => {
    setSelectedProvider(value);
    saveSetting(STORAGE_KEYS.provider, value);
    if (threadId) {
      try {
        await fetch(`http://127.0.0.1:8080/api/sessions/${threadId}/settings`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: value })
        });
        fetchSessions();
      } catch (err) {
        console.error('Error updating provider in backend session:', err);
      }
    }
  }, [threadId, fetchSessions]);

  const updateModel = useCallback(async (value: string) => {
    setSelectedModel(value);
    saveSetting(STORAGE_KEYS.model, value);
    if (threadId) {
      try {
        await fetch(`http://127.0.0.1:8080/api/sessions/${threadId}/settings`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: value })
        });
        fetchSessions();
      } catch (err) {
        console.error('Error updating model in backend session:', err);
      }
    }
  }, [threadId, fetchSessions]);

  // Update a single key inside promptConfig while persisting the whole dict
  const updatePromptConfig = useCallback((patch: Partial<PromptConfig>) => {
    setPromptConfig(prev => {
      const next = { ...prev, ...patch };
      savePromptConfig(next);
      return next;
    });
  }, []);

  // ── Select and Load a specific session ─────────────────────────────
  const handleSelectSession = useCallback((id: string) => {
    setThreadId(id);
    saveSetting(STORAGE_KEYS.threadId, id);
  }, []);

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

      // Synchronize settings from the loaded session
      if (data.settings) {
        setSelectedProvider(data.settings.provider);
        setSelectedModel(data.settings.model);
        saveSetting(STORAGE_KEYS.provider, data.settings.provider);
        saveSetting(STORAGE_KEYS.model, data.settings.model);

        const loadedPc = {
          chatbot_name: data.settings.chatbot_name,
          tone: data.settings.tone
        };
        setPromptConfig(loadedPc);
        savePromptConfig(loadedPc);
      }
    } catch (err: any) {
      console.error('Error fetching chat history:', err);
    }
  }, [threadId]);

  useEffect(() => {
    fetchHistory();
  }, [threadId, fetchHistory]);

  // ── Fetch sessions and catalog on mount ─────────────────────────────
  useEffect(() => {
    let cancelled = false;

    const initialize = async () => {
      try {
        // Fetch provider catalog
        const response = await fetch('http://127.0.0.1:8080/api/settings');
        if (!response.ok) throw new Error('Failed to load settings');
        const data: SettingsResponse = await response.json();
        if (cancelled) return;

        setProviders(data.providers);
        setAvailableTones(data.tones || []);

        // Load sessions
        const loadedSessions = await fetchSessions();
        if (cancelled) return;

        if (loadedSessions && loadedSessions.length > 0) {
          // If a threadId is saved in localStorage and exists in sessions, keep it, otherwise load first session
          const savedTid = localStorage.getItem(STORAGE_KEYS.threadId);
          const hasSavedThread = loadedSessions.some((s: Session) => s.id === savedTid);
          if (savedTid && hasSavedThread) {
            setThreadId(savedTid);
          } else {
            handleSelectSession(loadedSessions[0].id);
          }
        } else {
          // Create default first session on the backend
          const prov = loadSetting(STORAGE_KEYS.provider, 'openai');
          const mod = loadSetting(STORAGE_KEYS.model, 'gpt-4o-mini');
          const pc = loadPromptConfig();
          
          const createResponse = await fetch('http://127.0.0.1:8080/api/sessions', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              provider: prov,
              model: mod,
              chatbot_name: pc.chatbot_name,
              tone: pc.tone
            })
          });

          if (createResponse.ok) {
            const newSession = await createResponse.json();
            await fetchSessions();
            if (!cancelled) {
              handleSelectSession(newSession.id);
            }
          }
        }
      } catch (err: any) {
        if (cancelled) return;
        console.error('Error fetching settings/sessions:', err);
        setErrorMsg('Could not connect to FastAPI server. Make sure the backend is running on port 8080.');
      }
    };

    initialize();
    return () => { cancelled = true; };
  }, [fetchSessions, handleSelectSession]);

  // ── Auto-fix model when provider changes ───────────────────────────
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

  // ── Create, Rename, Delete session handlers ────────────────────────
  const handleCreateSession = useCallback(async () => {
    try {
      const response = await fetch('http://127.0.0.1:8080/api/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          provider: selectedProvider,
          model: selectedModel,
          chatbot_name: promptConfig.chatbot_name,
          tone: promptConfig.tone
        })
      });

      if (!response.ok) throw new Error('Failed to create new session');
      const newSession = await response.json();
      await fetchSessions();
      handleSelectSession(newSession.id);
    } catch (err) {
      console.error('Error creating session:', err);
      setErrorMsg('Failed to create a new session on the backend.');
    }
  }, [selectedProvider, selectedModel, promptConfig, fetchSessions, handleSelectSession]);

  const handleRenameSession = useCallback(async (id: string, newName: string) => {
    try {
      const response = await fetch(`http://127.0.0.1:8080/api/sessions/${id}/rename`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: newName })
      });

      if (!response.ok) throw new Error('Failed to rename session');
      await fetchSessions();
    } catch (err) {
      console.error('Error renaming session:', err);
      setErrorMsg('Failed to rename session.');
    }
  }, [fetchSessions]);

  const handleDeleteSession = useCallback(async (id: string) => {
    try {
      const response = await fetch(`http://127.0.0.1:8080/api/sessions/${id}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete session');
      
      const updatedList = await fetchSessions();
      
      if (id === threadId) {
        if (updatedList && updatedList.length > 0) {
          handleSelectSession(updatedList[0].id);
        } else {
          await handleCreateSession();
        }
      }
    } catch (err) {
      console.error('Error deleting session:', err);
      setErrorMsg('Failed to delete session.');
    }
  }, [threadId, fetchSessions, handleSelectSession, handleCreateSession]);

  // ── Send message handler ───────────────────────────────────────────
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    setErrorMsg(null);
    const userMessage: Message = { role: 'user', content: inputValue.trim() };
    
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
        let errorDetail = 'Failed to get agent response';
        try {
          const errData = await response.json();
          errorDetail = errData.detail || errorDetail;
        } catch (_) {}
        throw new Error(errorDetail);
      }

      // Add a placeholder message for the assistant
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Readable stream not supported or unavailable.');
      }

      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE data format: "data: {...}\n\n"
        const lines = buffer.split('\n');
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;

          const jsonStr = trimmed.slice(6);
          try {
            const data = JSON.parse(jsonStr);
            if (data.type === 'token') {
              setMessages(prev => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg && lastMsg.role === 'assistant') {
                  updated[updated.length - 1] = {
                    ...lastMsg,
                    content: lastMsg.content + data.content
                  };
                }
                return updated;
              });
            } else if (data.type === 'done') {
              if (data.messages) {
                setMessages(data.messages);
              }
            }
          } catch (e) {
            console.error('Error parsing SSE JSON:', e);
          }
        }
      }

      fetchSessions(); // Refresh sessions to update auto-generated names/timestamps
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
      
      // Start a fresh session
      const createResponse = await fetch('http://127.0.0.1:8080/api/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          provider: selectedProvider,
          model: selectedModel,
          chatbot_name: promptConfig.chatbot_name,
          tone: promptConfig.tone
        })
      });
      if (!createResponse.ok) throw new Error('Failed to create new session after clearing');
      const newSession = await createResponse.json();
      
      await fetchSessions();
      handleSelectSession(newSession.id);
    } catch (err: any) {
      console.error('Error clearing history:', err);
      setErrorMsg('Could not reset history on backend. Local chat has been reset.');
      setMessages([{ role: 'system', content: 'You are a helpful and efficient assistant.' }]);
    }
  };

  // ── Save prompt config and dynamic update ─────────────────────────
  const handlePromptConfigSave = async (newConfig: PromptConfig) => {
    updatePromptConfig(newConfig);
    if (threadId) {
      try {
        await fetch(`http://127.0.0.1:8080/api/sessions/${threadId}/settings`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            chatbot_name: newConfig.chatbot_name,
            tone: newConfig.tone
          })
        });
        fetchSessions();
      } catch (err) {
        console.error('Error updating prompt settings in backend session:', err);
      }
    }
    await fetchHistory(newConfig);
  };

  return (
    <div className="app-container">
      {/* Collapsible left sidebar for chat sessions */}
      <SessionsSidebar
        isOpen={isSessionsSidebarOpen}
        onToggle={() => setIsSessionsSidebarOpen(prev => !prev)}
        sessions={sessions}
        activeSessionId={threadId}
        onSelectSession={handleSelectSession}
        onCreateSession={handleCreateSession}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
      />

      {/* Main Chat Interface */}
      <main className="chat-main">
        <ChatHeader
          selectedProvider={selectedProvider}
          selectedModel={selectedModel}
          isModalOpen={isModalOpen}
          onToggleModal={toggleModal}
          isSessionsSidebarOpen={isSessionsSidebarOpen}
          onToggleSessionsSidebar={() => setIsSessionsSidebarOpen(prev => !prev)}
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
