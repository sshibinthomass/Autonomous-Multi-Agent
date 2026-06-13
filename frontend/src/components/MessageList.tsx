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
        .filter((msg) => {
          if (msg.role === 'system') return false;
          if (msg.role === 'assistant') {
            const hasNoContent = !msg.content || (typeof msg.content === 'string' && !msg.content.trim());
            const hasToolCalls = msg.tool_calls && msg.tool_calls.length > 0;
            if (hasNoContent && hasToolCalls) return false;
          }
          return true;
        })
        .map((msg, index) => {
          if (msg.role === 'tool') {
            return (
              <div
                key={index}
                className="message-row tool-row"
                style={{
                  alignSelf: 'flex-start',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 16px',
                  backgroundColor: 'rgba(59, 130, 246, 0.06)',
                  border: '1px solid rgba(59, 130, 246, 0.15)',
                  borderLeft: '4px solid var(--primary)',
                  borderRadius: '8px',
                  fontSize: '0.85rem',
                  maxWidth: '85%',
                  margin: '4px 0 4px 52px',
                }}
              >
                <span style={{ fontSize: '1rem', display: 'flex', alignItems: 'center' }}>🔧</span>
                <div style={{ fontFamily: 'Consolas, Monaco, monospace', color: 'var(--text-muted)', wordBreak: 'break-all' }}>
                  {msg.content}
                </div>
              </div>
            );
          }

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
