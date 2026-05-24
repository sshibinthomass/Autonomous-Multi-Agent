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
              <div className="message-bubble">
                <Markdown content={msg.content} />
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
