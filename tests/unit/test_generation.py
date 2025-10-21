"""Unit tests for content generation."""

import pytest

from src.domain.generation.exceptions import ValidationException
from src.domain.generation.generator import ContentGenerator
from src.domain.generation.models import (
    ContentType,
    GeneratedContent,
    GenerationRequest,
    LLMProvider,
    PromptTemplate,
)
from src.domain.research.models import (
    Fact,
    KnowledgeSource,
    ResearchResult,
    SourceType,
)
from src.infrastructure.llm.anthropic_provider import MockAnthropicProvider
from src.infrastructure.llm.openai_provider import MockOpenAIProvider


@pytest.fixture
def mock_openai_provider():
    """Create mock OpenAI provider."""
    return MockOpenAIProvider(default_model="gpt-3.5-turbo")


@pytest.fixture
def mock_anthropic_provider():
    """Create mock Anthropic provider."""
    return MockAnthropicProvider(default_model="claude-3-sonnet-20240229")


@pytest.fixture
def content_generator(mock_openai_provider, mock_anthropic_provider):
    """Create content generator with mock providers."""
    providers = {
        LLMProvider.OPENAI: mock_openai_provider,
        LLMProvider.ANTHROPIC: mock_anthropic_provider,
    }
    return ContentGenerator(providers=providers, default_provider=LLMProvider.OPENAI)


@pytest.fixture
def sample_research_result():
    """Create sample research result."""
    result = ResearchResult(
        concept_uri="http://example.org/AI",
        concept_label="Artificial Intelligence",
    )

    # Add sources
    sources = [
        KnowledgeSource(
            source_name="Wikipedia",
            source_type=SourceType.WEB,
            reliability_score=0.7,
            metadata={"url": "https://en.wikipedia.org/wiki/AI"},
        ),
        KnowledgeSource(
            source_name="Academic Source",
            source_type=SourceType.ACADEMIC,
            reliability_score=0.95,
            metadata={"url": "https://academic.example.com/ai"},
        ),
    ]

    # Add facts
    facts = [
        Fact(
            statement="AI is a branch of computer science.",
            subject="AI",
            predicate="is_a",
            object="Computer Science",
            confidence=0.9,
            source_id=sources[0].source_id,
        ),
        Fact(
            statement="Machine learning is a subset of AI.",
            subject="Machine Learning",
            predicate="is_a",
            object="AI",
            confidence=0.95,
            source_id=sources[1].source_id,
        ),
        Fact(
            statement="AI systems can learn from data.",
            confidence=0.85,
            source_id=sources[0].source_id,
        ),
    ]

    for fact, source in zip(facts, sources + [sources[0]]):
        result.add_fact(fact, source)

    result.calculate_confidence()

    return result


class TestGenerationModels:
    """Test generation domain models."""

    def test_generation_request_defaults(self):
        """Test generation request with defaults."""
        request = GenerationRequest(prompt="Test prompt")

        assert request.prompt == "Test prompt"
        assert request.content_type == ContentType.NARRATIVE
        assert request.max_tokens == 2000
        assert request.temperature == 0.7
        assert request.provider == LLMProvider.OPENAI
        assert request.citations_required is True

    def test_generated_content_add_citation(self):
        """Test adding citations to generated content."""
        content = GeneratedContent(content="Test content")

        citation = {
            "id": 1,
            "source_name": "Wikipedia",
            "url": "https://example.com",
        }

        content.add_citation(citation)

        assert len(content.citations) == 1
        assert content.citations[0]["source_name"] == "Wikipedia"

    def test_generated_content_quality_score(self):
        """Test quality score calculation."""
        content = GeneratedContent(
            content=(
                "This is a comprehensive test content with multiple sentences. "
                "It includes sufficient length and structure. "
                "The content is well-formed and informative."
            )
        )

        # Add citations
        content.add_citation({"id": 1, "source": "Source 1"})
        content.add_citation({"id": 2, "source": "Source 2"})

        quality = content.calculate_quality_score()

        # Should have reasonable quality
        assert 0.0 <= quality <= 1.0
        assert quality > 0.5

    def test_prompt_template_render(self):
        """Test prompt template rendering."""
        template = PromptTemplate(
            name="test",
            template="Write about {topic} using {style} style.",
            required_variables=["topic", "style"],
        )

        rendered = template.render({"topic": "AI", "style": "academic"})

        assert "AI" in rendered
        assert "academic" in rendered
        assert "{topic}" not in rendered

    def test_prompt_template_missing_variables(self):
        """Test template rendering with missing variables."""
        template = PromptTemplate(
            name="test",
            template="Write about {topic}.",
            required_variables=["topic"],
        )

        with pytest.raises(ValueError):
            template.render({})  # Missing required variable


