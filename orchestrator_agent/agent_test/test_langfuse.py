import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator_agent.schemas import ChatMessage
from orchestrator_agent.services import execute_chatbot_graph


class TestLangfuseIntegration(unittest.IsolatedAsyncioTestCase):
    @patch("orchestrator_agent.services.get_env_variable")
    @patch("orchestrator_agent.services.prepare_chatbot_graph_state")
    async def test_langfuse_tracing_disabled_by_default(self, mock_prep_state, mock_get_env):
        # Setup mock env variables to return empty/None
        def mock_env(name, default=""):
            return default

        mock_get_env.side_effect = mock_env

        # Mock prepare_chatbot_graph_state to return mock config and graph
        mock_graph = MagicMock()
        mock_graph.aupdate_state = AsyncMock()
        mock_graph.aget_state = AsyncMock()

        # Mock updated_state for aget_state
        mock_state = MagicMock()
        mock_state.values.get.return_value = []
        mock_graph.aget_state.return_value = mock_state

        async def mock_astream(*args, **kwargs):
            if False:
                yield

        mock_graph.astream_events = mock_astream

        config = {"configurable": {"thread_id": "test_thread_no_lf"}, "metadata": {}, "tags": []}
        mock_prep_state.return_value = (
            None,
            mock_graph,
            config,
            None,
            [],
            {"provider": "openai", "model": "gpt-4o-mini", "chatbot_name": "Jarvis", "tone": "friendly"},
        )

        # Execute chatbot graph
        generator = execute_chatbot_graph(
            message=ChatMessage(role="user", content="hello"),
            provider="openai",
            model="gpt-4o-mini",
            thread_id="test_thread_no_lf",
        )
        async for _ in generator:
            pass

        # Callbacks should not be in the config
        assert "callbacks" not in config

    @patch("orchestrator_agent.services.get_env_variable")
    @patch("langfuse.langchain.CallbackHandler")
    @patch("orchestrator_agent.services.prepare_chatbot_graph_state")
    async def test_langfuse_tracing_enabled(self, mock_prep_state, mock_callback_handler, mock_get_env):
        # Setup mock env variables for Langfuse
        def mock_env(name, default=""):
            if name == "LANGFUSE_PUBLIC_KEY":
                return "pk-lf-test"
            if name == "LANGFUSE_SECRET_KEY":
                return "sk-lf-test"
            return default

        mock_get_env.side_effect = mock_env

        # Mock the CallbackHandler constructor
        mock_handler_instance = MagicMock()
        mock_callback_handler.return_value = mock_handler_instance

        # Mock prepare_chatbot_graph_state to return mock config and graph
        mock_graph = MagicMock()
        mock_graph.aupdate_state = AsyncMock()
        mock_graph.aget_state = AsyncMock()

        # Mock updated_state for aget_state
        mock_state = MagicMock()
        mock_state.values.get.return_value = []
        mock_graph.aget_state.return_value = mock_state

        async def mock_astream(*args, **kwargs):
            if False:
                yield

        mock_graph.astream_events = mock_astream

        config = {
            "configurable": {"thread_id": "test_thread_lf"},
            "metadata": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "chatbot_name": "Jarvis",
                "tone": "friendly",
                "langfuse_session_id": "test_thread_lf",
                "langfuse_trace_name": "agent-Jarvis",
            },
            "tags": ["openai", "gpt-4o-mini", "friendly"],
        }
        mock_prep_state.return_value = (
            None,
            mock_graph,
            config,
            None,
            [],
            {"provider": "openai", "model": "gpt-4o-mini", "chatbot_name": "Jarvis", "tone": "friendly"},
        )

        # Execute chatbot graph
        generator = execute_chatbot_graph(
            message=ChatMessage(role="user", content="hello"),
            provider="openai",
            model="gpt-4o-mini",
            thread_id="test_thread_lf",
        )
        async for _ in generator:
            pass

        # Verify CallbackHandler was initialized with correct arguments
        mock_callback_handler.assert_called_once_with()

        # Config should contain callbacks with mock handler
        assert "callbacks" in config
        assert mock_handler_instance in config["callbacks"]
