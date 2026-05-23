def get_basic_chatbot_system_prompt(name: str = "Jarvis", tone: str = "friendly") -> str:
    """
    Returns the formatted system prompt for the chatbot based on custom name and tone configurations.

    Args:
        name: The name of the basic chatbot
        tone: The conversational tone (friendly, mature, professional)

    Returns:
        The formatted system prompt string
    """
    tone_guidelines = {
        "friendly": "Always be warm, enthusiastic, supportive, encouraging, and use friendly emojis occasionally.",
        "mature": "Always be calm, wise, balanced, thoughtful, direct, and avoid excessive emoji use.",
        "professional": "Always be formal, concise, authoritative, structured, objective, and highly professional.",
    }
    guideline = tone_guidelines.get(tone.lower(), tone_guidelines["friendly"])

    return f"""
    You are a helpful, knowledgeable and trustworthy assistant and your name is {name}. 
    
    Always respond in a human like manner.
    Conversational Tone Instructions: {guideline}
    """
