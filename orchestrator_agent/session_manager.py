import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_session_dir() -> Path:
    """
    Ensures the session history storage directory exists and returns it.
    """
    p = Path(__file__).resolve().parent / "stores" / "session_history"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_session_path(thread_id: str) -> Path:
    """
    Returns the file path for a given thread_id, preventing directory traversal.
    """
    safe_id = Path(thread_id).name
    return get_session_dir() / f"{safe_id}.json"


def load_session(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Loads and returns session data for a thread_id if the file exists.
    """
    path = get_session_path(thread_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session {thread_id}: {e}")
    return None


def save_session(
    thread_id: str,
    name: str,
    messages: List[Dict[str, str]],
    provider: str,
    model: str,
    chatbot_name: str,
    tone: str,
    date_time: Optional[str] = None,
    created_at: Optional[float] = None,
    updated_at: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Saves or updates a session configuration and history in a JSON file.
    """
    path = get_session_path(thread_id)
    now = time.time()

    session_data = {
        "id": thread_id,
        "name": name,
        "created_at": created_at or now,
        "updated_at": updated_at or now,
        "provider": provider,
        "model": model,
        "chatbot_name": chatbot_name,
        "tone": tone,
        "date_time": date_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": messages,
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving session {thread_id}: {e}")
    return session_data


def list_sessions() -> List[Dict[str, Any]]:
    """
    Lists the metadata of all saved sessions from the session_history directory,
    sorted by updated_at descending.
    """
    sessions = []
    for path in get_session_dir().glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append(
                    {
                        "id": data.get("id"),
                        "name": data.get("name", "New Chat"),
                        "created_at": data.get("created_at", time.time()),
                        "updated_at": data.get("updated_at", time.time()),
                        "provider": data.get("provider", "openai"),
                        "model": data.get("model", "gpt-4o-mini"),
                        "chatbot_name": data.get("chatbot_name", "Jarvis"),
                        "tone": data.get("tone", "friendly"),
                        "date_time": data.get("date_time", ""),
                    }
                )
        except Exception as e:
            print(f"Error reading session file {path}: {e}")

    # Sort by updated_at descending
    sessions.sort(key=lambda s: s.get("updated_at", 0), reverse=True)
    return sessions


def delete_session(thread_id: str) -> bool:
    """
    Deletes the JSON file associated with the thread_id.
    """
    path = get_session_path(thread_id)
    if path.exists():
        try:
            path.unlink()
            return True
        except Exception as e:
            print(f"Error deleting session {thread_id}: {e}")
    return False


def rename_session(thread_id: str, new_name: str) -> Optional[Dict[str, Any]]:
    """
    Loads a session, updates its name and updated_at fields, and saves it back.
    """
    session = load_session(thread_id)
    if session:
        session["name"] = new_name
        session["updated_at"] = time.time()
        try:
            path = get_session_path(thread_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2, ensure_ascii=False)
            return session
        except Exception as e:
            print(f"Error renaming session {thread_id}: {e}")
    return None
