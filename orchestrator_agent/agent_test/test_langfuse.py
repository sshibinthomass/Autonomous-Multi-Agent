import os
import unittest
from unittest.mock import patch, MagicMock
import pytest

from orchestrator_agent.services import prepare_chatbot_graph_state

class TestLangfuseIntegration(unittest.IsolatedAsyncioTestCase):
    @patch('orchestrator_agent.services.get_env_variable')
    async def test_langfuse_tracing_disabled_by_default(self, mock_get_env):
        # Setup mock env variables to return empty/None but keep OPENAI_API_KEY
        def mock_env(name, default=""):
            if name == "OPENAI_API_KEY":
                return "mock-openai-key"
            return default
        mock_get_env.side_effect = mock_env
        
        # Prepare graph state
        _, _, config, _, _, _ = await prepare_chatbot_graph_state(
            thread_id="test_thread_no_lf",
            provider="openai",
            model="gpt-4o-mini",
            chatbot_name="Jarvis",
            tone="friendly"
        )
        
        # Callbacks should not be in the config
        assert "callbacks" not in config

    @patch('orchestrator_agent.services.get_env_variable')
    @patch('langfuse.langchain.CallbackHandler')
    async def test_langfuse_tracing_enabled(self, mock_callback_handler, mock_get_env):
        # Setup mock env variables for Langfuse
        def mock_env(name, default=""):
            if name == "LANGFUSE_PUBLIC_KEY":
                return "pk-lf-test"
            if name == "LANGFUSE_SECRET_KEY":
                return "sk-lf-test"
            if name == "LANGFUSE_HOST":
                return "https://cloud.langfuse.com"
            if name == "OPENAI_API_KEY":
                return "mock-openai-key"
            return default
            
        mock_get_env.side_effect = mock_env
        
        # Mock the CallbackHandler constructor
        mock_handler_instance = MagicMock()
        mock_callback_handler.return_value = mock_handler_instance
        
        # Prepare graph state
        _, _, config, _, _, _ = await prepare_chatbot_graph_state(
            thread_id="test_thread_lf",
            provider="openai",
            model="gpt-4o-mini",
            chatbot_name="Jarvis",
            tone="friendly"
        )
        
        # Verify CallbackHandler was initialized with correct arguments
        mock_callback_handler.assert_called_once_with(
            public_key="pk-lf-test",
            secret_key="sk-lf-test",
            host="https://cloud.langfuse.com",
            session_id="test_thread_lf",
            trace_name="agent-Jarvis"
        )
        
        # Config should contain callbacks with mock handler
        assert "callbacks" in config
        assert mock_handler_instance in config["callbacks"]
