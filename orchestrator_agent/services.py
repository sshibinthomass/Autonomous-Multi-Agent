import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import HTTPException

# Add project root to sys.path to ensure correct imports
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from orchestrator_agent.graphs.graph_builder import GraphBuilder, memory_checkpointer
from orchestrator_agent.config import get_env_variable
from orchestrator_agent.schemas import ChatMessage
from orchestrator_agent.prompts.prompts import get_basic_chatbot_system_prompt
from orchestrator_agent.session_manager import load_session, save_session, delete_session
from orchestrator_agent.system_configuration import MAX_HISTORY_MESSAGES

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
    elif isinstance(message, ToolMessage):
        role = "tool"
    else:
        role = "user"
        
    content = message.content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        content = "".join(text_parts)
    elif content is None:
        content = ""

    dct = {"role": role, "content": content}
    
    if isinstance(message, AIMessage) and message.tool_calls:
        dct["tool_calls"] = message.tool_calls
    if isinstance(message, ToolMessage):
        dct["tool_call_id"] = message.tool_call_id
        dct["name"] = message.name
    
    timestamp = message.additional_kwargs.get("timestamp")
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message.additional_kwargs["timestamp"] = timestamp
        
    dct["timestamp"] = timestamp
    return dct

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
        additional_kwargs = {"timestamp": msg.timestamp} if msg.timestamp else {}
        if msg.role == "system":
            converted.append(SystemMessage(content=msg.content, additional_kwargs=additional_kwargs))
        elif msg.role == "assistant":
            tool_calls = msg.tool_calls if hasattr(msg, "tool_calls") and msg.tool_calls else []
            converted.append(AIMessage(content=msg.content, tool_calls=tool_calls, additional_kwargs=additional_kwargs))
        elif msg.role == "tool":
            tool_call_id = msg.tool_call_id if hasattr(msg, "tool_call_id") and msg.tool_call_id else ""
            name = msg.name if hasattr(msg, "name") and msg.name else ""
            converted.append(ToolMessage(content=msg.content, tool_call_id=tool_call_id, name=name, additional_kwargs=additional_kwargs))
        else:
            converted.append(HumanMessage(content=msg.content, additional_kwargs=additional_kwargs))
    return converted

async def prepare_chatbot_graph_state(thread_id: str, provider: str, model: str, chatbot_name: str, tone: str):
    """
    Helper function to resolve session settings, instantiate the base LLM, compile the graph,
    and ensure the LangGraph checkpointer is correctly seeded from session JSON if it is empty.
    Returns:
        tuple: (llm, graph, config, state, existing_messages, resolved_settings)
    """
    # Load session settings from disk if they exist to preserve individual session config
    session = load_session(thread_id)
    if session:
        chatbot_name = session.get("chatbot_name", chatbot_name)
        tone = session.get("tone", tone)
        provider = session.get("provider", provider)
        model = session.get("model", model)

    # 1. Instantiate the target LLM
    llm = get_base_llm(provider, model)
    # 2. Build and compile the graph (to resolve checkpointer and configuration)
    builder = GraphBuilder(model=llm)
    graph = await builder.setup_graph("basic_chatbot")
    
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {
            "provider": provider,
            "model": model,
            "chatbot_name": chatbot_name,
            "tone": tone,
            "langfuse_session_id": thread_id,
            "langfuse_trace_name": f"agent-{chatbot_name}"
        },
        "tags": [provider, model, tone]
    }
    
    # 3. Check for existing messages in state
    state = await graph.aget_state(config)
    existing_messages = state.values.get("messages", [])
    
    state_date_time = state.values.get("date_time")
    
    # State Persistence Recovery Guard:
    # Since LangGraph's MemorySaver checkpointer resides entirely in RAM, any server restart 
    # or python process reload (such as hot-reloads) completely clears the checkpointer.
    # To recover context, if the checkpointer has no record of the thread but a persistent JSON
    # history exists on disk, we lazily restore the messages and LLM configuration back 
    # into the checkpointer state. This preserves assistant memory continuity seamlessly.
    if not existing_messages:
        session = load_session(thread_id)
        if session:
            seeded_messages = to_langchain_messages([
                ChatMessage(
                    role=m["role"],
                    content=m["content"],
                    timestamp=m.get("timestamp"),
                    tool_calls=m.get("tool_calls"),
                    tool_call_id=m.get("tool_call_id"),
                    name=m.get("name")
                )
                for m in session.get("messages", [])
            ])
            state_date_time = session.get("date_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await graph.aupdate_state(config, {
                "messages": seeded_messages,
                "provider": session.get("provider", provider),
                "model": session.get("model", model),
                "chatbot_name": session.get("chatbot_name", chatbot_name),
                "tone": session.get("tone", tone),
                "date_time": state_date_time
            }, as_node="chatbot")
            # Reload graph state from the checkpointer to capture the newly seeded values
            state = await graph.aget_state(config)
            existing_messages = state.values.get("messages", [])
            
    if not state_date_time:
        state_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    resolved_settings = {
        "provider": provider,
        "model": model,
        "chatbot_name": chatbot_name,
        "tone": tone,
        "date_time": state_date_time
    }
    return llm, graph, config, state, existing_messages, resolved_settings

