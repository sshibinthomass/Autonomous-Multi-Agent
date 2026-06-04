import React from 'react';
import type { Message } from '../types';
import { Markdown } from './Markdown';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  chatEndRef: React.RefObject<HTMLDivElement | null>;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  chatEndRef,
}) => {
  return (
    <div className="messages-container">
      {messages
        .filter((msg) => msg.role !== 'system')
        .map((msg, index) => {
          return (
            <div
              key={index}
              className={`message-row ${
                msg.role === 'user' ? 'user-row' : 'bot-row'
              }`}
            >
              <div className="avatar">{msg.role === 'user' ? 'U' : 'AI'}</div>
              <div className="message-bubble-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxWidth: '100%' }}>
                <div className="message-bubble">
                  <Markdown content={msg.content} />
                </div>
                {msg.timestamp && (
                  <span
                    className="message-timestamp"
                    style={{
                      fontSize: '0.7rem',
                      color: 'var(--text-muted)',
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      opacity: 0.6,
                      marginTop: '2px',
                      padding: '0 4px',
                    }}
                  >
                    {msg.timestamp}
                  </span>
                )}
              </div>
            </div>
          );
        })}

      {/* Loading Indicator */}
      {isLoading && messages.length > 0 && messages[messages.length - 1]?.role !== 'assistant' && (
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
  );
};
