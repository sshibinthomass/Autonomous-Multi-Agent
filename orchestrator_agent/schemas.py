from pydantic import BaseModel
from typing import List, Dict

class ChatMessage(BaseModel):
    """
    Represents a single message in the conversation.
    Used to structure and validate individual messages sent back and forth 
    between the React frontend and the FastAPI backend.
    """
    role: str  # Dictates who sent the message: 'user', 'assistant', or 'system'
    content: str  # The actual text payload of the message

class PromptConfig(BaseModel):
    """
    Groups configurations relating to the agent's system prompt guidelines.
    """
    chatbot_name: str = "Jarvis"  # Custom assistant name (default: Jarvis)
    tone: str = "friendly"  # Conversational tone: friendly, mature, professional

class ChatRequest(BaseModel):
    """
    Represents the main request payload for the `/api/chat` endpoint.
    Used to validate that the frontend has provided a valid message history list,
    selected a supported provider, and picked a specific model name.
    """
    thread_id: str = "default"  # To identify the chat session in the backend
    prompt_config: PromptConfig = PromptConfig()  # Centralized prompt configuration variables
    messages: List[ChatMessage]  # The new message(s) to send (usually just the latest user message)
    provider: str  # The target engine provider: 'openai', 'gemini', 'groq', 'anthropic', 'ollama'
    model: str  # The specific model string (e.g. 'gpt-4o-mini', 'gemini-2.5-flash')

class ProviderDetail(BaseModel):
    """
    Describes the setup and model capability details for a single LLM provider.
    Used to encapsulate model collections inside the settings response.
    """
    models: List[str]  # The default list of models supported by this provider

class SettingsResponse(BaseModel):
    """
    Represents the response structure for the `/api/settings` endpoint.
    Used to cleanly serialize the catalog of all supported providers and models 
    so the frontend UI can render select menus.
    """
    providers: Dict[str, ProviderDetail]  # Map of provider names to their details
