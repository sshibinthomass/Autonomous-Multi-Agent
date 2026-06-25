from langchain_core.tools import tool


@tool
def add(a: float, b: float) -> float:
    """Adds two numbers together. Use this tool for mathematical addition."""
    return a + b

@tool
def subtract(a: float, b: float) -> float:
    """Subtracts b from a. Use this tool for mathematical subtraction."""
    return a - b

@tool
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers together. Use this tool for mathematical multiplication."""
    return a * b

@tool
def divide(a: float, b: float) -> float:
    """Divides a by b. Use this tool for mathematical division. Handles division by zero gracefully."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b

math_tools = [add, subtract, multiply, divide]
