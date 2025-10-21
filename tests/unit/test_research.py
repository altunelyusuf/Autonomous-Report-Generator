"""Unit tests for research services (Sprint 3)."""

import pytest

from src.domain.research.exceptions import SearchException, ValidationException
from src.domain.research.models import (
    Fact,
    KnowledgeSource,
    ResearchContext,
    ResearchResult,
    SourceType,
)
from src.domain.research.orchestrator import ResearchOrchestrator
from src.infrastructure.external_services.academic_api import MockAcademicAPIService
from src.infrastructure.external_services.web_search import MockWebSearchService
from src.infrastructure.external_services.wikidata_client import MockWikidataClient


class TestResearchModels:
    """Test research domain models."""

    def test_knowledge_source_creation(self):
        """Test creating a knowledge source."""
        source = KnowledgeSource(
            source_name="Wikipedia",
            source_type=SourceType.WEB,
            source_url="https://wikipedia.org",
            reliability_score=0.85,
        )

        assert source.source_name == "Wikipedia"
        assert source.source_type == SourceType.WEB
        assert source.reliability_score == 0.85
        assert source.is_active is True

    def test_fact_creation(self):
        """Test creating a fact."""
        fact = Fact(
            statement="Wine is an alcoholic beverage",
            subject="Wine",
            predicate="isA",
            object="Alcoholic Beverage",
            confidence=0.95,
        )

        assert fact.statement == "Wine is an alcoholic beverage"
        assert fact.confidence == 0.95

    def test_fact_conflict_detection(self):
        """Test detecting conflicting facts."""
        fact1 = Fact(
            statement="Wine is red",
            subject="Wine",
            predicate="hasColor",
            object="red",
        )

        fact2 = Fact(
            statement="Wine is white",
            subject="Wine",
            predicate="hasColor",
            object="white",
        )

        assert fact1.is_conflicting(fact2) is True

    def test_research_result_creation(self):
        """Test creating research result."""
        result = ResearchResult(
            concept_uri="http://example.org/Wine",
            concept_label="Wine",
        )

        assert result.concept_uri == "http://example.org/Wine"
        assert result.concept_label == "Wine"
        assert result.get_fact_count() == 0
        assert result.get_source_count() == 0

    def test_research_result_add_fact(self):
        """Test adding facts to research result."""
        result = ResearchResult(
            concept_uri="http://example.org/Wine",
            concept_label="Wine",
        )

        fact = Fact(statement="Wine is an alcoholic beverage")
        source = KnowledgeSource(source_name="Wikipedia")

        result.add_fact(fact, source)

        assert result.get_fact_count() == 1
        assert result.get_source_count() == 1

    def test_research_result_duplicate_removal(self):
        """Test removing duplicate facts."""
        result = ResearchResult(
            concept_uri="http://example.org/Wine",
            concept_label="Wine",
        )

        source = KnowledgeSource(source_name="Wikipedia")

        # Add same fact twice
        fact1 = Fact(statement="Wine is an alcoholic beverage")
        fact2 = Fact(statement="Wine is an alcoholic beverage")

        result.add_fact(fact1, source)
        result.add_fact(fact2, source)

        assert result.get_fact_count() == 2

        duplicates_removed = result.remove_duplicates()

        assert duplicates_removed == 1
        assert result.get_fact_count() == 1

    def test_research_result_confidence_calculation(self):
        """Test confidence score calculation."""
        result = ResearchResult(
            concept_uri="http://example.org/Wine",
            concept_label="Wine",
        )

        source = KnowledgeSource(source_name="Wikipedia")

        # Add facts with different confidence scores
        fact1 = Fact(statement="Fact 1", confidence=0.9)
        fact2 = Fact(statement="Fact 2", confidence=0.8)
        fact3 = Fact(statement="Fact 3", confidence=0.7)

        result.add_fact(fact1, source)
        result.add_fact(fact2, source)
        result.add_fact(fact3, source)

        confidence = result.calculate_confidence()

        # Average of 0.9, 0.8, 0.7 = 0.8
        assert confidence == pytest.approx(0.8, rel=0.01)

    def test_research_context(self):
        """Test research context creation."""
        context = ResearchContext(
            domain="wine",
            language="en",
            max_results=20,
            related_concepts=["red wine", "white wine"],
        )

        assert context.domain == "wine"
        assert context.language == "en"
        assert context.max_results == 20
        assert len(context.related_concepts) == 2


class TestWebSearchService:
    """Test web search service."""

    @pytest.mark.asyncio
    async def test_basic_search(self):
        """Test basic web search."""
        service = MockWebSearchService()

        results = await service.search("wine", max_results=5)

        assert len(results) > 0
        assert len(results) <= 5
        assert all(r.source_name == "Web Search" for r in results)

    @pytest.mark.asyncio
    async def test_search_with_context(self):
        """Test search with context."""
        service = MockWebSearchService()

        context = ResearchContext(
            domain="viticulture",
            max_results=3,
        )

        results = await service.search("wine", context=context)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_empty_query_validation(self):
        """Test empty query validation."""
        service = MockWebSearchService()

        with pytest.raises(ValidationException):
            await service.search("")

    @pytest.mark.asyncio
    async def test_validate_access(self):
        """Test service access validation."""
        service = MockWebSearchService()

        is_valid = await service.validate_access()

        assert is_valid is True

    def test_service_properties(self):
        """Test service properties."""
        service = MockWebSearchService(reliability_score=0.75)

        assert service.get_source_name() == "Web Search"
        assert service.get_source_type() == "web"
        assert service.get_reliability_score() == 0.75
        assert service.supports_advanced_search() is True


