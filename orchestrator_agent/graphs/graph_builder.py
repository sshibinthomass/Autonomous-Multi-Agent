import sys
from pathlib import Path

import dotenv
from langgraph.graph import StateGraph

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langgraph.checkpoint.memory import MemorySaver

from orchestrator_agent.graphs.basic_chatbot_graph import basic_chatbot_build_graph
from orchestrator_agent.states.chatbotState import ChatbotState

dotenv.load_dotenv()

# Global checkpointer instance for state/history persistence
memory_checkpointer = MemorySaver()


class GraphBuilder:
    def __init__(self, model):
        self.llm = model
        self.graph_builder = StateGraph(
            ChatbotState
        )  # StateGraph is a class in LangGraph that is used to build the graph

    async def setup_graph(self, usecase: str):
        """
        Sets up the graph for the selected use case.

        Args:
            usecase: The use case to set up ("basic_chatbot")
        """
        if usecase == "basic_chatbot":
            print
            basic_chatbot_build_graph(self.graph_builder, self.llm)
        else:
            raise ValueError(f"Unsupported use case: {usecase}")

        return self.graph_builder.compile(checkpointer=memory_checkpointer)


if __name__ == "__main__":
    import asyncio
    import os

    from langchain_core.messages import HumanMessage, SystemMessage

    from orchestrator_agent.llms.openai_llm import OpenAILLM

    async def main():
        user_controls_input = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "selected_llm": "gpt-4.1-mini",
        }
        llm = OpenAILLM(user_controls_input)
        llm = llm.get_base_llm()

        graph_builder = GraphBuilder(llm)


        # Setup graph with tools
        graph = await graph_builder.setup_graph("basic_chatbot")

        # Create input state for the graph
        initial_state = {
            "messages": [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(
                    content="Use preplexity to give me today's news in india?"
                ),
            ]
        }

        # Run the graph and print the output (use ainvoke for async graph with thread config)
        result = await graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": "cli-test-thread"}}
        )
        print("Graph Output:", result)

    # Run the async main function
    import nest_asyncio

    nest_asyncio.apply()
    asyncio.run(main())
