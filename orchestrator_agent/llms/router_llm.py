import logging
import os
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence

import dotenv

# Resolve the project root directory and add it to python path
# to enable direct execution of this script as a standalone module
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

dotenv.load_dotenv()

# Import shared LiteLLM client, import protection, log suppression, and helper utilities
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.outputs import ChatResult
from pydantic import Field

# Import router configuration metrics and fallback chains
from orchestrator_agent.config import COMPLEX_FALLBACK_CHAIN, ROUTER_FALLBACK_CHAIN, ROUTER_MODEL, SIMPLE_FALLBACK_CHAIN
from orchestrator_agent.llms.litellm_generic import convert_messages_to_litellm, process_response, to_litellm_model
from orchestrator_agent.prompts.prompts import get_llm_router_prompt
from orchestrator_agent.states.structured_outputs import RoutingDecision

logger = logging.getLogger(__name__)


class DynamicRouterLLM(BaseChatModel):
    """A custom LangChain ChatModel implementation that dynamically classifies incoming queries

    and routes execution to task-appropriate model fallbacks using LiteLLM.
    """

    user_controls_input: dict = Field(default_factory=dict)
    tools: Optional[Sequence[Any]] = Field(default=None)

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @property
    def _llm_type(self) -> str:
        return "dynamic_router_llm"

    def _sync_credentials(self) -> None:
        """Syncs API credentials from user overrides (e.g., custom UI fields) to environment variables for LiteLLM usage."""
        for key, val in self.user_controls_input.items():
            if val and key.endswith("_API_KEY"):
                os.environ[key] = val

    def _prepare_execution_params(
        self, provider: str, model: str, task_type: str, messages: List[BaseMessage]
    ) -> tuple[str, List[str], List[dict], Optional[List[dict]]]:
        """Resolves specific execution models, fallback chains, messages, and bound tools needed for LiteLLM."""
        primary_model = to_litellm_model(provider, model)

        # Decide which execution fallback chain to use based on prompt classification type
        fallback_chain = SIMPLE_FALLBACK_CHAIN if task_type == "simple" else COMPLEX_FALLBACK_CHAIN
        fallback_models = [to_litellm_model(p, m) for p, m in fallback_chain]

        # Prevent routing back to the primary model as a fallback candidate
        fallback_models = [m for m in fallback_models if m != primary_model]

        litellm_messages = convert_messages_to_litellm(messages)

        # Standardize bound tools format for model ingestion (only pass tools for complex execution tasks)
        litellm_tools = None
        if self.tools and task_type == "complex":
            from langchain_core.utils.function_calling import convert_to_openai_tool

            litellm_tools = [convert_to_openai_tool(tool) for tool in self.tools]

        return primary_model, fallback_models, litellm_messages, litellm_tools

    def _run_litellm(
        self, messages: List[BaseMessage], stop: Optional[List[str]] = None, is_async: bool = False, **kwargs: Any
    ) -> Any:
        """Consolidates LiteLLM invocation logic across synchronous and asynchronous execution paths."""
        self._sync_credentials()

        # Classify complexity and extract target model configuration
        provider, model, task_type = self.route_query(messages)

        # Resolve models, fallback sequence, formatting, and parameters
        primary_model, fallback_models, litellm_messages, litellm_tools = self._prepare_execution_params(
            provider, model, task_type, messages
        )

        logger.info(
            f"Executing {'async ' if is_async else ''}with LiteLLM. Model: {primary_model}, Fallbacks: {fallback_models}"
        )
        print(
            f"Executing {'async ' if is_async else ''}with LiteLLM. Model: {primary_model}, Fallbacks: {fallback_models}",
            flush=True,
        )

        if is_async:
            from litellm import acompletion

            return acompletion(
                model=primary_model,
                messages=litellm_messages,
                tools=litellm_tools,
                fallbacks=fallback_models,
                stop=stop,
                **kwargs,
            )
        else:
            from litellm import completion

            return completion(
                model=primary_model,
                messages=litellm_messages,
                tools=litellm_tools,
                fallbacks=fallback_models,
                stop=stop,
                **kwargs,
            )

    def route_query(self, messages: List[BaseMessage]) -> tuple[str, str, str]:
        """Classifies the last user request using the router model fallback chain.

        Returns:
            Tuple of (provider, model, task_type) where task_type is 'simple' or 'complex'.
        """
        # Find the last human query message
        user_query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_query = msg.content
                break

        if not user_query:
            logger.info("No user query found. Defaulting to local gemma3:1b.")
            return "ollama", "gemma3:1b", "complex"

        try:
            from litellm import completion

            self._sync_credentials()
            prompt = get_llm_router_prompt(user_query)

            # Format routers based on fallback config metrics
            primary_router = to_litellm_model("groq", ROUTER_MODEL)
            fallback_routers = [to_litellm_model(p, m) for p, m in ROUTER_FALLBACK_CHAIN]
            fallback_routers = [r for r in fallback_routers if r != primary_router]

            logger.info(
                f"Invoking router model classification. Primary: {primary_router}, Fallbacks: {fallback_routers}"
            )
            print(
                f"Invoking router model classification. Primary: {primary_router}, Fallbacks: {fallback_routers}",
                flush=True,
            )

            # Request classification using schema constraints (RoutingDecision) to enforce structured outputs
            response = completion(
                model=primary_router,
                messages=[{"role": "user", "content": prompt}],
                response_format=RoutingDecision,
                fallbacks=fallback_routers,
            )

            content = response.choices[0].message.content
            logger.info(f"Router model raw output: {content}")
            print(f"Router model raw output: {content}", flush=True)

            # Validate output and unpack routing details
            decision = RoutingDecision.model_validate_json(content)
            provider = decision.provider.lower().strip()
            model = decision.model.strip()
            task_type = decision.task_type.strip()

            logger.info(f"[Router Choice] Model that classified: {response.model}")
            logger.info(
                f"[Router Decision] Provider: {provider}, Model: {model}, Type: {task_type}, Reason: {decision.reason}"
            )
            print(f"[Router Choice] Model that classified: {response.model}", flush=True)
            print(
                f"[Router Decision] Provider: {provider}, Model: {model}, Type: {task_type}, Reason: {decision.reason}",
                flush=True,
            )

            return provider, model, task_type
        except Exception as e:
            fallback_provider, fallback_model = ROUTER_FALLBACK_CHAIN[0]
            logger.warning(
                f"Routing classification failed: {e}. Falling back to default: {fallback_provider}/{fallback_model}"
            )
            print(
                f"Routing classification failed: {e}. Falling back to default: {fallback_provider}/{fallback_model}",
                flush=True,
            )
            return fallback_provider, fallback_model, "complex"

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
        return DynamicRouterLLM(user_controls_input=self.user_controls_input, tools=tools, **kwargs)