class TestWikidataClient:
    """Test Wikidata client."""

    @pytest.mark.asyncio
    async def test_basic_search(self):
        """Test basic Wikidata search."""
        client = MockWikidataClient()

        results = await client.search("wine", max_results=5)

        assert len(results) > 0
        assert len(results) <= 5
        assert all(r.source_name == "Wikidata" for r in results)
        assert all("entity_id" in r.metadata for r in results)

    @pytest.mark.asyncio
    async def test_entity_facts_extraction(self):
        """Test extracting facts from entity."""
        client = MockWikidataClient()

        facts = await client.get_entity_facts("Q1234")

        assert len(facts) > 0
        assert all(isinstance(f, Fact) for f in facts)
        assert all(f.confidence > 0 for f in facts)

    @pytest.mark.asyncio
    async def test_invalid_entity_id(self):
        """Test invalid entity ID."""
        client = MockWikidataClient()

        with pytest.raises(ValidationException):
            await client.get_entity_facts("INVALID")

    def test_wikidata_properties(self):
        """Test Wikidata client properties."""
        client = MockWikidataClient(reliability_score=0.9)

        assert client.get_source_name() == "Wikidata"
        assert client.get_source_type() == "wikidata"
        assert client.get_reliability_score() == 0.9
        assert client.get_cost_per_query() == 0.0
        assert client.supports_advanced_search() is True


class TestAcademicAPIService:
    """Test academic API service."""

    @pytest.mark.asyncio
    async def test_basic_search(self):
        """Test basic academic search."""
        service = MockAcademicAPIService()

        results = await service.search("wine production", max_results=5)

        assert len(results) > 0
        assert len(results) <= 5
        assert all("paper_id" in r.metadata for r in results)
        assert all("citations" in r.metadata for r in results)
        assert all(r.metadata["is_peer_reviewed"] for r in results)

    @pytest.mark.asyncio
    async def test_paper_details(self):
        """Test fetching paper details."""
        service = MockAcademicAPIService()

        details = await service.get_paper_details("PAPER123")

        assert details is not None
        assert "paper_id" in details
        assert "authors" in details
        assert "abstract" in details

    def test_academic_properties(self):
        """Test academic service properties."""
        service = MockAcademicAPIService(reliability_score=0.95)

        assert service.get_source_type() == "academic"
        assert service.get_reliability_score() == 0.95
        assert service.get_cost_per_query() == 0.0  # Most academic APIs are free


class TestResearchOrchestrator:
    """Test research orchestrator."""

    def create_orchestrator(self):
        """Create orchestrator with mock services."""
        services = {
            SourceType.WEB: MockWebSearchService(),
            SourceType.WIKIDATA: MockWikidataClient(),
            SourceType.ACADEMIC: MockAcademicAPIService(),
        }

        return ResearchOrchestrator(
            services=services,
            cache_enabled=True,
            max_concurrent=3,
        )

    @pytest.mark.asyncio
    async def test_basic_research(self):
        """Test basic concept research."""
        orchestrator = self.create_orchestrator()

        result = await orchestrator.research_concept(
            concept_uri="http://example.org/Wine",
            concept_label="Wine",
        )

        assert result is not None
        assert result.concept_uri == "http://example.org/Wine"
        assert result.concept_label == "Wine"
        assert result.get_fact_count() > 0
        assert result.get_source_count() > 0

    @pytest.mark.asyncio
    async def test_research_with_context(self):
        """Test research with context."""
        orchestrator = self.create_orchestrator()

        context = ResearchContext(
            domain="viticulture",
            max_results=5,
        )

        result = await orchestrator.research_concept(
            concept_uri="http://example.org/Wine",
            concept_label="Wine",
            context=context,
        )

        assert result is not None
        assert result.get_fact_count() > 0

    @pytest.mark.asyncio
    async def test_cache_functionality(self):
        """Test caching functionality."""
        orchestrator = self.create_orchestrator()

        # First research - should not be cached
        result1 = await orchestrator.research_concept(
            concept_uri="http://example.org/Wine",
            concept_label="Wine",
        )

        # Second research - should be cached
        result2 = await orchestrator.research_concept(
            concept_uri="http://example.org/Wine",
            concept_label="Wine",
        )

        # Second result should be from cache
        assert result2.status.value == "cached"

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel research execution."""
        orchestrator = self.create_orchestrator()

        # Research should execute all services in parallel
        result = await orchestrator.research_concept(
            concept_uri="http://example.org/Wine",
            concept_label="Wine",
        )

        # Should have results from multiple sources
        assert result.get_source_count() >= 1

    def test_cache_management(self):
        """Test cache management."""
        orchestrator = self.create_orchestrator()

        # Check initial stats
        stats = orchestrator.get_cache_stats()
        assert stats["total_entries"] == 0

        # Clear cache
        cleared = orchestrator.clear_cache()
        assert cleared == 0

    @pytest.mark.asyncio
    async def test_service_validation(self):
        """Test service validation."""
        orchestrator = self.create_orchestrator()

        results = await orchestrator.validate_all_services()

        assert len(results) == 3
        assert all(results.values())  # All services should be valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
