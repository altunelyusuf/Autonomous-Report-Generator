"""Content generator for report sections."""

import logging
from typing import Dict, List, Optional

from src.domain.generation.exceptions import GenerationException, ValidationException
from src.domain.generation.models import (
    ContentType,
    GeneratedContent,
    GenerationMetrics,
    GenerationRequest,
    LLMProvider,
    PromptTemplate,
)
from src.domain.generation.provider import ILLMProvider
from src.domain.research.models import ResearchResult

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generate content for report sections using LLMs.

    Coordinates content generation across multiple LLM providers,
    manages prompt templates, and tracks generation metrics.

    Features:
    - Multi-provider support (OpenAI, Anthropic)
    - Template-based prompt generation
    - Citation embedding
    - Quality assessment
    - Cost tracking
    - Fallback handling
    """

    def __init__(
        self,
        providers: Dict[LLMProvider, ILLMProvider],
        default_provider: LLMProvider = LLMProvider.OPENAI,
    ):
        """Initialize content generator.

        Args:
            providers: Dictionary of provider type to provider instance
            default_provider: Default provider to use
        """
        self.providers = providers
        self.default_provider = default_provider
        self.metrics = GenerationMetrics()

        # Built-in prompt templates
        self.templates = self._create_default_templates()

        logger.info(
            f"Content generator initialized with {len(providers)} providers"
        )

    async def generate_narrative(
        self,
        concept_label: str,
        research_result: ResearchResult,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        provider: Optional[LLMProvider] = None,
    ) -> GeneratedContent:
        """Generate narrative content for a concept.

        Args:
            concept_label: Concept label
            research_result: Research results to base narrative on
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            provider: Preferred provider (uses default if None)

        Returns:
            Generated narrative content

        Raises:
            GenerationException: If generation fails
        """
        logger.info(f"Generating narrative for: {concept_label}")

        # Get template
        template = self.templates.get("narrative")
        if not template:
            raise GenerationException("Narrative template not found")

        # Build context from research results
        facts_summary = self._summarize_facts(research_result)
        sources_summary = self._summarize_sources(research_result)

        # Render prompt
        prompt = template.render({
            "concept": concept_label,
            "facts": facts_summary,
            "sources": sources_summary,
            "fact_count": research_result.get_fact_count(),
        })

        # Create generation request
        request = GenerationRequest(
            content_type=ContentType.NARRATIVE,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            provider=provider or self.default_provider,
            research_results=[research_result.to_dict()],
            citations_required=True,
            context={
                "system_prompt": template.system_prompt,
                "concept_label": concept_label,
            },
        )

        # Generate content
        result = await self._generate_with_fallback(request)

        # Embed citations
        result = self._embed_citations(result, research_result)

        # Calculate quality
        result.calculate_quality_score()

        logger.info(
            f"Narrative generated: {result.tokens_used} tokens, "
            f"quality={result.quality_score:.2f}, ${result.cost:.4f}"
        )

        return result

    async def generate_summary(
        self,
        concept_label: str,
        research_result: ResearchResult,
        max_tokens: int = 500,
        provider: Optional[LLMProvider] = None,
    ) -> GeneratedContent:
        """Generate summary content for a concept.

        Args:
            concept_label: Concept label
            research_result: Research results
            max_tokens: Maximum tokens
            provider: Preferred provider

        Returns:
            Generated summary
        """
        logger.info(f"Generating summary for: {concept_label}")

        template = self.templates.get("summary")
        if not template:
            raise GenerationException("Summary template not found")

        # Build context
        key_facts = self._extract_key_facts(research_result, limit=5)

        # Render prompt
        prompt = template.render({
            "concept": concept_label,
            "key_facts": key_facts,
        })

        # Create request
        request = GenerationRequest(
            content_type=ContentType.SUMMARY,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.5,  # Lower temperature for summaries
            provider=provider or self.default_provider,
            context={
                "system_prompt": template.system_prompt,
            },
        )

        # Generate
        result = await self._generate_with_fallback(request)
        result.calculate_quality_score()

        return result

    async def generate_definition(
        self,
        concept_label: str,
        research_result: ResearchResult,
        max_tokens: int = 300,
        provider: Optional[LLMProvider] = None,
    ) -> GeneratedContent:
        """Generate definition for a concept.

        Args:
            concept_label: Concept label
            research_result: Research results
            max_tokens: Maximum tokens
            provider: Preferred provider

        Returns:
            Generated definition
        """
        logger.info(f"Generating definition for: {concept_label}")

        template = self.templates.get("definition")
        if not template:
            raise GenerationException("Definition template not found")

        # Extract definitional facts
        definitional_facts = self._extract_definitional_facts(research_result)

        # Render prompt
        prompt = template.render({
            "concept": concept_label,
            "facts": definitional_facts,
        })

        # Create request
        request = GenerationRequest(
            content_type=ContentType.DEFINITION,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.3,  # Low temperature for definitions
            provider=provider or self.default_provider,
            context={
                "system_prompt": template.system_prompt,
            },
        )

        # Generate
        result = await self._generate_with_fallback(request)
        result.calculate_quality_score()

        return result

    async def _generate_with_fallback(
        self,
        request: GenerationRequest,
    ) -> GeneratedContent:
        """Generate content with fallback to alternative providers.

        Args:
            request: Generation request

        Returns:
            Generated content

        Raises:
            GenerationException: If all providers fail
        """
        # Try primary provider
        primary_provider = self.providers.get(request.provider)

        if primary_provider:
            try:
                result = await primary_provider.generate(request)

                # Record success
                self.metrics.record_generation(
                    success=True,
                    provider=request.provider,
                    model=result.model,
                    tokens=result.tokens_used,
                    cost=result.cost,
                    quality=result.quality_score,
                )

                return result

            except Exception as e:
                logger.warning(
                    f"Primary provider {request.provider.value} failed: {e}"
                )
                # Record failure
                self.metrics.record_generation(
                    success=False,
                    provider=request.provider,
                    model="unknown",
                    tokens=0,
                    cost=0.0,
                    quality=0.0,
                )

        # Try fallback providers
        for provider_type, provider in self.providers.items():
            if provider_type == request.provider:
                continue  # Already tried

            try:
                logger.info(f"Trying fallback provider: {provider_type.value}")
                result = await provider.generate(request)

                # Record success
                self.metrics.record_generation(
                    success=True,
                    provider=provider_type,
                    model=result.model,
                    tokens=result.tokens_used,
                    cost=result.cost,
                    quality=result.quality_score,
                )

                return result

            except Exception as e:
                logger.warning(f"Fallback provider {provider_type.value} failed: {e}")
                # Record failure
                self.metrics.record_generation(
                    success=False,
                    provider=provider_type,
                    model="unknown",
                    tokens=0,
                    cost=0.0,
                    quality=0.0,
                )

        # All providers failed
        raise GenerationException("All LLM providers failed")

    def _summarize_facts(self, research_result: ResearchResult) -> str:
        """Summarize facts from research result.

        Args:
            research_result: Research result

        Returns:
            Summarized facts as string
        """
        facts = research_result.get_facts()
        if not facts:
            return "No facts available."

        # Get top facts by confidence
        top_facts = sorted(facts, key=lambda f: f.confidence, reverse=True)[:10]

        summary = "\n".join(
            f"- {fact.statement}" for fact in top_facts
        )

        return summary

    def _summarize_sources(self, research_result: ResearchResult) -> str:
        """Summarize sources from research result.

        Args:
            research_result: Research result

        Returns:
            Summarized sources as string
        """
        sources = research_result.get_sources()
        if not sources:
            return "No sources available."

        summary = "\n".join(
            f"- {source.source_name} ({source.source_type.value})"
            for source in sources
        )

        return summary

    def _extract_key_facts(
        self, research_result: ResearchResult, limit: int = 5
    ) -> str:
        """Extract key facts for summarization.

        Args:
            research_result: Research result
            limit: Maximum number of facts

        Returns:
            Key facts as string
        """
        facts = research_result.get_facts()
        if not facts:
            return "No facts available."

        # Sort by confidence and relevance
        top_facts = sorted(
            facts,
            key=lambda f: (f.confidence, f.relevance_score or 0),
            reverse=True,
        )[:limit]

        return "\n".join(f"- {fact.statement}" for fact in top_facts)

    def _extract_definitional_facts(self, research_result: ResearchResult) -> str:
        """Extract facts useful for definitions.

        Args:
            research_result: Research result

        Returns:
            Definitional facts as string
        """
        facts = research_result.get_facts()
        if not facts:
            return "No facts available."

        # Look for facts with definitional predicates
        definitional_predicates = {"is_a", "subclass_of", "type", "definition"}

        definitional_facts = [
            f for f in facts
            if f.predicate and f.predicate.lower() in definitional_predicates
        ]

        # If no specific definitional facts, use high-confidence facts
        if not definitional_facts:
            definitional_facts = sorted(
                facts, key=lambda f: f.confidence, reverse=True
            )[:3]

        return "\n".join(f"- {fact.statement}" for fact in definitional_facts)

    def _embed_citations(
        self,
        content: GeneratedContent,
        research_result: ResearchResult,
    ) -> GeneratedContent:
        """Embed citations into generated content.

        Args:
            content: Generated content
            research_result: Research results with sources

        Returns:
            Content with embedded citations
        """
        sources = research_result.get_sources()

        for i, source in enumerate(sources, 1):
            citation = {
                "id": i,
                "source_name": source.source_name,
                "source_type": source.source_type.value,
                "reliability": source.reliability_score,
                "url": source.metadata.get("url", ""),
            }
            content.add_citation(citation)

        logger.debug(f"Embedded {len(content.citations)} citations")

        return content

    def _create_default_templates(self) -> Dict[str, PromptTemplate]:
        """Create default prompt templates.

        Returns:
            Dictionary of template name to template
        """
        templates = {}

        # Narrative template
        templates["narrative"] = PromptTemplate(
            name="narrative",
            content_type=ContentType.NARRATIVE,
            template=(
                "Write a comprehensive narrative about {concept}.\n\n"
                "Use the following research facts:\n{facts}\n\n"
                "Sources ({fact_count} facts from multiple sources):\n{sources}\n\n"
                "Requirements:\n"
                "1. Create a cohesive narrative that synthesizes the research\n"
                "2. Maintain academic tone and accuracy\n"
                "3. Include relevant context and background\n"
                "4. Structure with clear paragraphs\n"
                "5. Cite sources appropriately"
            ),
            required_variables=["concept", "facts", "sources", "fact_count"],
            system_prompt=(
                "You are an expert technical writer creating comprehensive "
                "narratives for research reports. Your writing is clear, accurate, "
                "and well-structured."
            ),
        )

        # Summary template
        templates["summary"] = PromptTemplate(
            name="summary",
            content_type=ContentType.SUMMARY,
            template=(
                "Write a concise summary of {concept}.\n\n"
                "Key facts:\n{key_facts}\n\n"
                "Requirements:\n"
                "1. Keep it concise (2-3 paragraphs maximum)\n"
                "2. Focus on the most important points\n"
                "3. Use clear, accessible language"
            ),
            required_variables=["concept", "key_facts"],
            system_prompt=(
                "You are an expert at creating concise, informative summaries. "
                "You distill complex information into clear, accessible content."
            ),
        )

        # Definition template
        templates["definition"] = PromptTemplate(
            name="definition",
            content_type=ContentType.DEFINITION,
            template=(
                "Provide a clear, accurate definition of {concept}.\n\n"
                "Based on these facts:\n{facts}\n\n"
                "Requirements:\n"
                "1. Start with a formal definition\n"
                "2. Explain key characteristics\n"
                "3. Provide context if needed\n"
                "4. Keep it concise but complete"
            ),
            required_variables=["concept", "facts"],
            system_prompt=(
                "You are an expert at creating precise, clear definitions. "
                "Your definitions are accurate, well-structured, and informative."
            ),
        )

        return templates

    def add_template(self, template: PromptTemplate) -> None:
        """Add a custom prompt template.

        Args:
            template: Prompt template to add
        """
        self.templates[template.name] = template
        logger.info(f"Added template: {template.name}")

    def get_metrics(self) -> GenerationMetrics:
        """Get generation metrics.

        Returns:
            Current metrics
        """
        return self.metrics

    def get_metrics_summary(self) -> Dict[str, any]:
        """Get metrics summary.

        Returns:
            Dictionary with metrics summary
        """
        return {
            "total_requests": self.metrics.total_requests,
            "successful_generations": self.metrics.successful_generations,
            "failed_generations": self.metrics.failed_generations,
            "success_rate": self.metrics.get_success_rate(),
            "total_tokens": self.metrics.total_tokens,
            "total_cost": self.metrics.total_cost,
            "average_cost_per_request": self.metrics.get_average_cost_per_request(),
            "average_quality": self.metrics.average_quality,
            "provider_usage": self.metrics.provider_usage,
            "model_usage": self.metrics.model_usage,
        }
