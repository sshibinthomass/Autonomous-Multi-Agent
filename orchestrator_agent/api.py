import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Ensure the project root is in python path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import modular layers
from orchestrator_agent.config import AVAILABLE_MODELS
from orchestrator_agent.config import TONES
from orchestrator_agent.schemas import ChatRequest, PromptConfig
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
    Receives current message history and runs it through the LangGraph StateGraph pipeline.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")

    try:
        # Run graph execution service
        all_messages = await execute_chatbot_graph(
            messages=request.messages,
            provider=request.provider,
            model=request.model,
            thread_id=request.thread_id,
            prompt_config=request.prompt_config.dict()
        )
        return all_messages
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
