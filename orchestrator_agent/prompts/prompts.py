def get_basic_chatbot_system_prompt(name: str = "") -> str:
    """
    Returns the system prompt for basic chatbot.

    Args:
        name: The name of the basic chatbot

    Returns:
        The formatted system prompt string
    """
    return """
    You are a helpful,knowledgeable and trustworthy assistant and your name is {name}. 
    
    Always respond in a human like manner. 
    """.format(name=name)
