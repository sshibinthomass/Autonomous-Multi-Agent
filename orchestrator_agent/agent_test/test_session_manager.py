import pytest
import os
import time
from pathlib import Path
from orchestrator_agent.session_manager import (
    save_session,
    load_session,
    list_sessions,
    delete_session,
    rename_session,
    get_session_path,
)

TEST_THREAD_ID = "test-session-temp-xyz-999"

@pytest.fixture(autouse=True)
def clean_test_session():
    # Setup: ensure the session does not exist before running the test
    delete_session(TEST_THREAD_ID)
    yield
    # Teardown: clean up the session file after the test
    delete_session(TEST_THREAD_ID)

def test_save_and_load_session():
    messages = [
        {"role": "user", "content": "Hello world"},
        {"role": "assistant", "content": "Hello! How can I help you today?"}
    ]
    
    saved_data = save_session(
        thread_id=TEST_THREAD_ID,
        name="Temporary Test Session",
        messages=messages,
        provider="openai",
        model="gpt-4o-mini",
        chatbot_name="Jarvis",
        tone="friendly"
    )
    
    assert saved_data["id"] == TEST_THREAD_ID
    assert saved_data["name"] == "Temporary Test Session"
    assert saved_data["provider"] == "openai"
    assert saved_data["model"] == "gpt-4o-mini"
    assert saved_data["messages"] == messages
    
    # Load session and check values
    loaded_data = load_session(TEST_THREAD_ID)
    assert loaded_data is not None
    assert loaded_data["id"] == TEST_THREAD_ID
    assert loaded_data["name"] == "Temporary Test Session"
    assert loaded_data["messages"] == messages

def test_rename_session():
    save_session(
        thread_id=TEST_THREAD_ID,
        name="Original Name",
        messages=[],
        provider="gemini",
        model="gemini-2.5-flash",
        chatbot_name="Helper",
        tone="professional"
    )
    
    renamed_data = rename_session(TEST_THREAD_ID, "New Name")
    assert renamed_data is not None
    assert renamed_data["name"] == "New Name"
    
    # Load and confirm rename is written to disk
    loaded = load_session(TEST_THREAD_ID)
    assert loaded is not None
    assert loaded["name"] == "New Name"

def test_list_sessions():
    # Save a test session
    save_session(
        thread_id=TEST_THREAD_ID,
        name="Listed Chat",
        messages=[],
        provider="openai",
        model="gpt-4o-mini",
        chatbot_name="Jarvis",
        tone="friendly"
    )
    
    sessions = list_sessions()
    # Find our temp session in the list
    temp_session = next((s for s in sessions if s["id"] == TEST_THREAD_ID), None)
    
    assert temp_session is not None
    assert temp_session["name"] == "Listed Chat"
    assert temp_session["provider"] == "openai"
    assert temp_session["model"] == "gpt-4o-mini"

def test_delete_session():
    save_session(
        thread_id=TEST_THREAD_ID,
        name="Deletable Chat",
        messages=[],
        provider="openai",
        model="gpt-4o-mini",
        chatbot_name="Jarvis",
        tone="friendly"
    )
    
    path = get_session_path(TEST_THREAD_ID)
    assert path.exists()
    
    # Delete it
    deleted = delete_session(TEST_THREAD_ID)
    assert deleted is True
    assert not path.exists()
    
    # Deleting again should return False
    deleted_again = delete_session(TEST_THREAD_ID)
    assert deleted_again is False
