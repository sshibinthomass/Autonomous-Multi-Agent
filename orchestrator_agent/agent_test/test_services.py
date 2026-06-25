from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from orchestrator_agent.schemas import ChatMessage
from orchestrator_agent.services import to_chat_dict, to_langchain_messages


def test_to_chat_dict_system_message():
    msg = SystemMessage(content="You are an AI.")
    res = to_chat_dict(msg)

    assert res["role"] == "system"
    assert res["content"] == "You are an AI."
    assert "timestamp" in res
    assert res["timestamp"] is not None


def test_to_chat_dict_ai_message_with_existing_timestamp():
    msg = AIMessage(content="Hello there!", additional_kwargs={"timestamp": "2026-06-13 12:00:00"})
    res = to_chat_dict(msg)

    assert res["role"] == "assistant"
    assert res["content"] == "Hello there!"
    assert res["timestamp"] == "2026-06-13 12:00:00"


def test_to_chat_dict_human_message():
    msg = HumanMessage(content="Hello AI.")
    res = to_chat_dict(msg)

    assert res["role"] == "user"
    assert res["content"] == "Hello AI."
    assert "timestamp" in res


def test_to_langchain_messages_conversion():
    chat_msgs = [
        ChatMessage(role="system", content="System instruction", timestamp="2026-06-13 10:00:00"),
        ChatMessage(role="assistant", content="AI reply"),
        ChatMessage(role="user", content="Human prompt"),
    ]

    converted = to_langchain_messages(chat_msgs)

    assert len(converted) == 3
    assert isinstance(converted[0], SystemMessage)
    assert converted[0].content == "System instruction"
    assert converted[0].additional_kwargs.get("timestamp") == "2026-06-13 10:00:00"

    assert isinstance(converted[1], AIMessage)
    assert converted[1].content == "AI reply"
    assert "timestamp" not in converted[1].additional_kwargs

    assert isinstance(converted[2], HumanMessage)
    assert converted[2].content == "Human prompt"
