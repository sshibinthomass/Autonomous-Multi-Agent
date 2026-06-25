from typing import Annotated

from langgraph.graph.message import add_messages
from typing_extensions import List, TypedDict


class ChatbotState(TypedDict, total=False):
    """
    Represent the structure of the state used in graph,
    add_messages is a function that adds messages to the state for history of the conversation.
    """

    messages: Annotated[List, add_messages]
    provider: str
    model: str
    chatbot_name: str
    tone: str
    date_time: str

