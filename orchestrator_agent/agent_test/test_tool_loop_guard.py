import sys
import unittest
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from orchestrator_agent.graphs.graph_builder import GraphBuilder, memory_checkpointer
from orchestrator_agent.system_configuration import MAX_TOOL_ITERATIONS


class ToolsBoundLLM:
    def __init__(self, base: "LoopingToolLLM"):
        self.base = base

    def invoke(self, messages):
        self.base.tool_rounds += 1
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "add",
                    "args": {"a": self.base.tool_rounds, "b": 1},
                    "id": f"call_{self.base.tool_rounds}",
                }
            ],
        )


class LoopingToolLLM:
    """Always requests another tool call until forced onto the base LLM."""

    def __init__(self):
        self.calls = 0
        self.tool_rounds = 0

    def bind_tools(self, tools):
        self.tools = tools
        return ToolsBoundLLM(self)

    def invoke(self, messages):
        self.calls += 1
        tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
        latest = tool_msgs[-1].content if tool_msgs else "unknown"
        return AIMessage(content=f"Final answer after tools: {latest}")


class TestToolLoopGuard(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.llm = LoopingToolLLM()
        self.builder = GraphBuilder(model=self.llm)
        self.graph = await self.builder.setup_graph("basic_chatbot")
        self.thread_id = "test-tool-loop-guard"

    async def asyncTearDown(self):
        memory_checkpointer.storage.pop(self.thread_id, None)

    async def test_graph_stops_after_max_tool_iterations(self):
        config = {"configurable": {"thread_id": self.thread_id}}
        initial_state = {
            "messages": [
                SystemMessage(content="You are a helpful math assistant."),
                HumanMessage(content="Keep adding 1 forever"),
            ]
        }

        await self.graph.ainvoke(initial_state, config)
        state = await self.graph.aget_state(config)
        messages = state.values.get("messages", [])
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

        self.assertEqual(len(tool_messages), MAX_TOOL_ITERATIONS)
        self.assertEqual(messages[-1].content, "Final answer after tools: 11.0")


if __name__ == "__main__":
    unittest.main()
