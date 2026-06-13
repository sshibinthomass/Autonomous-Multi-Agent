import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure the project root is in python path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import modular layers
from orchestrator_agent.config import AVAILABLE_MODELS
from orchestrator_agent.config import TONES
from orchestrator_agent.schemas import (
    ChatRequest,
    PromptConfig,
    CreateSessionRequest,
    RenameSessionRequest,
    UpdateSettingsRequest
)
from orchestrator_agent.services import execute_chatbot_graph, get_chatbot_history, clear_chatbot_history

# Initialize FastAPI application
app = FastAPI(
    title="Autonomous Multi-Agent Orchestrator API",
    description="Clean, modular API for running agent StateGraphs.",
    version="2.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/settings")
def get_settings():
    """
    Exposes available providers, models, and tone options.
    This lets the React frontend dynamically build settings dropdowns.
    """
    return {
        "providers": {
            provider: {
                "models": AVAILABLE_MODELS[provider]
            }
            for provider in AVAILABLE_MODELS
        },
        "tones": TONES
    }

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Receives current message and runs it through the LangGraph StateGraph pipeline,
    streaming response tokens chunk-by-chunk using Server-Sent Events (SSE).
    """
    try:
        # Run streaming graph execution service
        generator = execute_chatbot_graph(
            message=request.message,
            provider=request.provider,
            model=request.model,
            thread_id=request.thread_id,
            prompt_config=request.prompt_config.dict()
        )
        return StreamingResponse(generator, media_type="text/event-stream")
        
    except HTTPException as he:
        raise he
    except Exception as e:
        # Gracefully handle validation and runtime exceptions
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/{thread_id}/history")
async def get_history(thread_id: str, provider: str, model: str, prompt_config: PromptConfig = Depends()):
    """
    Fetches existing conversation history for a given thread.
    Uses PromptConfig (query params: chatbot_name, tone) — same schema as POST /chat.
    """
    try:
        history = await get_chatbot_history(provider, model, thread_id, prompt_config.dict())
        return history
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/{thread_id}/clear")
def clear_history(thread_id: str):
    """
    Wipes the conversation history snapshot for the thread from the backend checkpointer.
    """
    try:
        clear_chatbot_history(thread_id)
        return {"status": "success", "detail": f"History for thread {thread_id} cleared."}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
def get_sessions_list():
    """
    Lists all available chat sessions on disk.
    """
    try:
        from orchestrator_agent.session_manager import list_sessions
        return list_sessions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions")
def create_new_session(req: CreateSessionRequest):
    """
    Creates a brand new empty session and returns it.
    """
    try:
        import uuid
        from orchestrator_agent.session_manager import save_session
        from orchestrator_agent.prompts.prompts import get_basic_chatbot_system_prompt
        
        thread_id = f"thread-{uuid.uuid4().hex[:12]}"
        prompt = get_basic_chatbot_system_prompt(name=req.chatbot_name, tone=req.tone)
        system_message = {"role": "system", "content": prompt}
        
        session = save_session(
            thread_id=thread_id,
            name="New Chat",
            messages=[system_message],
            provider=req.provider,
            model=req.model,
            chatbot_name=req.chatbot_name,
            tone=req.tone
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{thread_id}/rename")
def rename_existing_session(thread_id: str, req: RenameSessionRequest):
    """
    Renames a session JSON file on disk.
    """
    try:
        from orchestrator_agent.session_manager import rename_session
        session = rename_session(thread_id, req.name)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{thread_id}")
def delete_existing_session(thread_id: str):
    """
    Deletes the session on disk and clears from checkpointer.
    """
    try:
        from orchestrator_agent.session_manager import delete_session
        from orchestrator_agent.services import clear_chatbot_history
        
        deleted = delete_session(thread_id)
        clear_chatbot_history(thread_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "success", "detail": f"Session {thread_id} deleted."}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/sessions/{thread_id}/settings")
async def update_session_settings(thread_id: str, req: UpdateSettingsRequest):
    """
    Updates the LLM settings (provider, model, chatbot_name, tone) of an active session.
    Also synchronizes the state checkpointer and system prompt.
    """
    import time
    try:
        from orchestrator_agent.session_manager import load_session, save_session
        from orchestrator_agent.services import get_base_llm
        from orchestrator_agent.graphs.graph_builder import GraphBuilder
        
        session = load_session(thread_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if req.provider is not None:
            session["provider"] = req.provider
        if req.model is not None:
            session["model"] = req.model
        if req.chatbot_name is not None:
            session["chatbot_name"] = req.chatbot_name
        if req.tone is not None:
            session["tone"] = req.tone
            
        # Re-save to disk
        save_session(
            thread_id=thread_id,
            name=session.get("name", "New Chat"),
            messages=session["messages"],
            provider=session["provider"],
            model=session["model"],
            chatbot_name=session["chatbot_name"],
            tone=session["tone"],
            date_time=session.get("date_time"),
            created_at=session.get("created_at"),
            updated_at=time.time()
        )
        
        # Synchronize checkpointer memory
        llm = get_base_llm(session["provider"], session["model"])
        builder = GraphBuilder(model=llm)
        graph = await builder.setup_graph("basic_chatbot")
        config = {"configurable": {"thread_id": thread_id}}
        
        # Re-fetch state and update messages if prompt settings changed
        state = await graph.aget_state(config)
        messages = state.values.get("messages", [])
        if messages:
            from orchestrator_agent.prompts.prompts import get_basic_chatbot_system_prompt
            from langchain_core.messages import SystemMessage
            # Update system message content
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    new_prompt = get_basic_chatbot_system_prompt(name=session["chatbot_name"], tone=session["tone"])
                    msg.content = new_prompt
                    break
            
            await graph.aupdate_state(config, {
                "messages": messages,
                "provider": session["provider"],
                "model": session["model"],
                "chatbot_name": session["chatbot_name"],
                "tone": session["tone"],
                "date_time": session.get("date_time")
            }, as_node="chatbot")
        else:
            await graph.aupdate_state(config, {
                "provider": session["provider"],
                "model": session["model"],
                "chatbot_name": session["chatbot_name"],
                "tone": session["tone"],
                "date_time": session.get("date_time")
            }, as_node="chatbot")
            
        return session
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
