import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

# Resolve the project root directory and add it to python path
# to enable direct execution of this script as a standalone module
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import shared LiteLLM client, import protection, log suppression, and helper utilities
from orchestrator_agent.llms.litellm_generic import (
    litellm,
    to_litellm_model,
    convert_messages_to_litellm,
    process_response
)

from pydantic import Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun

from orchestrator_agent.config import ROUTER_FALLBACK_CHAIN

logger = logging.getLogger(__name__)


class LiteLLMChat(BaseChatModel):
    """A basic ChatModel wrapper using LiteLLM to handle fallback chains natively.

    Does not perform dynamic query classification/routing.
    """
    user_controls_input: dict = Field(default_factory=dict)
    tools: Optional[Sequence[Any]] = Field(default=None)

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @property
    def _llm_type(self) -> str:
        return "litellm_chat"

    def _sync_credentials(self) -> None:
        """Syncs API credentials from user inputs to environment variables."""
        for key, val in self.user_controls_input.items():
            if val and key.endswith("_API_KEY"):
                os.environ[key] = val

    def _prepare_execution_params(
        self,
        messages: List[BaseMessage]
    ) -> tuple[str, List[str], List[dict], Optional[List[dict]]]:
        """Resolves execution models, fallbacks, messages, and bound tools."""
        models = [to_litellm_model(p, m) for p, m in ROUTER_FALLBACK_CHAIN]
        
        selected = self.user_controls_input.get("selected_llm", "fallback")
        if selected == "fallback" or not selected:
            primary_model = models[0]
            fallback_models = models[1:]
        else:
            primary_model = selected
            fallback_models = [m for m in models if m != primary_model]
            
        litellm_messages = convert_messages_to_litellm(messages)
        
        litellm_tools = None
        if self.tools:
            from langchain_core.utils.function_calling import convert_to_openai_tool
            litellm_tools = [convert_to_openai_tool(tool) for tool in self.tools]
            
        return primary_model, fallback_models, litellm_messages, litellm_tools

    def _run_litellm(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        is_async: bool = False,
        **kwargs: Any
    ) -> Any:
        """Consolidates LiteLLM invocation logic across synchronous and asynchronous paths."""
        self._sync_credentials()
        primary_model, fallback_models, litellm_messages, litellm_tools = self._prepare_execution_params(messages)
        
        logger.info(f"LiteLLMChat executing {'async ' if is_async else ''}with LiteLLM. Model: {primary_model}, Fallbacks: {fallback_models}")
        print(f"LiteLLMChat executing {'async ' if is_async else ''}with LiteLLM. Model: {primary_model}, Fallbacks: {fallback_models}", flush=True)

        if is_async:
            from litellm import acompletion
            return acompletion(
                model=primary_model,
                messages=litellm_messages,
                tools=litellm_tools,
                fallbacks=fallback_models,
                stop=stop,
                **kwargs
            )
        else:
            from litellm import completion
            return completion(
                model=primary_model,
                messages=litellm_messages,
                tools=litellm_tools,
                fallbacks=fallback_models,
                stop=stop,
                **kwargs
            )

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Main entry point for synchronous execution."""
        response = self._run_litellm(messages, stop=stop, is_async=False, **kwargs)
        return process_response(response)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Main entry point for asynchronous execution."""
        response = await self._run_litellm(messages, stop=stop, is_async=True, **kwargs)
        return process_response(response)

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Any:
        """Binds a list of tools to this model instance."""
        return LiteLLMChat(
            user_controls_input=self.user_controls_input,
            tools=tools,
            **kwargs
        )


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    user_controls_input = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
        "selected_llm": "fallback",
    }
    
    print("Testing LiteLLMChat...")
    chat = LiteLLMChat(user_controls_input=user_controls_input)
    
    # Simple query test
    msg = [HumanMessage(content="Hello! How is it going?")]
    try:
        res = chat.invoke(msg)
        print("Response:\n", res.content)
    except Exception as e:
        print("Error:", e)
