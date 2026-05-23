import type { PromptConfig } from '../types';

export const STORAGE_KEYS = {
  threadId: 'agent_thread_id',
  provider: 'agent_provider',
  model: 'agent_model',
  promptConfig: 'agent_prompt_config',
} as const;

export const DEFAULT_PROMPT_CONFIG: PromptConfig = {
  chatbot_name: 'Jarvis',
  tone: 'friendly',
};

export function loadSetting(key: string, fallback: string): string {
  return localStorage.getItem(key) || fallback;
}

export function saveSetting(key: string, value: string): void {
  localStorage.setItem(key, value);
}

export function loadPromptConfig(): PromptConfig {
  const raw = localStorage.getItem(STORAGE_KEYS.promptConfig);
  if (raw) {
    try {
      return { ...DEFAULT_PROMPT_CONFIG, ...JSON.parse(raw) };
    } catch {
      /* corrupted JSON, fall through */
    }
  }
  return { ...DEFAULT_PROMPT_CONFIG };
}

export function savePromptConfig(config: PromptConfig): void {
  localStorage.setItem(STORAGE_KEYS.promptConfig, JSON.stringify(config));
}
