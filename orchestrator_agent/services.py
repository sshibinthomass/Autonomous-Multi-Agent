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
from orchestrator_agent.prompts.prompts import get_basic_chatbot_system_prompt

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

async def execute_chatbot_graph(messages: List[ChatMessage], provider: str, model: str, thread_id: str = "default", prompt_config: dict = None) -> dict:
    """
    Initializes the required base LLM, compiles the basic chatbot StateGraph,
    runs it asynchronously using ainvoke with a checkpointer, and returns the full message history and settings.
    """
    if prompt_config is None:
        prompt_config = {}
    chatbot_name = prompt_config.get("chatbot_name", "Jarvis")
    tone = prompt_config.get("tone", "friendly")

    # Load session settings from disk if they exist to preserve individual session config
    from orchestrator_agent.session_manager import load_session
    session = load_session(thread_id)
    if session:
        chatbot_name = session.get("chatbot_name", chatbot_name)
        tone = session.get("tone", tone)
        provider = session.get("provider", provider)
        model = session.get("model", model)

    # 1. Instantiate the target LLM
    llm = get_base_llm(provider, model)
    # 2. Build and compile the graph
    builder = GraphBuilder(model=llm)
    graph = await builder.setup_graph("basic_chatbot")
    
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {
            "provider": provider,
            "model": model,
            "chatbot_name": chatbot_name,
            "tone": tone
        },
        "tags": [provider, model, tone]
    }
    
    # 3. Check for existing messages in state
    state = await graph.aget_state(config)
    existing_messages = state.values.get("messages", [])
    
    # Seed checkpointer from session JSON if memory is empty
    if not existing_messages:
        from orchestrator_agent.session_manager import load_session
        session = load_session(thread_id)
        if session:
            seeded_messages = to_langchain_messages([
                ChatMessage(role=m["role"], content=m["content"])
                for m in session.get("messages", [])
            ])
            await graph.aupdate_state(config, {
                "messages": seeded_messages,
                "provider": session.get("provider", provider),
                "model": session.get("model", model),
                "chatbot_name": session.get("chatbot_name", chatbot_name),
                "tone": session.get("tone", tone)
            })
            # Reload state
            state = await graph.aget_state(config)
            existing_messages = state.values.get("messages", [])
    
    # 4. Prepare new messages
    langchain_messages = to_langchain_messages(messages)
    if not existing_messages:
        # If thread is empty, prepend a default system prompt if not already present
        if not any(isinstance(m, SystemMessage) for m in langchain_messages):
            prompt = get_basic_chatbot_system_prompt(name=chatbot_name, tone=tone)
            langchain_messages.insert(0, SystemMessage(content=prompt))
            
    # 5. Execute state graph asynchronously
    await graph.ainvoke({"messages": langchain_messages}, config)
    
    # 6. Save current settings in state checkpoint
    await graph.aupdate_state(config, {
        "provider": provider,
        "model": model,
        "chatbot_name": chatbot_name,
        "tone": tone
    })
    
    # 7. Retrieve full updated messages and settings state
    updated_state = await graph.aget_state(config)
    all_messages = updated_state.values.get("messages", [])
    
    # Save/update session on disk
    from orchestrator_agent.session_manager import load_session, save_session
    existing_session = load_session(thread_id)
    
    if existing_session and existing_session.get("name") != "New Chat":
        name = existing_session.get("name")
        created_at = existing_session.get("created_at")
    else:
        # Generate name from first user message
        user_messages = [m for m in all_messages if isinstance(m, HumanMessage)]
        if user_messages:
            first_content = user_messages[0].content
            name = first_content[:40] + ("..." if len(first_content) > 40 else "")
        else:
            name = "New Chat"
        created_at = existing_session.get("created_at") if existing_session else None
        
    save_session(
        thread_id=thread_id,
        name=name,
        messages=[to_chat_dict(m) for m in all_messages],
        provider=provider,
        model=model,
        chatbot_name=chatbot_name,
        tone=tone,
        created_at=created_at
    )
    
    return {
        "messages": [to_chat_dict(m) for m in all_messages],
        "settings": {
            "provider": updated_state.values.get("provider", provider),
            "model": updated_state.values.get("model", model),
            "chatbot_name": updated_state.values.get("chatbot_name", chatbot_name),
            "tone": updated_state.values.get("tone", tone)
        }
    }

