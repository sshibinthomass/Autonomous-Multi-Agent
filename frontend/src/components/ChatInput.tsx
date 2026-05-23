import React from 'react';

interface ChatInputProps {
  inputValue: string;
  onInputChange: (val: string) => void;
  onSend: (e: React.FormEvent) => void;
  isLoading: boolean;
  placeholder: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  inputValue,
  onInputChange,
  onSend,
  isLoading,
  placeholder,
}) => {
  return (
    <footer className="chat-input-footer">
      <form onSubmit={onSend} className="input-form">
        <input
          type="text"
          placeholder={placeholder}
          value={inputValue}
          onChange={(e) => onInputChange(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" disabled={!inputValue.trim() || isLoading}>
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </footer>
  );
};
