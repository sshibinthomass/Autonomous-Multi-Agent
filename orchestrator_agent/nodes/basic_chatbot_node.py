import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from orchestrator_agent.states.chatbotState import ChatbotState
from orchestrator_agent.system_configuration import MAX_HISTORY_MESSAGES, MAX_TOOL_ITERATIONS

load_dotenv()


def prepare_messages_for_llm(messages: list, max_messages: int = MAX_HISTORY_MESSAGES) -> list:
    """Keep system prompts, trim older turns, and always keep the full latest user turn."""
    system_messages = [m for m in messages if isinstance(m, SystemMessage)]
    other_messages = [m for m in messages if not isinstance(m, SystemMessage)]

    last_human_idx = -1
    for i in range(len(other_messages) - 1, -1, -1):
        if isinstance(other_messages[i], HumanMessage):
            last_human_idx = i
            break

    if last_human_idx < 0:
        return system_messages + other_messages[-max_messages:]

    current_turn = other_messages[last_human_idx:]
    prior_turns = other_messages[:last_human_idx]
    prior_budget = max(0, max_messages - len(current_turn))
    return system_messages + prior_turns[-prior_budget:] + current_turn


def tool_calls_in_current_turn(messages: list) -> int:
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return sum(1 for m in messages[i:] if isinstance(m, ToolMessage))
    return 0


class BasicChatbotNode:
    def __init__(self, model, model_with_tools=None):
        self.llm_with_tools = model_with_tools or model
        self.base_llm = model

    def process(self, state: ChatbotState) -> dict:
        messages = state.get("messages", [])
        input_messages = prepare_messages_for_llm(messages)

        llm = self.base_llm if tool_calls_in_current_turn(messages) >= MAX_TOOL_ITERATIONS else self.llm_with_tools
        response = llm.invoke(input_messages)
        return {"messages": [response]}


if __name__ == "__main__":
    from langchain_core.messages import HumanMessage, SystemMessage

    from orchestrator_agent.llms.groq_llm import GroqLLM

    user_controls_input = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "selected_llm": "openai/gpt-oss-20b",
    }
    llm = GroqLLM(user_controls_input).get_base_llm()
    node = BasicChatbotNode(llm)
    result = node.process(
        {
            "messages": [
                SystemMessage(content="You are a helpful and efficient assistant."),
                HumanMessage(content="Hi"),
            ]
        }
    )
    print("Basic Chatbot Node Result:", result)