async def get_chatbot_history(provider: str, model: str, thread_id: str = "default", prompt_config: dict = None) -> dict:
    """
    Retrieves the full conversation history and saved settings for a thread.
    If it doesn't exist, initializes it with a default system message and settings.
    """
    if prompt_config is None:
        prompt_config = {}
    chatbot_name = prompt_config.get("chatbot_name", "Jarvis")
    tone = prompt_config.get("tone", "friendly")

    # Load session settings from disk if they exist to preserve individual session config
    from orchestrator_agent.session_manager import load_session
    session = load_session(thread_id)
    if session:
        chatbot_name = session.get("chatbot_name", chatbot_name)
        tone = session.get("tone", tone)
        provider = session.get("provider", provider)
        model = session.get("model", model)

    # A. Compile with default parameters to pull the initial state snapshot
    llm = get_base_llm(provider, model)
    builder = GraphBuilder(model=llm)
    graph = await builder.setup_graph("basic_chatbot")
    config = {"configurable": {"thread_id": thread_id}}
    
    state = await graph.aget_state(config)
    messages = state.values.get("messages", [])
    
    # Load from JSON if checkpointer is empty (e.g. server restarted)
    if not messages:
        from orchestrator_agent.session_manager import load_session, save_session
        session = load_session(thread_id)
        if session:
            msgs_to_seed = to_langchain_messages([
                ChatMessage(role=m["role"], content=m["content"])
                for m in session.get("messages", [])
            ])
            await graph.aupdate_state(config, {
                "messages": msgs_to_seed,
                "provider": session.get("provider", provider),
                "model": session.get("model", model),
                "chatbot_name": session.get("chatbot_name", chatbot_name),
                "tone": session.get("tone", tone)
            })
            state = await graph.aget_state(config)
            messages = state.values.get("messages", [])
        else:
            # Initialize system message in state & disk
            prompt = get_basic_chatbot_system_prompt(name=chatbot_name, tone=tone)
            system_msg = SystemMessage(content=prompt)
            await graph.aupdate_state(config, {
                "messages": [system_msg],
                "provider": provider,
                "model": model,
                "chatbot_name": chatbot_name,
                "tone": tone
            })
            state = await graph.aget_state(config)
            messages = [system_msg]
            
            save_session(
                thread_id=thread_id,
                name="New Chat",
                messages=[to_chat_dict(system_msg)],
                provider=provider,
                model=model,
                chatbot_name=chatbot_name,
                tone=tone
            )
            
    # B. If thread was previously active and has saved settings, dynamically reload/compile with those settings!
    saved_provider = state.values.get("provider")
    saved_model = state.values.get("model")
    if saved_provider and saved_model and (saved_provider != provider or saved_model != model):
        llm = get_base_llm(saved_provider, saved_model)
        builder = GraphBuilder(model=llm)
        graph = await builder.setup_graph("basic_chatbot")
        state = await graph.aget_state(config)
        messages = state.values.get("messages", [])
        
    # Check if we need to dynamically update the system prompt in the checkpointer
    saved_chatbot_name = state.values.get("chatbot_name")
    saved_tone = state.values.get("tone")
    if messages and (saved_chatbot_name != chatbot_name or saved_tone != tone):
        for msg in messages:
            if isinstance(msg, SystemMessage):
                new_prompt = get_basic_chatbot_system_prompt(name=chatbot_name, tone=tone)
                msg.content = new_prompt
                await graph.aupdate_state(config, {
                    "messages": [msg],
                    "chatbot_name": chatbot_name,
                    "tone": tone
                })
                break
        # Reload state to fetch the updated messages
        state = await graph.aget_state(config)
        messages = state.values.get("messages", [])
        
        # Keep JSON file in sync with system prompt update
        from orchestrator_agent.session_manager import load_session, save_session
        existing_session = load_session(thread_id)
        name = existing_session.get("name", "New Chat") if existing_session else "New Chat"
        created_at = existing_session.get("created_at") if existing_session else None
        save_session(
            thread_id=thread_id,
            name=name,
            messages=[to_chat_dict(m) for m in messages],
            provider=state.values.get("provider", provider),
            model=state.values.get("model", model),
            chatbot_name=chatbot_name,
            tone=tone,
            created_at=created_at
        )
        
    return {
        "messages": [to_chat_dict(m) for m in messages],
        "settings": {
            "provider": state.values.get("provider", provider),
            "model": state.values.get("model", model),
            "chatbot_name": state.values.get("chatbot_name", chatbot_name),
            "tone": state.values.get("tone", tone)
        }
    }

def clear_chatbot_history(thread_id: str) -> None:
    """
    Removes a thread and its message history from memory checkpointer storage and disk.
    """
    memory_checkpointer.storage.pop(thread_id, None)
    
    from orchestrator_agent.session_manager import delete_session
    delete_session(thread_id)

