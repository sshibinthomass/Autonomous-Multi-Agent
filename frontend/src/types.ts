export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ProviderInfo {
  models: string[];
}

export interface SettingsResponse {
  providers: {
    [key: string]: ProviderInfo;
  };
  tones: string[];
}

// Mirrors the backend's PromptConfig (schemas.py)
export interface PromptConfig {
  chatbot_name: string;
  tone: string;
}