async def execute_chatbot_graph(message: ChatMessage, provider: str, model: str, thread_id: str = "default", prompt_config: dict = None):
    """
    Initializes the required base LLM, compiles the basic chatbot StateGraph,
    streams response tokens from the LLM, and updates the memory checkpointer
    and session history on disk once complete.
    Yields standard Server-Sent Events (SSE).
    """
    if prompt_config is None:
        prompt_config = {}
    chatbot_name = prompt_config.get("chatbot_name", "Jarvis")
    tone = prompt_config.get("tone", "friendly")

    # Call unified helper to resolve LLM, compile graph, and seed checkpointer if needed
    llm, graph, config, state, existing_messages, settings = await prepare_chatbot_graph_state(
        thread_id=thread_id,
        provider=provider,
        model=model,
        chatbot_name=chatbot_name,
        tone=tone
    )
    resolved_provider = settings["provider"]
    resolved_model = settings["model"]
    resolved_chatbot_name = settings["chatbot_name"]
    resolved_tone = settings["tone"]
    
    # Setup optional Langfuse tracing callback for graph execution
    lf_public = get_env_variable("LANGFUSE_PUBLIC_KEY")
    lf_secret = get_env_variable("LANGFUSE_SECRET_KEY")
    if lf_public and lf_secret:
        try:
            from langfuse.langchain import CallbackHandler
            lf_handler = CallbackHandler()
            config["callbacks"] = [lf_handler]
            print(f"Langfuse tracing enabled for session: {thread_id}")
        except Exception as e:
            print(f"Failed to initialize Langfuse callback handler: {e}")

    # 4. Prepare new messages
    langchain_messages = to_langchain_messages([message])
    if not existing_messages:
        # If thread is empty, prepend a default system prompt if not already present
        if not any(isinstance(m, SystemMessage) for m in langchain_messages):
            prompt = get_basic_chatbot_system_prompt(name=resolved_chatbot_name, tone=resolved_tone)
            langchain_messages.insert(0, SystemMessage(content=prompt))
            
    input_state = {
        "messages": langchain_messages,
        "provider": resolved_provider,
        "model": resolved_model,
        "chatbot_name": resolved_chatbot_name,
        "tone": resolved_tone
    }

    # 5. Stream the response using graph.astream_events
    try:
        async for event in graph.astream_events(input_state, config, version="v2"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            elif kind == "on_tool_start":
                name = event["name"]
                inputs = event["data"].get("input", {})
                yield f"data: {json.dumps({'type': 'tool_start', 'name': name, 'inputs': inputs})}\n\n"
            elif kind == "on_tool_end":
                name = event["name"]
                output = event["data"].get("output")
                if hasattr(output, "content"):
                    output_str = output.content
                else:
                    output_str = str(output)
                yield f"data: {json.dumps({'type': 'tool_end', 'name': name, 'output': output_str})}\n\n"
    except Exception as e:
        print(f"Error during graph streaming, invoking graph: {e}")
        await graph.ainvoke(input_state, config)

    # 6. Save current settings in state checkpoint
    current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state_config = {k: v for k, v in config.items() if k != "callbacks"}
    await graph.aupdate_state(state_config, {
        "provider": resolved_provider,
        "model": resolved_model,
        "chatbot_name": resolved_chatbot_name,
        "tone": resolved_tone,
        "date_time": current_dt
    }, as_node="chatbot")
    
    # 7. Retrieve full updated messages and settings state
    updated_state = await graph.aget_state(state_config)
    all_messages = updated_state.values.get("messages", [])
    
    # Save/update session on disk
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
        provider=resolved_provider,
        model=resolved_model,
        chatbot_name=resolved_chatbot_name,
        tone=resolved_tone,
        date_time=updated_state.values.get("date_time", current_dt),
        created_at=created_at
    )
    
    final_data = {
        "type": "done",
        "messages": [to_chat_dict(m) for m in all_messages],
        "settings": {
            "provider": updated_state.values.get("provider", resolved_provider),
            "model": updated_state.values.get("model", resolved_model),
            "chatbot_name": updated_state.values.get("chatbot_name", resolved_chatbot_name),
            "tone": updated_state.values.get("tone", resolved_tone),
            "date_time": updated_state.values.get("date_time", current_dt)
        }
    }
    yield f"data: {json.dumps(final_data)}\n\n"

