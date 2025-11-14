"""
Initialize Ollama LLM for use with LangChain.
"""
from langchain_ollama import ChatOllama
from config.config import OLLAMA_MODEL


def get_ollama_chat(model: str = None, temperature: float = 0.2):
    """
    Get an Ollama Chat model instance (for LangChain chat patterns).

    Args:
        model: Model name to use (defaults to config setting)
        temperature: Temperature for response generation

    Returns:
        ChatOllama instance
    """
    model_name = model or OLLAMA_MODEL
    return ChatOllama(
        model=model_name,
        temperature=temperature
    )
