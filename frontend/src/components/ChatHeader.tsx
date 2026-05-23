import React from 'react';

interface ChatHeaderProps {
  selectedProvider: string;
  selectedModel: string;
  isModalOpen: boolean;
  onToggleModal: () => void;
  isSessionsSidebarOpen: boolean;
  onToggleSessionsSidebar: () => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  selectedProvider,
  selectedModel,
  isModalOpen,
  onToggleModal,
  isSessionsSidebarOpen,
  onToggleSessionsSidebar,
}) => {
  return (
    <header className="chat-header">
      <div className="chat-header-left">
        {/* Toggle Sessions Sidebar button */}
        <button
          className={`sidebar-toggle-btn ${isSessionsSidebarOpen ? 'active' : ''}`}
          onClick={onToggleSessionsSidebar}
          aria-label="Toggle Sessions"
          title="Toggle Sessions"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ width: '20px', height: '20px' }}
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="3" x2="9" y2="21"></line>
          </svg>
        </button>
        <h1>Autonomous Agent Playground</h1>
      </div>
      
      <div className="chat-header-actions">
        <div className="status-indicator">
          <span className="dot active"></span>
          Active Model:{' '}
          <strong style={{ marginLeft: '4px' }}>
            {selectedProvider.toUpperCase()} / {selectedModel}
          </strong>
        </div>

        {/* Toggle Settings Modal button */}
        <button
          className={`sidebar-toggle-btn ${isModalOpen ? 'active' : ''}`}
          onClick={onToggleModal}
          aria-label="Open Settings"
          title="Open Settings"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="icon-gear"
          >
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </button>
      </div>
    </header>
  );
};
