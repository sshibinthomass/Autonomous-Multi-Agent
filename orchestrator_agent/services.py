import sys
from pathlib import Path
from typing import List, Optional
from fastapi import HTTPException

# Add project root to sys.path to ensure correct imports
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from orchestrator_agent.graphs.graph_builder import GraphBuilder, memory_checkpointer
from orchestrator_agent.config import get_env_variable
from orchestrator_agent.schemas import ChatMessage

# Import LLM wrappers
from orchestrator_agent.llms.openai_llm import OpenAILLM
from orchestrator_agent.llms.gemini_llm import GeminiLLM
from orchestrator_agent.llms.groq_llm import GroqLLM
from orchestrator_agent.llms.anthropic_llm import AnthropicLLM
from orchestrator_agent.llms.ollama_llm import OllamaLLM

def to_chat_dict(message) -> dict:
    """
    Converts standard LangChain Message objects to standard dictionary format for API delivery.
    """
    if isinstance(message, SystemMessage):
        role = "system"
    elif isinstance(message, AIMessage):
        role = "assistant"
    else:
        role = "user"
    return {"role": role, "content": message.content}

def get_base_llm(provider: str, model: str):
    """
    Dynamically maps a provider name and specific model selection to its corresponding
    LangChain wrapper class, loading credentials from .env.
    """
    controls = {"selected_llm": model}
    
    if provider == "openai":
        controls["OPENAI_API_KEY"] = get_env_variable("OPENAI_API_KEY")
        if not controls["OPENAI_API_KEY"]:
            raise HTTPException(status_code=400, detail="OpenAI API Key is missing. Add it to .env.")
        return OpenAILLM(controls).get_base_llm()
        
    elif provider == "gemini":
        controls["GEMINI_API_KEY"] = get_env_variable("GEMINI_API_KEY")
        if not controls["GEMINI_API_KEY"]:
            raise HTTPException(status_code=400, detail="Gemini API Key is missing. Add it to .env.")
        return GeminiLLM(controls).get_base_llm()
        
    elif provider == "groq":
        controls["GROQ_API_KEY"] = get_env_variable("GROQ_API_KEY")
        if not controls["GROQ_API_KEY"]:
            raise HTTPException(status_code=400, detail="Groq API Key is missing. Add it to .env.")
        return GroqLLM(controls).get_base_llm()
        
    elif provider == "anthropic":
        controls["ANTHROPIC_API_KEY"] = get_env_variable("ANTHROPIC_API_KEY")
        if not controls["ANTHROPIC_API_KEY"]:
            raise HTTPException(status_code=400, detail="Anthropic API Key is missing. Add it to .env.")
        return AnthropicLLM(controls).get_base_llm()
        
    elif provider == "ollama":
        controls["OLLAMA_BASE_URL"] = get_env_variable("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaLLM(controls).get_base_llm()
        
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}")

def to_langchain_messages(messages: List[ChatMessage]):
    """
    Transforms Pydantic ChatMessage objects (coming from API requests)
    into standard LangChain Message objects (required by GraphBuilder).
    """
    converted = []
    for msg in messages:
        if msg.role == "system":
            converted.append(SystemMessage(content=msg.content))
        elif msg.role == "assistant":
            converted.append(AIMessage(content=msg.content))
        else:
            converted.append(HumanMessage(content=msg.content))
    return converted

async def execute_chatbot_graph(messages: List[ChatMessage], provider: str, model: str, thread_id: str = "default") -> List[dict]:
    """
    Initializes the required base LLM, compiles the basic chatbot StateGraph,
    runs it asynchronously using ainvoke with a checkpointer, and returns the full message history.
    """
    # 1. Instantiate the target LLM
    llm = get_base_llm(provider, model)
    
    # 2. Build and compile the graph
    builder = GraphBuilder(model=llm)
    graph = await builder.setup_graph("basic_chatbot")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # 3. Check for existing messages in state
    state = await graph.aget_state(config)
    existing_messages = state.values.get("messages", [])
    
    # 4. Prepare new messages
    langchain_messages = to_langchain_messages(messages)
    if not existing_messages:
        # If thread is empty, prepend a default system prompt if not already present
        if not any(isinstance(m, SystemMessage) for m in langchain_messages):
            langchain_messages.insert(0, SystemMessage(content="You are a helpful and efficient assistant."))
            
    # 5. Execute state graph asynchronously
    await graph.ainvoke({"messages": langchain_messages}, config)
    
    # 6. Retrieve full updated messages state
    updated_state = await graph.aget_state(config)
    all_messages = updated_state.values.get("messages", [])
    
    return [to_chat_dict(m) for m in all_messages]

async def get_chatbot_history(provider: str, model: str, thread_id: str = "default") -> List[dict]:
    """
    Retrieves the full conversation history for a thread.
    If it doesn't exist, initializes it with a default system message.
    """
    llm = get_base_llm(provider, model)
    builder = GraphBuilder(model=llm)
    graph = await builder.setup_graph("basic_chatbot")
    config = {"configurable": {"thread_id": thread_id}}
    
    state = await graph.aget_state(config)
    messages = state.values.get("messages", [])
    
    if not messages:
        system_msg = SystemMessage(content="You are a helpful and efficient assistant.")
        await graph.aupdate_state(config, {"messages": [system_msg]})
        messages = [system_msg]
        
    return [to_chat_dict(m) for m in messages]

def clear_chatbot_history(thread_id: str) -> None:
    """
    Removes a thread and its message history from memory checkpointer storage.
    """
    memory_checkpointer.storage.pop(thread_id, None)
