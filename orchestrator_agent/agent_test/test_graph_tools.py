import sys
import unittest
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from orchestrator_agent.graphs.graph_builder import GraphBuilder, memory_checkpointer


class MockToolCallingLLM:
    """
    Mock LLM that triggers a tool call on its first turn,
    then answers the question on its second turn using the tool's result.
    """

    def __init__(self):
        self.calls = 0
        self.invoked_messages = []
        self.tools = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.calls += 1
        self.invoked_messages.append(messages)
        if self.calls == 1:
            return AIMessage(content="", tool_calls=[{"name": "add", "args": {"a": 15, "b": 25}, "id": "call_abc123"}])
        else:
            tool_msg = next((m for m in messages if isinstance(m, ToolMessage)), None)
            val = tool_msg.content if tool_msg else "unknown"
            return AIMessage(content=f"The result is {val}.")


class TestGraphTools(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.llm = MockToolCallingLLM()
        self.builder = GraphBuilder(model=self.llm)
        self.graph = await self.builder.setup_graph("basic_chatbot")
        self.thread_id = "test-tool-routing-thread-1"

    async def asyncTearDown(self):
        memory_checkpointer.storage.pop(self.thread_id, None)

    async def test_tool_calling_and_routing_loop(self):
        config = {"configurable": {"thread_id": self.thread_id}}

        # Invoke graph with user message asking to add 15 and 25
        initial_state = {
            "messages": [
                SystemMessage(content="You are a helpful math assistant."),
                HumanMessage(content="What is 15 + 25?"),
            ]
        }

        # Run graph
        await self.graph.ainvoke(initial_state, config)

        # Fetch actual compiled state from checkpointer
        state = await self.graph.aget_state(config)
        messages = state.values.get("messages", [])

        # The history loop should contain:
        # 1. SystemMessage
        # 2. HumanMessage ("What is 15 + 25?")
        # 3. AIMessage (tool_calls=[...])
        # 4. ToolMessage (content="40.0")
        # 5. AIMessage (content="The result is 40.0.")
        self.assertEqual(len(messages), 5)
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertIsInstance(messages[1], HumanMessage)

        self.assertIsInstance(messages[2], AIMessage)
        self.assertEqual(len(messages[2].tool_calls), 1)
        self.assertEqual(messages[2].tool_calls[0]["name"], "add")

        self.assertIsInstance(messages[3], ToolMessage)
        self.assertEqual(messages[3].content, "40.0")
        self.assertEqual(messages[3].tool_call_id, "call_abc123")

        self.assertIsInstance(messages[4], AIMessage)
        self.assertEqual(messages[4].content, "The result is 40.0.")

        # Confirm mock was called twice (once for tool decision, once for final text)
        self.assertEqual(self.llm.calls, 2)


if __name__ == "__main__":
    unittest.main()
