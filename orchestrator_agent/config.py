import os

import dotenv

# Load environment variables from .env on startup
dotenv.load_dotenv()

# List of default models supported per provider
AVAILABLE_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.5-preview"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"],
    "groq": ["openai/gpt-oss-20b","openai/gpt-oss-20b","llama-3.1-8b-instant","llama-3.3-70b-versatile"],
    "anthropic": ["claude-haiku-4-5-20251001","claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
    "ollama": ["gemma3:1b","llama3", "mistral", "phi3"]
}

def get_env_variable(name: str, default: str = "") -> str:
    """Reads environment variables from current process space."""
    return os.getenv(name, default)


# Prompt Configuration
TONES = ["friendly","professional","mature"]