class TestOpenAIProvider:
    """Test OpenAI provider."""

    @pytest.mark.asyncio
    async def test_openai_generate_mock(self, mock_openai_provider):
        """Test OpenAI generation with mock."""
        request = GenerationRequest(
            prompt="What is artificial intelligence?",
            content_type=ContentType.NARRATIVE,
            max_tokens=500,
        )

        result = await mock_openai_provider.generate(request)

        assert result is not None
        assert len(result.content) > 0
        assert result.provider == LLMProvider.OPENAI
        assert result.model == "gpt-3.5-turbo"
        assert result.tokens_used > 0

    @pytest.mark.asyncio
    async def test_openai_empty_prompt(self, mock_openai_provider):
        """Test OpenAI with empty prompt."""
        request = GenerationRequest(prompt="")

        with pytest.raises(ValidationException):
            await mock_openai_provider.generate(request)

    @pytest.mark.asyncio
    async def test_openai_validate_api_key(self, mock_openai_provider):
        """Test API key validation."""
        is_valid = await mock_openai_provider.validate_api_key()
        assert is_valid is True

    def test_openai_get_available_models(self, mock_openai_provider):
        """Test getting available models."""
        models = mock_openai_provider.get_available_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-3.5-turbo" in models or "gpt-4" in models

    def test_openai_calculate_cost(self, mock_openai_provider):
        """Test cost calculation."""
        cost = mock_openai_provider.calculate_cost(
            model="gpt-3.5-turbo",
            input_tokens=1000,
            output_tokens=500,
        )

        assert cost > 0.0
        assert isinstance(cost, float)

    def test_openai_provider_info(self, mock_openai_provider):
        """Test provider information."""
        assert mock_openai_provider.get_provider_name() == "OpenAI"
        assert mock_openai_provider.get_provider_type() == LLMProvider.OPENAI
        assert mock_openai_provider.supports_streaming() is True
        assert mock_openai_provider.supports_function_calling() is True


class TestAnthropicProvider:
    """Test Anthropic provider."""

    @pytest.mark.asyncio
    async def test_anthropic_generate_mock(self, mock_anthropic_provider):
        """Test Anthropic generation with mock."""
        request = GenerationRequest(
            prompt="What is machine learning?",
            content_type=ContentType.NARRATIVE,
            max_tokens=500,
        )

        result = await mock_anthropic_provider.generate(request)

        assert result is not None
        assert len(result.content) > 0
        assert result.provider == LLMProvider.ANTHROPIC
        assert "claude" in result.model
        assert result.tokens_used > 0

    @pytest.mark.asyncio
    async def test_anthropic_empty_prompt(self, mock_anthropic_provider):
        """Test Anthropic with empty prompt."""
        request = GenerationRequest(prompt="")

        with pytest.raises(ValidationException):
            await mock_anthropic_provider.generate(request)

    @pytest.mark.asyncio
    async def test_anthropic_validate_api_key(self, mock_anthropic_provider):
        """Test API key validation."""
        is_valid = await mock_anthropic_provider.validate_api_key()
        assert is_valid is True

    def test_anthropic_get_available_models(self, mock_anthropic_provider):
        """Test getting available models."""
        models = mock_anthropic_provider.get_available_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert any("claude" in model for model in models)

    def test_anthropic_calculate_cost(self, mock_anthropic_provider):
        """Test cost calculation."""
        cost = mock_anthropic_provider.calculate_cost(
            model="claude-3-sonnet-20240229",
            input_tokens=1000,
            output_tokens=500,
        )

        assert cost > 0.0
        assert isinstance(cost, float)

    def test_anthropic_provider_info(self, mock_anthropic_provider):
        """Test provider information."""
        assert mock_anthropic_provider.get_provider_name() == "Anthropic"
        assert mock_anthropic_provider.get_provider_type() == LLMProvider.ANTHROPIC
        assert mock_anthropic_provider.supports_streaming() is True
        assert mock_anthropic_provider.supports_function_calling() is False