async def get_chatbot_history(provider: str, model: str, thread_id: str = "default", prompt_config: dict = None) -> dict:
    """
    Retrieves the full conversation history and saved settings for a thread.
    If it doesn't exist, initializes it with a default system message and settings.
    """
    if prompt_config is None:
        prompt_config = {}
    chatbot_name = prompt_config.get("chatbot_name", "Jarvis")
    tone = prompt_config.get("tone", "friendly")

    # Call unified helper to resolve LLM, compile graph, and seed checkpointer if needed
    llm, graph, config, state, messages, settings = await prepare_chatbot_graph_state(
        thread_id=thread_id,
        provider=provider,
        model=model,
        chatbot_name=chatbot_name,
        tone=tone
    )
    resolved_provider = settings["provider"]
    resolved_model = settings["model"]
    resolved_chatbot_name = settings["chatbot_name"]
    resolved_tone = settings["tone"]

    # Seed with system message if thread is completely empty (no checkpointer and no JSON session on disk)
    if not messages:
        # Initialize system message in state & disk
        prompt = get_basic_chatbot_system_prompt(name=resolved_chatbot_name, tone=resolved_tone)
        system_msg = SystemMessage(content=prompt)
        current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await graph.aupdate_state(config, {
            "messages": [system_msg],
            "provider": resolved_provider,
            "model": resolved_model,
            "chatbot_name": resolved_chatbot_name,
            "tone": resolved_tone,
            "date_time": current_dt
        }, as_node="chatbot")
        state = await graph.aget_state(config)
        messages = [system_msg]
        
        save_session(
            thread_id=thread_id,
            name="New Chat",
            messages=[to_chat_dict(system_msg)],
            provider=resolved_provider,
            model=resolved_model,
            chatbot_name=resolved_chatbot_name,
            tone=resolved_tone,
            date_time=current_dt
        )
            
    # B. If thread was previously active and has saved settings, dynamically reload/compile with those settings!
    saved_provider = state.values.get("provider")
    saved_model = state.values.get("model")
    if saved_provider and saved_model and (saved_provider != resolved_provider or saved_model != resolved_model):
        llm, graph, config, state, messages, settings = await prepare_chatbot_graph_state(
            thread_id=thread_id,
            provider=saved_provider,
            model=saved_model,
            chatbot_name=resolved_chatbot_name,
            tone=resolved_tone
        )
        # Re-resolve active settings
        resolved_provider = settings["provider"]
        resolved_model = settings["model"]
        
    # Check if we need to dynamically update the system prompt in the checkpointer
    saved_chatbot_name = state.values.get("chatbot_name")
    saved_tone = state.values.get("tone")
    if messages and (saved_chatbot_name != resolved_chatbot_name or saved_tone != resolved_tone):
        for msg in messages:
            if isinstance(msg, SystemMessage):
                new_prompt = get_basic_chatbot_system_prompt(name=resolved_chatbot_name, tone=resolved_tone)
                msg.content = new_prompt
                await graph.aupdate_state(config, {
                    "messages": [msg],
                    "chatbot_name": resolved_chatbot_name,
                    "tone": resolved_tone
                }, as_node="chatbot")
                break
        # Reload state to fetch the updated messages
        state = await graph.aget_state(config)
        messages = state.values.get("messages", [])
        
        # Keep JSON file in sync with system prompt update
        existing_session = load_session(thread_id)
        name = existing_session.get("name", "New Chat") if existing_session else "New Chat"
        created_at = existing_session.get("created_at") if existing_session else None
        save_session(
            thread_id=thread_id,
            name=name,
            messages=[to_chat_dict(m) for m in messages],
            provider=state.values.get("provider", resolved_provider),
            model=state.values.get("model", resolved_model),
            chatbot_name=resolved_chatbot_name,
            tone=resolved_tone,
            date_time=state.values.get("date_time", settings["date_time"]),
            created_at=created_at
        )
        
    return {
        "messages": [to_chat_dict(m) for m in messages],
        "settings": {
            "provider": state.values.get("provider", resolved_provider),
            "model": state.values.get("model", resolved_model),
            "chatbot_name": state.values.get("chatbot_name", resolved_chatbot_name),
            "tone": state.values.get("tone", resolved_tone),
            "date_time": state.values.get("date_time", settings["date_time"])
        }
    }

def clear_chatbot_history(thread_id: str) -> None:
    """
    Removes a thread and its message history from memory checkpointer storage and disk.
    """
    memory_checkpointer.storage.pop(thread_id, None)
    delete_session(thread_id)
