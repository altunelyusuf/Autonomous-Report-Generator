"""OpenAI LLM provider implementation."""

import logging
from typing import Dict, List, Optional
from uuid import uuid4

from openai import AsyncOpenAI

from src.domain.generation.exceptions import (
    ProviderException,
    QuotaException,
    ValidationException,
)
from src.domain.generation.models import (
    GeneratedContent,
    GenerationRequest,
    LLMProvider,
)
from src.domain.generation.provider import ILLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(ILLMProvider):
    """OpenAI LLM provider.

    Integrates with OpenAI's GPT models for content generation.

    Features:
    - GPT-4 and GPT-3.5 support
    - Chat completion API
    - Token usage tracking
    - Cost calculation
    - Error handling
    """

    # Model pricing (cost per 1K tokens) - as of 2024
    MODEL_COSTS = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gpt-3.5-turbo",
        organization: Optional[str] = None,
    ):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            default_model: Default model to use
            organization: OpenAI organization ID
        """
        self.api_key = api_key
        self.default_model = default_model
        self.organization = organization

        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                organization=organization,
            )
        else:
            self.client = None
            logger.warning("No OpenAI API key provided, using mock mode")

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GeneratedContent:
        """Generate content using OpenAI.

        Args:
            request: Generation request

        Returns:
            Generated content

        Raises:
            ValidationException: If request is invalid
            ProviderException: If generation fails
        """
        logger.info(
            f"OpenAI generation request: {request.content_type.value} "
            f"(max_tokens={request.max_tokens})"
        )

        # Validate request
        if not request.prompt or len(request.prompt.strip()) == 0:
            raise ValidationException("Prompt cannot be empty")

        # If no API key, return mock content
        if not self.client:
            return self._generate_mock_content(request)

        try:
            # Build messages
            messages = []

            # Add system message if available
            if "system_prompt" in request.context:
                messages.append({
                    "role": "system",
                    "content": request.context["system_prompt"],
                })

            # Add user message
            messages.append({
                "role": "user",
                "content": request.prompt,
            })

            # Call OpenAI API
            model = request.context.get("model", self.default_model)
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

            # Extract content
            content_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            # Calculate cost
            cost = self.calculate_cost(model, input_tokens, output_tokens)

            # Create result
            result = GeneratedContent(
                request_id=request.request_id,
                content=content_text,
                provider=LLMProvider.OPENAI,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "finish_reason": response.choices[0].finish_reason,
                },
            )

            logger.info(
                f"OpenAI generation completed: {tokens_used} tokens, ${cost:.4f}"
            )

            return result

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")

            # Check for quota errors
            if "quota" in str(e).lower() or "rate_limit" in str(e).lower():
                raise QuotaException(f"OpenAI quota exceeded: {e}")

            raise ProviderException(f"OpenAI generation failed: {e}")

    async def generate_with_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs,
    ) -> GeneratedContent:
        """Generate content using chat interface.

        Args:
            messages: Chat messages
            max_tokens: Maximum tokens
            temperature: Temperature
            **kwargs: Additional parameters

        Returns:
            Generated content
        """
        if not self.client:
            # Mock response
            return GeneratedContent(
                content="Mock chat response",
                provider=LLMProvider.OPENAI,
                model=self.default_model,
                tokens_used=100,
                cost=0.0,
            )

        try:
            model = kwargs.get("model", self.default_model)

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            cost = self.calculate_cost(model, input_tokens, output_tokens)

            return GeneratedContent(
                content=content_text,
                provider=LLMProvider.OPENAI,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            )

        except Exception as e:
            logger.error(f"OpenAI chat generation failed: {e}")
            raise ProviderException(f"OpenAI chat generation failed: {e}")

    def _generate_mock_content(self, request: GenerationRequest) -> GeneratedContent:
        """Generate mock content for testing.

        Args:
            request: Generation request

        Returns:
            Mock generated content
        """
        content_templates = {
            "narrative": (
                f"This is a comprehensive narrative about {request.prompt}. "
                "The topic is explored from multiple perspectives, "
                "incorporating insights from various sources. "
                "Key points include historical context, current developments, "
                "and future implications."
            ),
            "summary": (
                f"Summary of {request.prompt}: "
                "The main points include several important aspects "
                "that have been thoroughly researched and documented."
            ),
            "definition": (
                f"{request.prompt} can be defined as a concept with multiple "
                "dimensions and applications across various domains."
            ),
        }

        content = content_templates.get(
            request.content_type.value,
            f"Mock content for {request.prompt}",
        )

        return GeneratedContent(
            request_id=request.request_id,
            content=content,
            provider=LLMProvider.OPENAI,
            model=self.default_model,
            tokens_used=100,
            cost=0.0,
            metadata={"mock": True},
        )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "OpenAI"

    def get_provider_type(self) -> LLMProvider:
        """Get provider type."""
        return LLMProvider.OPENAI

    def get_available_models(self) -> List[str]:
        """Get available models."""
        return list(self.MODEL_COSTS.keys())

    def get_model_cost(self, model: str) -> Dict[str, float]:
        """Get model cost information.

        Args:
            model: Model name

        Returns:
            Cost dictionary
        """
        if model in self.MODEL_COSTS:
            return {
                "input_cost_per_1k": self.MODEL_COSTS[model]["input"],
                "output_cost_per_1k": self.MODEL_COSTS[model]["output"],
            }

        # Default to GPT-3.5-turbo pricing
        return {
            "input_cost_per_1k": 0.0005,
            "output_cost_per_1k": 0.0015,
        }

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate generation cost.

        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Total cost in USD
        """
        costs = self.get_model_cost(model)

        input_cost = (input_tokens / 1000) * costs["input_cost_per_1k"]
        output_cost = (output_tokens / 1000) * costs["output_cost_per_1k"]

        return input_cost + output_cost

    async def validate_api_key(self) -> bool:
        """Validate API key.

        Returns:
            True if valid
        """
        if not self.client:
            logger.warning("No API key configured")
            return False

        try:
            # Try a minimal API call
            await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False

    def get_rate_limit(self) -> Optional[int]:
        """Get rate limit.

        Returns:
            Requests per minute (varies by model)
        """
        # OpenAI rate limits vary by tier
        # Returning conservative estimate
        return 60  # 60 requests per minute

    def supports_streaming(self) -> bool:
        """Check streaming support."""
        return True

    def supports_function_calling(self) -> bool:
        """Check function calling support."""
        return True


class MockOpenAIProvider(OpenAIProvider):
    """Mock OpenAI provider for testing.

    Always returns mock content without requiring API keys.
    """

    def __init__(self, default_model: str = "gpt-3.5-turbo"):
        """Initialize mock provider.

        Args:
            default_model: Default model name
        """
        super().__init__(api_key=None, default_model=default_model)

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GeneratedContent:
        """Generate mock content.

        Args:
            request: Generation request

        Returns:
            Mock generated content
        """
        logger.info(f"Mock OpenAI generation: {request.content_type.value}")

        # Validate
        if not request.prompt or len(request.prompt.strip()) == 0:
            raise ValidationException("Prompt cannot be empty")

        return self._generate_mock_content(request)

    async def validate_api_key(self) -> bool:
        """Validate API key (always True for mock)."""
        return True
