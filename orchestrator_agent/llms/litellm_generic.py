import json
import logging
import sys
import warnings
from pathlib import Path
from typing import Any, List

# Prevent python from shadowing the third-party 'litellm' library
local_dir = str(Path(__file__).resolve().parent)
had_local = local_dir in sys.path
if had_local:
    sys.path.remove(local_dir)
import litellm

if had_local:
    sys.path.insert(0, local_dir)

# Silence LiteLLM logging & warning noise globally
litellm.set_verbose = False
litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited")

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

logger = logging.getLogger(__name__)


def to_litellm_model(provider: str, model: str) -> str:
    """Converts provider and model names into LiteLLM's standard string format.

    E.g., "openai", "gpt-4o" -> "gpt-4o"
    E.g., "anthropic", "claude-3-5-sonnet-latest" -> "anthropic/claude-3-5-sonnet-latest"
    """
    p_lower = provider.lower().strip()
    m_strip = model.strip()
    if p_lower == "openai":
        return m_strip
    return f"{p_lower}/{m_strip}"


def convert_messages_to_litellm(messages: List[BaseMessage]) -> List[dict]:
    """Converts a sequence of LangChain message objects into standard LiteLLM/OpenAI-compatible dictionaries.

    Supports SystemMessage, AIMessage (with tool calls), ToolMessage, and generic messages.
    """
    litellm_msgs = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        elif isinstance(msg, ToolMessage):
            role = "tool"
        else:
            role = "user"

        dct = {"role": role, "content": msg.content or ""}

        # Parse and translate LangChain tool calls back to standard OpenAI tool calls format
        if isinstance(msg, AIMessage) and msg.tool_calls:
            openai_tool_calls = []
            for tc in msg.tool_calls:
                openai_tool_calls.append(
                    {
                        "id": tc.get("id"),
                        "type": "function",
                        "function": {"name": tc.get("name"), "arguments": json.dumps(tc.get("args"))},
                    }
                )
            dct["tool_calls"] = openai_tool_calls

        # Add metadata needed for tool execution responses
        if isinstance(msg, ToolMessage):
            dct["tool_call_id"] = msg.tool_call_id
            dct["name"] = msg.name

        litellm_msgs.append(dct)
    return litellm_msgs


def map_tool_calls(message: Any) -> List[dict]:
    """Parses OpenAI tool calls back into LangChain structured dictionaries."""
    tool_calls = []
    if hasattr(message, "tool_calls") and message.tool_calls:
        for tc in message.tool_calls:
            tool_calls.append(
                {"name": tc.function.name, "args": json.loads(tc.function.arguments), "id": tc.id, "type": "tool_call"}
            )
    return tool_calls


def process_response(response: Any) -> ChatResult:
    """Helper to map a LiteLLM response back into a standard LangChain ChatResult."""
    logger.info(f"Model that actually answered: {response.model}")
    print(f"Model that actually answered: {response.model}", flush=True)

    choice = response.choices[0]
    message = choice.message
    content = message.content or ""
    tool_calls = map_tool_calls(message)

    ai_msg = AIMessage(content=content, tool_calls=tool_calls)
    return ChatResult(generations=[ChatGeneration(message=ai_msg)])
