#%%
import sys
from pathlib import Path
import os
import dotenv

dotenv.load_dotenv()

print("cwd:", Path.cwd())
print("python:", sys.executable)

project_root_value = os.getenv("PROJECT_ROOT", "")
if project_root_value:
    repo_root = Path(project_root_value).expanduser().resolve()
elif "__file__" in globals():
    repo_root = Path(__file__).resolve().parent.parent.parent
else:
    repo_root = Path.cwd()

sys.path.insert(0, str(repo_root))

from orchestrator_agent.llms.anthropic_llm import AnthropicLLM
from orchestrator_agent.llms.groq_llm import GroqLLM
from orchestrator_agent.llms.gemini_llm import GeminiLLM
from orchestrator_agent.llms.ollama_llm import OllamaLLM
from orchestrator_agent.llms.openai_llm import OpenAILLM

prompt = "Hello, who won the FIFA World Cup in 2018?"


# %%
def invoke_and_print(label, llm_wrapper, user_controls_input):
    llm = llm_wrapper(user_controls_input).get_base_llm()
    response = llm.invoke(prompt)
    print(f"{label}: {response}")


invoke_and_print(
    "Gemini",
    GeminiLLM,
    {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "selected_llm": "gemini-2.5-flash",
    },
)

invoke_and_print(
    "OpenAI",
    OpenAILLM,
    {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "selected_llm": "gpt-4.1-mini",
    },
)

invoke_and_print(
    "Anthropic",
    AnthropicLLM,
    {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "selected_llm": "claude-haiku-4-5-20251001",
    },
)

invoke_and_print(
    "Groq",
    GroqLLM,
    {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "selected_llm": "openai/gpt-oss-20b",
    },
)

invoke_and_print(
    "Ollama",
    OllamaLLM,
    {
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "selected_llm": "gemma3:1b",
    },
)