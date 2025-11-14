"""
Centralized model factory for creating LLM instances.
Supports Anthropic, OpenAI, and Ollama providers.
Includes LLM call tracking for observability.
"""
from typing import Optional
from datetime import datetime
from langchain_core.language_models.chat_models import BaseChatModel

from config.config import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
)

# Global flag for tracking (can be disabled for production)
ENABLE_LLM_TRACKING = True


def get_chat_model(temperature: float = 0.3, model_override: Optional[str] = None) -> BaseChatModel:
    """
    Creates and returns a chat model instance based on the configured provider.

    Args:
        temperature: Temperature parameter for the model (default: 0.3)
        model_override: Optional model name to override the default from config

    Returns:
        BaseChatModel: An instance of the appropriate chat model

    Raises:
        ValueError: If the provider is not supported or API keys are missing
    """
    provider = LLM_PROVIDER.lower()

    if provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Please set it in your .env file."
            )

        from langchain_anthropic import ChatAnthropic

        model_name = model_override or ANTHROPIC_MODEL
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            api_key=ANTHROPIC_API_KEY,
        )

    elif provider == "openai":
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not found. Please set it in your .env file."
            )

        from langchain_openai import ChatOpenAI

        model_name = model_override or OPENAI_MODEL
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=OPENAI_API_KEY,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        model_name = model_override or OLLAMA_MODEL
        return ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=OLLAMA_BASE_URL,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Please use 'anthropic', 'openai', or 'ollama'."
        )


class TrackedChatModel:
    """
    Wrapper for BaseChatModel that tracks LLM calls for observability.

    This wrapper intercepts invoke() calls and records:
    - Timing information
    - Prompt and response lengths
    - Model configuration
    - Calling node context
    """

    def __init__(self, model: BaseChatModel, node_name: str = "unknown", purpose: Optional[str] = None):
        """
        Initialize tracked model wrapper.

        Args:
            model: The actual chat model instance
            node_name: Name of the node/worker using this model
            purpose: Purpose of the LLM call (e.g., "routing", "processing")
        """
        self.model = model
        self.node_name = node_name
        self.purpose = purpose
        self._model_name = self._get_model_name()
        self._temperature = getattr(model, 'temperature', 0.3)

    def _get_model_name(self) -> str:
        """Extract model name from the model instance."""
        if hasattr(self.model, 'model_name'):
            return self.model.model_name
        elif hasattr(self.model, 'model'):
            return self.model.model
        else:
            return self.model.__class__.__name__

    def invoke(self, prompt, **kwargs):
        """
        Invoke the model and track the call.

        Args:
            prompt: The prompt to send to the model
            **kwargs: Additional arguments to pass to model.invoke()

        Returns:
            Model response
        """
        if not ENABLE_LLM_TRACKING:
            # Tracking disabled, just pass through
            return self.model.invoke(prompt, **kwargs)

        # Track the call
        start_time = datetime.now()
        prompt_length = len(str(prompt)) if prompt else 0

        try:
            # Make the actual LLM call
            response = self.model.invoke(prompt, **kwargs)

            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Get response length
            response_text = response.content if hasattr(response, 'content') else str(response)
            response_length = len(response_text)

            # Record the call
            try:
                from helpers.observability import LLMCallTracker
                LLMCallTracker.record_call(
                    node_name=self.node_name,
                    model_name=self._model_name,
                    temperature=self._temperature,
                    prompt_length=prompt_length,
                    response_length=response_length,
                    duration_seconds=duration,
                    purpose=self.purpose
                )
            except Exception as e:
                # Don't fail the LLM call if tracking fails
                print(f"Warning: Failed to record LLM call: {e}")

            return response

        except Exception as e:
            # Record failed call
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            try:
                from helpers.observability import LLMCallTracker
                LLMCallTracker.record_call(
                    node_name=self.node_name,
                    model_name=self._model_name,
                    temperature=self._temperature,
                    prompt_length=prompt_length,
                    response_length=0,
                    duration_seconds=duration,
                    purpose=f"{self.purpose} (FAILED)"
                )
            except:
                pass

            # Re-raise the original exception
            raise e

    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped model."""
        return getattr(self.model, name)


def get_tracked_chat_model(
    node_name: str,
    temperature: float = 0.3,
    model_override: Optional[str] = None,
    purpose: Optional[str] = None
) -> TrackedChatModel:
    """
    Creates a tracked chat model instance with LLM call monitoring.

    Args:
        node_name: Name of the node/worker using this model
        temperature: Temperature parameter for the model (default: 0.3)
        model_override: Optional model name to override the default from config
        purpose: Purpose of the LLM call (e.g., "routing_decision", "task_processing")

    Returns:
        TrackedChatModel: Wrapped model instance with call tracking

    Example:
        model = get_tracked_chat_model(node_name="executor", temperature=0.2, purpose="routing")
        response = model.invoke(prompt)
    """
    base_model = get_chat_model(temperature=temperature, model_override=model_override)
    return TrackedChatModel(base_model, node_name=node_name, purpose=purpose)
