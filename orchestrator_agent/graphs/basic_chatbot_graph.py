import sys
from pathlib import Path

from langgraph.graph import START
from langgraph.prebuilt import ToolNode, tools_condition

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from orchestrator_agent.nodes.basic_chatbot_node import BasicChatbotNode
from orchestrator_agent.tools.math_tools import math_tools


def basic_chatbot_build_graph(graph_builder, llm):
    """
    Builds a basic chatbot graph using LangGraph.
    This method initializes a chatbot node with tools bound, adds a ToolNode,
    and handles routing via tools_condition.
    """
    # 1. Bind mathematical tools to the base LLM instance
    llm_with_tools = llm.bind_tools(math_tools)
    
    # 2. Instantiate basic chatbot node with both base and tools-enabled LLMs
    basic_chatbot_node = BasicChatbotNode(llm, llm_with_tools)

    # 3. Add nodes
    graph_builder.add_node("chatbot", basic_chatbot_node.process)
    graph_builder.add_node("tools", ToolNode(math_tools))
    
    # 4. Add edges
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")