class TestContentGenerator:
    """Test content generator."""

    def test_generator_initialization(self, content_generator):
        """Test generator initializes correctly."""
        assert len(content_generator.providers) == 2
        assert content_generator.default_provider == LLMProvider.OPENAI
        assert len(content_generator.templates) > 0

    @pytest.mark.asyncio
    async def test_generate_narrative(
        self, content_generator, sample_research_result
    ):
        """Test narrative generation."""
        result = await content_generator.generate_narrative(
            concept_label="Artificial Intelligence",
            research_result=sample_research_result,
            max_tokens=1000,
        )

        assert result is not None
        assert len(result.content) > 0
        assert result.provider in [LLMProvider.OPENAI, LLMProvider.ANTHROPIC]
        assert len(result.citations) > 0  # Should have embedded citations
        assert result.quality_score > 0

    @pytest.mark.asyncio
    async def test_generate_summary(
        self, content_generator, sample_research_result
    ):
        """Test summary generation."""
        result = await content_generator.generate_summary(
            concept_label="Artificial Intelligence",
            research_result=sample_research_result,
            max_tokens=300,
        )

        assert result is not None
        assert len(result.content) > 0
        assert result.quality_score > 0

    @pytest.mark.asyncio
    async def test_generate_definition(
        self, content_generator, sample_research_result
    ):
        """Test definition generation."""
        result = await content_generator.generate_definition(
            concept_label="Artificial Intelligence",
            research_result=sample_research_result,
            max_tokens=200,
        )

        assert result is not None
        assert len(result.content) > 0
        assert result.quality_score > 0

    @pytest.mark.asyncio
    async def test_generate_with_specific_provider(
        self, content_generator, sample_research_result
    ):
        """Test generation with specific provider."""
        result = await content_generator.generate_narrative(
            concept_label="AI",
            research_result=sample_research_result,
            provider=LLMProvider.ANTHROPIC,
        )

        assert result is not None
        assert result.provider == LLMProvider.ANTHROPIC

    def test_add_custom_template(self, content_generator):
        """Test adding custom template."""
        template = PromptTemplate(
            name="custom",
            content_type=ContentType.EXPLANATION,
            template="Explain {concept} in simple terms.",
            required_variables=["concept"],
        )

        content_generator.add_template(template)

        assert "custom" in content_generator.templates
        assert content_generator.templates["custom"] == template

    def test_get_metrics(self, content_generator):
        """Test getting metrics."""
        metrics = content_generator.get_metrics()

        assert metrics is not None
        assert metrics.total_requests >= 0

    @pytest.mark.asyncio
    async def test_metrics_tracking(
        self, content_generator, sample_research_result
    ):
        """Test that metrics are tracked correctly."""
        initial_requests = content_generator.metrics.total_requests

        await content_generator.generate_summary(
            concept_label="AI",
            research_result=sample_research_result,
        )

        assert content_generator.metrics.total_requests == initial_requests + 1
        assert content_generator.metrics.successful_generations > 0

    def test_get_metrics_summary(self, content_generator):
        """Test getting metrics summary."""
        summary = content_generator.get_metrics_summary()

        assert "total_requests" in summary
        assert "successful_generations" in summary
        assert "success_rate" in summary
        assert "total_cost" in summary
        assert "average_quality" in summary

    def test_summarize_facts(self, content_generator, sample_research_result):
        """Test fact summarization."""
        summary = content_generator._summarize_facts(sample_research_result)

        assert len(summary) > 0
        assert "AI" in summary or "artificial intelligence" in summary.lower()

    def test_extract_key_facts(self, content_generator, sample_research_result):
        """Test key fact extraction."""
        key_facts = content_generator._extract_key_facts(
            sample_research_result, limit=2
        )

        assert len(key_facts) > 0
        lines = key_facts.split("\n")
        assert len(lines) <= 2  # Should respect limit

    def test_embed_citations(self, content_generator, sample_research_result):
        """Test citation embedding."""
        content = GeneratedContent(content="Test content")

        enriched = content_generator._embed_citations(content, sample_research_result)

        assert len(enriched.citations) > 0
        assert all("source_name" in c for c in enriched.citations)


class TestGenerationEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_research_result(self, content_generator):
        """Test generation with empty research result."""
        empty_result = ResearchResult(
            concept_uri="http://example.org/test",
            concept_label="Test",
        )

        # Should still generate something
        result = await content_generator.generate_summary(
            concept_label="Test",
            research_result=empty_result,
        )

        assert result is not None
        assert len(result.content) > 0

    def test_template_with_optional_variables(self):
        """Test template with optional variables."""
        template = PromptTemplate(
            name="test",
            template="Write about {topic}. {optional}",
            required_variables=["topic"],
            optional_variables=["optional"],
        )

        # Should work even without optional variable
        rendered = template.render({"topic": "AI"})
        assert "AI" in rendered

    @pytest.mark.asyncio
    async def test_provider_fallback(self, content_generator, sample_research_result):
        """Test fallback to alternative provider."""
        # Generate with primary provider
        result = await content_generator.generate_narrative(
            concept_label="AI",
            research_result=sample_research_result,
        )

        # Should succeed with some provider
        assert result is not None
        assert result.provider in [LLMProvider.OPENAI, LLMProvider.ANTHROPIC]
