import sys
from pathlib import Path
import unittest
import asyncio

# Setup sys.path to find project root
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from orchestrator_agent.graphs.graph_builder import GraphBuilder, memory_checkpointer
from orchestrator_agent.services import to_langchain_messages, to_chat_dict
from orchestrator_agent.schemas import ChatMessage

class MockLLM:
    """
    A lightweight Mock LLM to test LangGraph memory operations without external API calls.
    """
    def invoke(self, messages):
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

if __name__ == "__main__":
    unittest.main()
