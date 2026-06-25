import os

import dotenv
from langchain_anthropic import ChatAnthropic

dotenv.load_dotenv()


class AnthropicLLM:
    def __init__(self, user_controls_input):
        self.user_controls_input = user_controls_input

    def get_base_llm(self):
        """Return the base ChatAnthropic LLM instance"""
        anthropic_api_key = self.user_controls_input.get("ANTHROPIC_API_KEY", "")
        selected_anthropic_model = self.user_controls_input.get("selected_llm", "claude-haiku-4-5-20251001")

        return ChatAnthropic(api_key=anthropic_api_key, model=selected_anthropic_model)  # type: ignore[call-arg]


import sys

if __name__ == "__main__":
    # Example user_controls_input
    user_controls_input = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),  # Use env var or set your key here
        "selected_llm": "claude-haiku-4-5-20251001",
    }

    anthropic_llm = AnthropicLLM(user_controls_input)
    llm = anthropic_llm.get_base_llm()
    if llm:
        prompt = "What is the capital of France?"
        try:
            response = llm.invoke(prompt)
            print("Response:", response)
        except Exception as e:
            print("Error during invocation:", e)
            sys.exit(1)
    else:
        print("LLM could not be initialized.")
        sys.exit(1)
