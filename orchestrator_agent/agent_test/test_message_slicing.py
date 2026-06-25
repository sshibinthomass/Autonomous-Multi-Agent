import sys
import unittest
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from orchestrator_agent.nodes.basic_chatbot_node import (
    prepare_messages_for_llm,
    tool_calls_in_current_turn,
)
from orchestrator_agent.system_configuration import MAX_HISTORY_MESSAGES


class TestMessageSlicing(unittest.TestCase):
    def test_multi_tool_turn_keeps_user_message(self):
        """A multi-step tool chain must not drop the user's question."""
        messages = [
            SystemMessage(content="You are helpful."),
            HumanMessage(content="sum of 6 and 3 multiplied by 6 and subtracted by four"),
            AIMessage(content="", tool_calls=[{"name": "add", "args": {"a": 6, "b": 3}, "id": "c1"}]),
            ToolMessage(content="9.0", tool_call_id="c1", name="add"),
            AIMessage(content="", tool_calls=[{"name": "multiply", "args": {"a": 9, "b": 6}, "id": "c2"}]),
            ToolMessage(content="54.0", tool_call_id="c2", name="multiply"),
            AIMessage(content="", tool_calls=[{"name": "subtract", "args": {"a": 54, "b": 4}, "id": "c3"}]),
            ToolMessage(content="50.0", tool_call_id="c3", name="subtract"),
        ]

        prepared = prepare_messages_for_llm(messages)

        self.assertIsInstance(prepared[0], SystemMessage)
        self.assertIsInstance(prepared[1], HumanMessage)
        self.assertEqual(prepared[1].content, "sum of 6 and 3 multiplied by 6 and subtracted by four")
        self.assertGreaterEqual(len(prepared), 6)

    def test_tool_calls_in_current_turn(self):
        messages = [
            HumanMessage(content="older question"),
            AIMessage(content="older answer"),
            HumanMessage(content="current question"),
            AIMessage(content="", tool_calls=[{"name": "add", "args": {"a": 1, "b": 2}, "id": "c1"}]),
            ToolMessage(content="3.0", tool_call_id="c1", name="add"),
            AIMessage(content="", tool_calls=[{"name": "add", "args": {"a": 3, "b": 4}, "id": "c2"}]),
            ToolMessage(content="7.0", tool_call_id="c2", name="add"),
        ]
        self.assertEqual(tool_calls_in_current_turn(messages), 2)

    def test_history_limit_still_applies_to_prior_turns(self):
        messages: list[BaseMessage] = [SystemMessage(content="System prompt instructions")]
        for i in range(15):
            messages.append(HumanMessage(content=f"User msg {i}"))
            messages.append(AIMessage(content=f"AI msg {i}"))
        messages.append(HumanMessage(content="Next user message"))

        prepared = prepare_messages_for_llm(messages)
        non_system = [m for m in prepared if not isinstance(m, SystemMessage)]

        self.assertEqual(len(non_system), MAX_HISTORY_MESSAGES)
        self.assertEqual(non_system[-1].content, "Next user message")


if __name__ == "__main__":
    unittest.main()
