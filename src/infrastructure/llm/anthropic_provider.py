"""Anthropic LLM provider implementation."""

import logging
from typing import Dict, List, Optional

from anthropic import AsyncAnthropic

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


class AnthropicProvider(ILLMProvider):
    """Anthropic LLM provider.

    Integrates with Anthropic's Claude models for content generation.

    Features:
    - Claude 3 model family support
    - Message API
    - Token usage tracking
    - Cost calculation
    - Error handling
    """

    # Model pricing (cost per 1M tokens) - as of 2024
    MODEL_COSTS = {
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        "claude-2.1": {"input": 8.00, "output": 24.00},
        "claude-2.0": {"input": 8.00, "output": 24.00},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "claude-3-sonnet-20240229",
    ):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            default_model: Default model to use
        """
        self.api_key = api_key
        self.default_model = default_model

        if api_key:
            self.client = AsyncAnthropic(api_key=api_key)
        else:
            self.client = None
            logger.warning("No Anthropic API key provided, using mock mode")

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GeneratedContent:
        """Generate content using Anthropic.

        Args:
            request: Generation request

        Returns:
            Generated content

        Raises:
            ValidationException: If request is invalid
            ProviderException: If generation fails
        """
        logger.info(
            f"Anthropic generation request: {request.content_type.value} "
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
            messages = [{"role": "user", "content": request.prompt}]

            # Get system prompt if available
            system_prompt = request.context.get("system_prompt", "")

            # Call Anthropic API
            model = request.context.get("model", self.default_model)
            response = await self.client.messages.create(
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=system_prompt if system_prompt else None,
                messages=messages,
            )

            # Extract content
            content_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            tokens_used = input_tokens + output_tokens

            # Calculate cost
            cost = self.calculate_cost(model, input_tokens, output_tokens)

            # Create result
            result = GeneratedContent(
                request_id=request.request_id,
                content=content_text,
                provider=LLMProvider.ANTHROPIC,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "stop_reason": response.stop_reason,
                },
            )

            logger.info(
                f"Anthropic generation completed: {tokens_used} tokens, ${cost:.4f}"
            )

            return result

        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")

            # Check for quota errors
            if "rate_limit" in str(e).lower() or "quota" in str(e).lower():
                raise QuotaException(f"Anthropic quota exceeded: {e}")

            raise ProviderException(f"Anthropic generation failed: {e}")

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
                provider=LLMProvider.ANTHROPIC,
                model=self.default_model,
                tokens_used=100,
                cost=0.0,
            )

        try:
            model = kwargs.get("model", self.default_model)
            system_prompt = kwargs.get("system", "")

            # Convert messages to Anthropic format
            anthropic_messages = []
            for msg in messages:
                if msg["role"] != "system":  # System handled separately
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })

            response = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                messages=anthropic_messages,
            )

            content_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            tokens_used = input_tokens + output_tokens

            cost = self.calculate_cost(model, input_tokens, output_tokens)

            return GeneratedContent(
                content=content_text,
                provider=LLMProvider.ANTHROPIC,
                model=model,
                tokens_used=tokens_used,
                cost=cost,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            )

        except Exception as e:
            logger.error(f"Anthropic chat generation failed: {e}")
            raise ProviderException(f"Anthropic chat generation failed: {e}")

    def _generate_mock_content(self, request: GenerationRequest) -> GeneratedContent:
        """Generate mock content for testing.

        Args:
            request: Generation request

        Returns:
            Mock generated content
        """
        content_templates = {
            "narrative": (
                f"This is a detailed exploration of {request.prompt}. "
                "Through careful analysis and synthesis of multiple sources, "
                "we can understand the multifaceted nature of this topic. "
                "The narrative weaves together historical context, current research, "
                "and future implications to provide a comprehensive overview."
            ),
            "summary": (
                f"In summary, {request.prompt} encompasses several key aspects: "
                "1) Core concepts and definitions, "
                "2) Historical development and evolution, "
                "3) Current state and applications."
            ),
            "definition": (
                f"{request.prompt} is defined as a complex concept that integrates "
                "multiple dimensions including theoretical foundations, "
                "practical applications, and ongoing research directions."
            ),
        }

        content = content_templates.get(
            request.content_type.value,
            f"Mock content for {request.prompt}",
        )

        return GeneratedContent(
            request_id=request.request_id,
            content=content,
            provider=LLMProvider.ANTHROPIC,
            model=self.default_model,
            tokens_used=150,
            cost=0.0,
            metadata={"mock": True},
        )

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "Anthropic"

    def get_provider_type(self) -> LLMProvider:
        """Get provider type."""
        return LLMProvider.ANTHROPIC

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
                "input_cost_per_1k": self.MODEL_COSTS[model]["input"] / 1000,
                "output_cost_per_1k": self.MODEL_COSTS[model]["output"] / 1000,
            }

        # Default to Claude 3 Sonnet pricing
        return {
            "input_cost_per_1k": 0.003,
            "output_cost_per_1k": 0.015,
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
            await self.client.messages.create(
                model=self.default_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False

    def get_rate_limit(self) -> Optional[int]:
        """Get rate limit.

        Returns:
            Requests per minute
        """
        # Anthropic rate limits vary by tier
        # Returning conservative estimate
        return 50  # 50 requests per minute

    def supports_streaming(self) -> bool:
        """Check streaming support."""
        return True

    def supports_function_calling(self) -> bool:
        """Check function calling support."""
        return False  # Anthropic doesn't support function calling like OpenAI


class MockAnthropicProvider(AnthropicProvider):
    """Mock Anthropic provider for testing.

    Always returns mock content without requiring API keys.
    """

    def __init__(self, default_model: str = "claude-3-sonnet-20240229"):
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
        logger.info(f"Mock Anthropic generation: {request.content_type.value}")

        # Validate
        if not request.prompt or len(request.prompt.strip()) == 0:
            raise ValidationException("Prompt cannot be empty")

        return self._generate_mock_content(request)

    async def validate_api_key(self) -> bool:
        """Validate API key (always True for mock)."""
        return True