if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path

    import dotenv

    dotenv.load_dotenv()

    # Configure logging to stdout so we can see what's happening
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Resolve project root for imports
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from langchain_core.messages import HumanMessage

    from orchestrator_agent.tools.math_tools import math_tools

    user_controls_input = {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
    }

    print("Testing DynamicRouterLLM...")
    # Initialize the router model with math tools bound
    router = DynamicRouterLLM(user_controls_input=user_controls_input).bind_tools(math_tools)

    # Simple query test
    print("\n--- Invoking with Simple Query ---")
    simple_msg = [HumanMessage(content="Hi! How's it going?")]
    try:
        res = router.invoke(simple_msg)
        print("Response:\n", res.content)
    except Exception as e:
        print("Error testing simple query:", e)

    # Complex query test
    print("\n--- Invoking with Complex Query ---")
    complex_msg = [HumanMessage(content="Write a recursive Python function to print Fibonacci numbers.")]
    try:
        res = router.invoke(complex_msg)
        print("Response:\n", res.content)
    except Exception as e:
        print("Error testing complex query:", e)

    # Tool invocation test
    print("\n--- Invoking with Tool Query ---")
    tool_msg = [HumanMessage(content="Using the multiply tool, calculate 123 * 456")]
    try:
        res = router.invoke(tool_msg)
        print("Response:\n", res.content)
        print("Tool Calls Generated:\n", getattr(res, "tool_calls", []))
    except Exception as e:
        print("Error testing tool query:", e)
