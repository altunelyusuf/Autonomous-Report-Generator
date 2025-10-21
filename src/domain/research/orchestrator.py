"""Research orchestrator for coordinating multi-source research."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.domain.research.aggregator import ResearchAggregator
from src.domain.research.exceptions import ResearchException
from src.domain.research.models import (
    Fact,
    KnowledgeSource,
    ResearchContext,
    ResearchProcess,
    ResearchResult,
    ResearchStatus,
    SearchResult,
    SourceType,
)
from src.domain.research.service import IResearchService

logger = logging.getLogger(__name__)


class ResearchOrchestrator:
    """Orchestrate domain research across multiple knowledge sources.

    Coordinates parallel research from web, academic, and Wikidata sources,
    aggregates results, and manages caching.

    Features:
    - Parallel research execution
    - Result aggregation
    - Error handling and fallbacks
    - Result caching
    - Progress tracking
    """

    def __init__(
        self,
        services: Dict[SourceType, IResearchService],
        cache_enabled: bool = True,
        cache_ttl_hours: int = 168,  # 1 week default
        max_concurrent: int = 3,
    ):
        """Initialize research orchestrator.

        Args:
            services: Dictionary of source type to research service
            cache_enabled: Whether to use caching
            cache_ttl_hours: Cache TTL in hours
            max_concurrent: Maximum concurrent research operations
        """
        self.services = services
        self.cache_enabled = cache_enabled
        self.cache_ttl_hours = cache_ttl_hours
        self.max_concurrent = max_concurrent

        # Research aggregator for enhanced result processing
        self.aggregator = ResearchAggregator()

        # Simple in-memory cache (in production, use Redis)
        self._cache: Dict[str, ResearchResult] = {}

        logger.info(
            f"Research orchestrator initialized with {len(services)} services"
        )

    async def research_concept(
        self,
        concept_uri: str,
        concept_label: str,
        context: Optional[ResearchContext] = None,
    ) -> ResearchResult:
        """Conduct comprehensive research on a concept.

        Executes parallel research across all configured sources,
        aggregates results, and handles errors gracefully.

        Args:
            concept_uri: URI of the ontology concept
            concept_label: Human-readable concept label
            context: Optional research context

        Returns:
            ResearchResult with aggregated findings

        Raises:
            ResearchException: If all research sources fail
        """
        logger.info(f"Starting research for concept: {concept_label} ({concept_uri})")

        # Check cache
        if self.cache_enabled:
            cached = self._get_from_cache(concept_uri)
            if cached:
                logger.info(f"Cache hit for concept: {concept_label}")
                cached.status = ResearchStatus.CACHED
                return cached

        # Initialize research result
        research_result = ResearchResult(
            concept_uri=concept_uri,
            concept_label=concept_label,
            status=ResearchStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )

        # Generate search queries for each source type
        queries = self._generate_queries(concept_label, context)

        # Execute parallel research
        research_processes = []
        tasks = []

        for source_type, service in self.services.items():
            query = queries.get(source_type, concept_label)

            process = ResearchProcess(
                source_type=source_type,
                query=query,
            )
            process.mark_started()
            research_processes.append(process)

            # Create async task
            task = self._research_from_source(
                service, query, context, process
            )
            tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Research failed for {research_processes[i].source_type.value}: {result}"
                )
                research_processes[i].mark_failed(str(result))
            else:
                research_processes[i].mark_completed(len(result))
                successful_results.extend(result)

        # Check if all sources failed
        if not successful_results:
            research_result.status = ResearchStatus.FAILED
            research_result.completed_at = datetime.utcnow()
            raise ResearchException(
                f"All research sources failed for concept: {concept_label}"
            )

        # Store raw results
        for search_result in successful_results:
            research_result.add_raw_result(search_result)

        # Extract facts from results
        facts = self._extract_facts_from_results(successful_results)

        # Add facts with sources
        for fact in facts:
            # Find or create source
            source = self._create_knowledge_source(fact.metadata.get("source_name", "Unknown"))
            research_result.add_fact(fact, source)

        # Enhanced aggregation and quality assessment
        research_result = self.aggregator._enhance_result(research_result)

        # Calculate quality metrics
        quality_score = self.aggregator.calculate_quality_score(research_result)
        diversity_score = self.aggregator.calculate_diversity_score(research_result)

        # Identify knowledge gaps
        gaps = self.aggregator.identify_knowledge_gaps(research_result)
        if gaps:
            logger.warning(f"Knowledge gaps for {concept_label}: {', '.join(gaps)}")
            suggestions = self.aggregator.suggest_additional_research(research_result)
            if suggestions:
                logger.info(f"Research suggestions: {len(suggestions)} recommendations available")

        logger.info(
            f"Quality metrics - Overall: {quality_score:.2f}, "
            f"Diversity: {diversity_score:.2f}, "
            f"Confidence: {research_result.confidence_score:.2f}"
        )

        # Mark completed
        research_result.status = ResearchStatus.COMPLETED
        research_result.completed_at = datetime.utcnow()

        # Cache result
        if self.cache_enabled:
            self._add_to_cache(concept_uri, research_result)

        logger.info(
            f"Research completed for {concept_label}: "
            f"{research_result.get_fact_count()} facts from "
            f"{research_result.get_source_count()} sources"
        )

        return research_result

    async def _research_from_source(
        self,
        service: IResearchService,
        query: str,
        context: Optional[ResearchContext],
        process: ResearchProcess,
    ) -> List[SearchResult]:
        """Execute research from a single source.

        Args:
            service: Research service
            query: Search query
            context: Research context
            process: Research process tracker

        Returns:
            List of search results

        Raises:
            Exception: If research fails
        """
        try:
            logger.debug(
                f"Researching from {service.get_source_name()}: '{query}'"
            )

            # Execute search
            results = await service.search(
                query=query,
                max_results=context.max_results if context else 10,
                context=context,
            )

            logger.debug(
                f"Got {len(results)} results from {service.get_source_name()}"
            )

            return results

        except Exception as e:
            logger.error(
                f"Research failed from {service.get_source_name()}: {e}"
            )
            raise

    def _generate_queries(
        self,
        concept_label: str,
        context: Optional[ResearchContext],
    ) -> Dict[SourceType, str]:
        """Generate optimized queries for each source type.

        Args:
            concept_label: Concept label
            context: Optional context

        Returns:
            Dictionary of source type to query string
        """
        queries = {}

        # Web search: broad, natural language
        web_query = concept_label
        if context and context.domain:
            web_query = f"{concept_label} {context.domain}"
        queries[SourceType.WEB] = web_query

        # Academic: more structured, quoted
        academic_query = f'"{concept_label}"'
        if context and context.domain:
            academic_query += f" AND {context.domain}"
        queries[SourceType.ACADEMIC] = academic_query

        # Wikidata: entity-based
        queries[SourceType.WIKIDATA] = concept_label

        return queries

    def _extract_facts_from_results(
        self, results: List[SearchResult]
    ) -> List[Fact]:
        """Extract facts from search results.

        Args:
            results: List of search results

        Returns:
            List of extracted facts
        """
        facts = []

        for result in results:
            # Create fact from snippet
            fact = Fact(
                statement=result.snippet,
                source_id=result.result_id,  # Use result ID as proxy for source
                confidence=result.relevance_score,
                metadata={
                    "source_name": result.source_name,
                    "url": result.url,
                    "title": result.title,
                },
            )
            facts.append(fact)

        return facts

    def _create_knowledge_source(self, source_name: str) -> KnowledgeSource:
        """Create a knowledge source object.

        Args:
            source_name: Source name

        Returns:
            KnowledgeSource object
        """
        # Determine source type and reliability from name
        source_type = SourceType.WEB
        reliability = 0.7

        if "wikidata" in source_name.lower():
            source_type = SourceType.WIKIDATA
            reliability = 0.9
        elif "academic" in source_name.lower() or "scholar" in source_name.lower():
            source_type = SourceType.ACADEMIC
            reliability = 0.95

        return KnowledgeSource(
            source_name=source_name,
            source_type=source_type,
            reliability_score=reliability,
        )

    def _get_from_cache(self, concept_uri: str) -> Optional[ResearchResult]:
        """Get result from cache.

        Args:
            concept_uri: Concept URI

        Returns:
            Cached result or None
        """
        if concept_uri in self._cache:
            cached = self._cache[concept_uri]

            # Check if expired
            if cached.expires_at and cached.expires_at < datetime.utcnow():
                logger.debug(f"Cache entry expired for: {concept_uri}")
                del self._cache[concept_uri]
                return None

            return cached

        return None

    def _add_to_cache(self, concept_uri: str, result: ResearchResult) -> None:
        """Add result to cache.

        Args:
            concept_uri: Concept URI
            result: Research result
        """
        # Set expiration
        result.expires_at = datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)

        # Add to cache
        self._cache[concept_uri] = result

        logger.debug(
            f"Added to cache: {concept_uri} (expires in {self.cache_ttl_hours}h)"
        )

    def clear_cache(self) -> int:
        """Clear all cached results.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cache entries")
        return count

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total = len(self._cache)
        expired = sum(
            1 for r in self._cache.values()
            if r.expires_at and r.expires_at < datetime.utcnow()
        )

        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
        }

    async def validate_all_services(self) -> Dict[SourceType, bool]:
        """Validate all configured services.

        Returns:
            Dictionary of source type to validation result
        """
        logger.info("Validating all research services")

        results = {}
        for source_type, service in self.services.items():
            try:
                is_valid = await service.validate_access()
                results[source_type] = is_valid
                logger.info(
                    f"{service.get_source_name()}: "
                    f"{'✓ Valid' if is_valid else '✗ Invalid'}"
                )
            except Exception as e:
                logger.error(f"Validation failed for {source_type.value}: {e}")
                results[source_type] = False

        return results
