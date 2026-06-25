import sys
import unittest
from pathlib import Path

# Setup sys.path to find project root
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from orchestrator_agent.graphs.graph_builder import GraphBuilder, memory_checkpointer
from orchestrator_agent.schemas import ChatMessage
from orchestrator_agent.services import to_langchain_messages


class MockLLM:
    """
    A lightweight Mock LLM to test LangGraph memory operations without external API calls.
    """

    def __init__(self):
        self.invoked_messages = None

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.invoked_messages = messages
        last_msg = messages[-1].content
        return AIMessage(content=f"Echo: {last_msg}")


class TestBackendMemory(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Build graph with Mock LLM
        self.llm = MockLLM()
        self.builder = GraphBuilder(model=self.llm)
        self.graph = await self.builder.setup_graph("basic_chatbot")
        self.thread_id = "test-thread-xyz-123"

    async def asyncTearDown(self):
        # Clear checkpointer state for this thread
        memory_checkpointer.storage.pop(self.thread_id, None)

    async def test_initial_state_and_system_message(self):
        config = {"configurable": {"thread_id": self.thread_id}}

        # Verify initially thread has no snapshots
        state = await self.graph.aget_state(config)
        self.assertEqual(state.values, {})

        # Invoke with a new message
        msg = ChatMessage(role="user", content="Hello!")
        langchain_msgs = to_langchain_messages([msg])

        # Prepend default system prompt if empty
        langchain_msgs.insert(0, SystemMessage(content="You are a helpful and efficient assistant."))

        # Run graph
        await self.graph.ainvoke({"messages": langchain_msgs}, config)

        # Fetch updated history
        updated_state = await self.graph.aget_state(config)
        messages = updated_state.values.get("messages", [])

        # Should have: SystemMessage -> HumanMessage -> AIMessage
        self.assertEqual(len(messages), 3)
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertIsInstance(messages[1], HumanMessage)
        self.assertIsInstance(messages[2], AIMessage)
        self.assertEqual(messages[2].content, "Echo: Hello!")

    async def test_memory_persistence_across_multiple_invocations(self):
        config = {"configurable": {"thread_id": self.thread_id}}

        # First turn
        msg1 = ChatMessage(role="user", content="First message")
        langchain_msgs1 = to_langchain_messages([msg1])
        langchain_msgs1.insert(0, SystemMessage(content="You are a helpful and efficient assistant."))
        await self.graph.ainvoke({"messages": langchain_msgs1}, config)

        # Second turn
        msg2 = ChatMessage(role="user", content="Second message")
        langchain_msgs2 = to_langchain_messages([msg2])
        await self.graph.ainvoke({"messages": langchain_msgs2}, config)

        # Retrieve cumulative history
        updated_state = await self.graph.aget_state(config)
        messages = updated_state.values.get("messages", [])

        # Should have: SystemMessage -> HumanMessage 1 -> AIMessage 1 -> HumanMessage 2 -> AIMessage 2
        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[1].content, "First message")
        self.assertEqual(messages[2].content, "Echo: First message")
        self.assertEqual(messages[3].content, "Second message")
        self.assertEqual(messages[4].content, "Echo: Second message")

    async def test_clear_history(self):
        config = {"configurable": {"thread_id": self.thread_id}}

        # Write some message history
        msg = ChatMessage(role="user", content="Hello!")
        langchain_msgs = to_langchain_messages([msg])
        await self.graph.ainvoke({"messages": langchain_msgs}, config)

        # Confirm history is created
        state = await self.graph.aget_state(config)
        self.assertIn("messages", state.values)

        # Clear history from checkpointer
        memory_checkpointer.storage.pop(self.thread_id, None)

        # Confirm history is wiped out
        cleared_state = await self.graph.aget_state(config)
        self.assertEqual(cleared_state.values, {})

    async def test_settings_persistence_in_graph_state(self):
        config = {"configurable": {"thread_id": self.thread_id}}

        # Write messages and settings to the graph state
        await self.graph.aupdate_state(
            config,
            {
                "messages": [SystemMessage(content="Hello")],
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "chatbot_name": "Hal",
                "tone": "mature",
            },
        )

        # Load state snapshot
        state = await self.graph.aget_state(config)

        # Verify all settings are preserved correctly in the checkpointer
        self.assertEqual(state.values.get("provider"), "gemini")
        self.assertEqual(state.values.get("model"), "gemini-2.5-flash")
        self.assertEqual(state.values.get("chatbot_name"), "Hal")
        self.assertEqual(state.values.get("tone"), "mature")

    async def test_history_slicing_limit(self):
        config = {"configurable": {"thread_id": self.thread_id}}

        # Write many messages to exceed MAX_HISTORY_MESSAGES limit
        from orchestrator_agent.system_configuration import MAX_HISTORY_MESSAGES

        # We will create a history with 1 system message and 30 user/assistant messages
        system_msg = SystemMessage(content="System prompt instructions")
        messages: list[BaseMessage] = [system_msg]

        for i in range(15):
            messages.append(HumanMessage(content=f"User msg {i}"))
            messages.append(AIMessage(content=f"AI msg {i}"))

        await self.graph.aupdate_state(config, {"messages": messages})

        # Now run another message through the graph to trigger node invocation
        next_msg = ChatMessage(role="user", content="Next user message")
        await self.graph.ainvoke({"messages": to_langchain_messages([next_msg])}, config)

        # Check what messages were actually passed to the LLM
        invoked = self.llm.invoked_messages

        # The total non-system messages passed should be limited to MAX_HISTORY_MESSAGES
        # plus the system message(s)
        self.assertIsNotNone(invoked)
        assert invoked is not None

        # Filters
        non_system_invoked = [m for m in invoked if not isinstance(m, SystemMessage)]
        system_invoked = [m for m in invoked if isinstance(m, SystemMessage)]

        self.assertEqual(len(system_invoked), 1)
        self.assertEqual(system_invoked[0].content, "System prompt instructions")
        self.assertEqual(len(non_system_invoked), MAX_HISTORY_MESSAGES)
        # The very last message in the invoked list should be our new message
        self.assertEqual(non_system_invoked[-1].content, "Next user message")


if __name__ == "__main__":
    unittest.main()
