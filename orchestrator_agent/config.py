import os

import dotenv

# Load environment variables from .env on startup
dotenv.load_dotenv()

# List of default models supported per provider
AVAILABLE_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.5-preview"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"],
    "groq": [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile"
    ],
    "anthropic": ["claude-haiku-4-5-20251001", "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
    "ollama": ["gemma3:1b", "llama3", "mistral", "phi3"],
    "dynamic": ["router"],
    "litellm": ["fallback"]
}

def get_env_variable(name: str, default: str = "") -> str:
    """Reads environment variables from current process space."""
    return os.getenv(name, default)


# Prompt Configuration
TONES = ["friendly","professional","mature"]


# Model used by the dynamic routing LLM layer to classify prompts
ROUTER_MODEL = "openai/gpt-oss-20b"

# Primary models recommended for simple and complex tasks
PRIMARY_SIMPLE_MODEL = ("groq", "openai/gpt-oss-20b")
PRIMARY_COMPLEX_MODEL = ("groq", "openai/gpt-oss-120b")

# Fallback sequence if the router call itself fails
ROUTER_FALLBACK_CHAIN = [
    ("groq", "openai/gpt-oss-120b"),
    ("openai", "gpt-4o-mini"),
    ("anthropic", "claude-haiku-4-5-20251001"),
    ("gemini", "gemini-2.5-flash"),
    ("ollama", "gemma3:1b")
]

# Fallback sequence for simple tasks (when simple model fails)
SIMPLE_FALLBACK_CHAIN = [
    ("groq", "openai/gpt-oss-120b"),
    ("gemini", "gemini-2.5-flash"),
    ("ollama", "gemma3:1b")
]

# Fallback sequence for complex tasks (when complex model fails)
COMPLEX_FALLBACK_CHAIN = [
    ("groq", "openai/gpt-oss-120b"),
    ("anthropic", "claude-haiku-4-5-20251001"),
    ("anthropic", "claude-3-5-sonnet-latest"),
    ("gemini", "gemini-2.5-flash"),
    ("ollama", "gemma3:1b")
]