"""LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.domain.generation.models import GeneratedContent, GenerationRequest, LLMProvider


class ILLMProvider(ABC):
    """Interface for LLM providers.

    Defines the contract for interacting with different LLM services
    (OpenAI, Anthropic, etc.).
    """

    @abstractmethod
    async def generate(
        self,
        request: GenerationRequest,
    ) -> GeneratedContent:
        """Generate content using the LLM.

        Args:
            request: Generation request with prompt and parameters

        Returns:
            Generated content with metadata

        Raises:
            GenerationException: If generation fails
        """
        pass

    @abstractmethod
    async def generate_with_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs,
    ) -> GeneratedContent:
        """Generate content using chat-based interface.

        Args:
            messages: List of chat messages (role, content)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated content

        Raises:
            GenerationException: If generation fails
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name.

        Returns:
            Provider name (e.g., "OpenAI", "Anthropic")
        """
        pass

    @abstractmethod
    def get_provider_type(self) -> LLMProvider:
        """Get provider type enum.

        Returns:
            Provider type
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models.

        Returns:
            List of model names
        """
        pass

    @abstractmethod
    def get_model_cost(self, model: str) -> Dict[str, float]:
        """Get cost information for a model.

        Args:
            model: Model name

        Returns:
            Dictionary with 'input_cost_per_1k' and 'output_cost_per_1k'
        """
        pass

    @abstractmethod
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for token usage.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Total cost in USD
        """
        pass

    @abstractmethod
    async def validate_api_key(self) -> bool:
        """Validate API key is valid and has access.

        Returns:
            True if API key is valid
        """
        pass

    @abstractmethod
    def get_rate_limit(self) -> Optional[int]:
        """Get rate limit for this provider.

        Returns:
            Requests per minute limit, or None if unlimited
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if provider supports streaming responses.

        Returns:
            True if streaming is supported
        """
        pass

    @abstractmethod
    def supports_function_calling(self) -> bool:
        """Check if provider supports function calling.

        Returns:
            True if function calling is supported
        """
        pass
