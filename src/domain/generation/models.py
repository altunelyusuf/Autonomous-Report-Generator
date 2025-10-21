"""Domain models for content generation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4


class LLMProvider(str, Enum):
    """LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ContentType(str, Enum):
    """Content generation types."""

    NARRATIVE = "narrative"
    SUMMARY = "summary"
    DEFINITION = "definition"
    EXPLANATION = "explanation"
    COMPARISON = "comparison"


@dataclass
class GenerationRequest:
    """Request for content generation.

    Attributes:
        request_id: Unique request identifier
        content_type: Type of content to generate
        prompt: Generation prompt
        context: Additional context for generation
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 to 1.0)
        provider: Preferred LLM provider
        research_results: Optional research results to include
        citations_required: Whether to include citations
        created_at: Request creation timestamp
    """

    request_id: UUID = field(default_factory=uuid4)
    content_type: ContentType = ContentType.NARRATIVE
    prompt: str = ""
    context: Dict[str, any] = field(default_factory=dict)
    max_tokens: int = 2000
    temperature: float = 0.7
    provider: LLMProvider = LLMProvider.OPENAI
    research_results: Optional[List[Dict]] = None
    citations_required: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GeneratedContent:
    """Generated content result.

    Attributes:
        content_id: Unique content identifier
        request_id: Associated request ID
        content: Generated text content
        citations: List of citations embedded in content
        provider: LLM provider used
        model: Specific model used
        tokens_used: Number of tokens consumed
        cost: Generation cost in USD
        quality_score: Quality assessment score
        metadata: Additional metadata
        generated_at: Generation timestamp
    """

    content_id: UUID = field(default_factory=uuid4)
    request_id: UUID = field(default_factory=uuid4)
    content: str = ""
    citations: List[Dict[str, any]] = field(default_factory=list)
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    quality_score: float = 0.0
    metadata: Dict[str, any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def add_citation(self, citation: Dict[str, any]) -> None:
        """Add citation to content.

        Args:
            citation: Citation dictionary with source info
        """
        self.citations.append(citation)

    def calculate_quality_score(self) -> float:
        """Calculate quality score for generated content.

        Returns:
            Quality score (0.0 to 1.0)
        """
        scores = []

        # 1. Length check (not too short, not too long)
        word_count = len(self.content.split())
        if word_count >= 50:
            length_score = min(1.0, word_count / 500)  # Cap at 500 words
            scores.append(length_score)
        else:
            scores.append(0.3)  # Penalize very short content

        # 2. Citation score (if required)
        if self.citations:
            citation_score = min(1.0, len(self.citations) / 5)  # Cap at 5 citations
            scores.append(citation_score)
        else:
            scores.append(0.5)  # Neutral if no citations

        # 3. Coherence score (simple heuristic based on sentence structure)
        sentences = self.content.split('.')
        if len(sentences) >= 3:
            scores.append(0.8)
        else:
            scores.append(0.5)

        self.quality_score = sum(scores) / len(scores) if scores else 0.0
        return self.quality_score


@dataclass
class PromptTemplate:
    """Template for generating prompts.

    Attributes:
        template_id: Unique template identifier
        name: Template name
        content_type: Type of content this template generates
        template: Template string with placeholders
        required_variables: Variables required in template
        optional_variables: Optional variables
        system_prompt: System prompt for LLM
        examples: Few-shot examples
    """

    template_id: UUID = field(default_factory=uuid4)
    name: str = ""
    content_type: ContentType = ContentType.NARRATIVE
    template: str = ""
    required_variables: List[str] = field(default_factory=list)
    optional_variables: List[str] = field(default_factory=list)
    system_prompt: str = ""
    examples: List[Dict[str, str]] = field(default_factory=list)

    def render(self, variables: Dict[str, any]) -> str:
        """Render template with variables.

        Args:
            variables: Dictionary of template variables

        Returns:
            Rendered prompt string

        Raises:
            ValueError: If required variables are missing
        """
        # Check required variables
        missing = set(self.required_variables) - set(variables.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")

        # Simple template rendering (in production, use Jinja2)
        rendered = self.template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            rendered = rendered.replace(placeholder, str(value))

        return rendered


@dataclass
class GenerationMetrics:
    """Metrics for generation operations.

    Attributes:
        total_requests: Total generation requests
        successful_generations: Successful generations
        failed_generations: Failed generations
        total_tokens: Total tokens consumed
        total_cost: Total cost in USD
        average_quality: Average quality score
        provider_usage: Usage by provider
        model_usage: Usage by model
    """

    total_requests: int = 0
    successful_generations: int = 0
    failed_generations: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    average_quality: float = 0.0
    provider_usage: Dict[str, int] = field(default_factory=dict)
    model_usage: Dict[str, int] = field(default_factory=dict)

    def record_generation(
        self,
        success: bool,
        provider: LLMProvider,
        model: str,
        tokens: int,
        cost: float,
        quality: float,
    ) -> None:
        """Record a generation operation.

        Args:
            success: Whether generation succeeded
            provider: Provider used
            model: Model used
            tokens: Tokens consumed
            cost: Cost in USD
            quality: Quality score
        """
        self.total_requests += 1

        if success:
            self.successful_generations += 1
            self.total_tokens += tokens
            self.total_cost += cost

            # Update average quality
            n = self.successful_generations
            self.average_quality = (
                self.average_quality * (n - 1) + quality
            ) / n

            # Track provider usage
            provider_key = provider.value
            self.provider_usage[provider_key] = (
                self.provider_usage.get(provider_key, 0) + 1
            )

            # Track model usage
            self.model_usage[model] = self.model_usage.get(model, 0) + 1
        else:
            self.failed_generations += 1

    def get_success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate (0.0 to 1.0)
        """
        if self.total_requests == 0:
            return 0.0
        return self.successful_generations / self.total_requests

    def get_average_cost_per_request(self) -> float:
        """Calculate average cost per successful request.

        Returns:
            Average cost in USD
        """
        if self.successful_generations == 0:
            return 0.0
        return self.total_cost / self.successful_generations
