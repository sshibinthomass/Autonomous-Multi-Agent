import React, { useState, useEffect } from 'react';
import type { ProviderInfo, PromptConfig } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  providers: Record<string, ProviderInfo>;
  availableTones: string[];
  selectedProvider: string;
  selectedModel: string;
  onProviderChange: (value: string) => void;
  onModelChange: (value: string) => void;
  promptConfig: PromptConfig;
  onPromptConfigSave: (config: PromptConfig) => Promise<void> | void;
  onClearHistory: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  providers,
  availableTones,
  selectedProvider,
  selectedModel,
  onProviderChange,
  onModelChange,
  promptConfig,
  onPromptConfigSave,
  onClearHistory,
}) => {
  const [activeTab, setActiveTab] = useState<'agent' | 'prompt'>('agent');
  const [tempPromptConfig, setTempPromptConfig] = useState<PromptConfig>(promptConfig);
  const [isSavedSuccessfully, setIsSavedSuccessfully] = useState<boolean>(false);

  // Synchronise temporary prompt config when modal opens or when promptConfig is loaded
  useEffect(() => {
    if (isOpen) {
      setTempPromptConfig(promptConfig);
      setIsSavedSuccessfully(false);
    }
  }, [isOpen, promptConfig]);

  if (!isOpen) return null;

  const handleSave = async () => {
    await onPromptConfigSave(tempPromptConfig);
    setIsSavedSuccessfully(true);
    setTimeout(() => setIsSavedSuccessfully(false), 3000);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Agent Settings</h2>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close"
            title="Close Settings"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="icon-close"
            >
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
                  onChange={(e) => onProviderChange(e.target.value)}
                >
                  {Object.keys(providers).map((p) => (
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
                  onChange={(e) => onModelChange(e.target.value)}
                >
                  {providers[selectedProvider]?.models.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
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
                  onChange={(e) =>
                    setTempPromptConfig((prev) => ({
                      ...prev,
                      chatbot_name: e.target.value,
                    }))
                  }
                  placeholder="e.g. Jarvis"
                  className="name-input"
                />
              </div>

              <div className="setting-group">
                <label>Assistant Tone</label>
                <select
                  value={tempPromptConfig.tone}
                  onChange={(e) =>
                    setTempPromptConfig((prev) => ({
                      ...prev,
                      tone: e.target.value,
                    }))
                  }
                >
                  {availableTones.map((t) => (
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
                  onClick={handleSave}
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
              onClearHistory();
              onClose();
            }}
          >
            Reset Chat History
          </button>
          <button
            type="button"
            className="modal-action-btn primary"
            onClick={onClose}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
