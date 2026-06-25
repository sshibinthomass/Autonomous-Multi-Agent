from typing import Literal, Optional

from pydantic import BaseModel, Field


class RoutingDecision(BaseModel):
    provider: str = Field(
        ...,
        description="The selected target LLM provider (must be one of: 'openai', 'gemini', 'groq', 'anthropic', 'ollama').",
    )
    model: str = Field(..., description="The specific model name corresponding to the selected provider.")
    task_type: Literal["simple", "complex"] = Field(
        "complex", description="Classification of the query's complexity: 'simple' or 'complex'."
    )
    reason: Optional[str] = Field(
        None, description="A short reasoning of why this model was chosen based on prompt complexity or user request."
    )
