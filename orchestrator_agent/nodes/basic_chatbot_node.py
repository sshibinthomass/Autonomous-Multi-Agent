import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from orchestrator_agent.states.chatbotState import ChatbotState
from langchain_core.messages import AIMessage, SystemMessage
from orchestrator_agent.system_configuration import MAX_HISTORY_MESSAGES

load_dotenv()


class BasicChatbotNode:
    """
    Basic Chatbot login implementation
    """

    def __init__(self, model):
        self.llm = model

    def process(self, state: ChatbotState) -> dict:
        """
        Processes the input state and generates a chatbot response.
        Returns the AI response as an AIMessage object to maintain conversation history.
        """
        messages = state.get("messages", [])
        system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
        other_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]
        
        # Keep only the last MAX_HISTORY_MESSAGES messages, discarding any orphaned ToolMessages
        # whose preceding AIMessage with tool_calls was sliced out.
        temp_slice = other_messages[-MAX_HISTORY_MESSAGES:]
        
        from langchain_core.messages import AIMessage, ToolMessage
        aimsg_tool_ids = set()
        for msg in temp_slice:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    if "id" in tc:
                        aimsg_tool_ids.add(tc["id"])
                        
        last_orphan_idx = -1
        for i, msg in enumerate(temp_slice):
            if isinstance(msg, ToolMessage):
                if msg.tool_call_id not in aimsg_tool_ids:
                    last_orphan_idx = i
                    
        if last_orphan_idx != -1:
            sliced_other = temp_slice[last_orphan_idx + 1:]
        else:
            sliced_other = temp_slice
        
        # Combine system messages (which control chatbot personality/settings) and the sliced messages
        input_messages = system_messages + sliced_other

        response = self.llm.invoke(input_messages)

        # Error handling for the response
        # If response is already an AIMessage, return it directly
        if hasattr(response, "content") and hasattr(response, "type"):
            # It's already a message object (AIMessage)
            return {"messages": [response]}
        # If response is a dict with 'content', create AIMessage
        if isinstance(response, dict) and "content" in response:
            return {"messages": [AIMessage(content=response["content"])]}
        # If response is a string, wrap it in AIMessage
        if isinstance(response, str):
            return {"messages": [AIMessage(content=response)]}
        # Fallback: try to extract content and create AIMessage
        if hasattr(response, "content"):
            return {"messages": [AIMessage(content=response.content)]}
        # Last resort: convert to string
        return {"messages": [AIMessage(content=str(response))]}


if __name__ == "__main__":
    from orchestrator_agent.llms.groq_llm import GroqLLM
    from langchain_core.messages import HumanMessage, SystemMessage

    # Create LLM instance
    user_controls_input = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "selected_llm": "openai/gpt-oss-20b",
    }
    llm = GroqLLM(user_controls_input)
    llm = llm.get_base_llm()

    # Create RestaurantRecommendationNode instance with the LLM
    node = BasicChatbotNode(llm)

    # Example conversation history
    state = {
        "messages": [
            SystemMessage(content="You are a helpful and efficient assistant."),
            HumanMessage(content="Hi"),
        ]
    }

    # Call the search_node method and print the result
    result = node.process(state)
    print("Basic Chatbot Node Result:", result)
