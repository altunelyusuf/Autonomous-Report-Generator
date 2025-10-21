"""Unit tests for ResearchAggregator."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.domain.research.aggregator import ResearchAggregator
from src.domain.research.models import (
    Fact,
    KnowledgeSource,
    ResearchResult,
    ResearchStatus,
    SearchResult,
    SourceType,
)


@pytest.fixture
def aggregator():
    """Create test aggregator."""
    return ResearchAggregator(
        min_confidence=0.3,
        min_source_reliability=0.5,
    )


@pytest.fixture
def sample_sources():
    """Create sample knowledge sources."""
    return [
        KnowledgeSource(
            source_name="Wikipedia",
            source_type=SourceType.WEB,
            reliability_score=0.7,
        ),
        KnowledgeSource(
            source_name="Semantic Scholar",
            source_type=SourceType.ACADEMIC,
            reliability_score=0.95,
        ),
        KnowledgeSource(
            source_name="Wikidata",
            source_type=SourceType.WIKIDATA,
            reliability_score=0.9,
        ),
    ]


@pytest.fixture
def sample_facts(sample_sources):
    """Create sample facts."""
    return [
        Fact(
            statement="Machine learning is a subset of artificial intelligence.",
            subject="Machine Learning",
            predicate="is_a",
            object="Artificial Intelligence",
            confidence=0.9,
            source_id=sample_sources[0].source_id,
        ),
        Fact(
            statement="Deep learning uses neural networks.",
            subject="Deep Learning",
            predicate="uses",
            object="Neural Networks",
            confidence=0.85,
            source_id=sample_sources[1].source_id,
        ),
        Fact(
            statement="AI was founded as an academic discipline in 1956.",
            confidence=0.8,
            source_id=sample_sources[2].source_id,
        ),
    ]


@pytest.fixture
def sample_research_result(sample_facts, sample_sources):
    """Create sample research result."""
    result = ResearchResult(
        concept_uri="http://example.org/AI",
        concept_label="Artificial Intelligence",
        status=ResearchStatus.COMPLETED,
    )

    for fact, source in zip(sample_facts, sample_sources):
        result.add_fact(fact, source)

    return result


class TestResearchAggregator:
    """Test ResearchAggregator class."""

    def test_aggregator_initialization(self, aggregator):
        """Test aggregator initializes correctly."""
        assert aggregator.min_confidence == 0.3
        assert aggregator.min_source_reliability == 0.5

    def test_aggregate_empty_results(self, aggregator):
        """Test aggregating empty results list."""
        result = aggregator.aggregate([])
        assert result is not None
        assert result.get_fact_count() == 0

    def test_aggregate_single_result(self, aggregator, sample_research_result):
        """Test aggregating single result."""
        aggregated = aggregator.aggregate([sample_research_result])

        assert aggregated is not None
        assert aggregated.concept_uri == "http://example.org/AI"
        assert aggregated.get_fact_count() >= 1

    def test_aggregate_multiple_results(self, aggregator):
        """Test aggregating multiple results."""
        # Create two research results
        result1 = ResearchResult(
            concept_uri="http://example.org/AI",
            concept_label="AI",
        )
        source1 = KnowledgeSource(
            source_name="Source1",
            source_type=SourceType.WEB,
            reliability_score=0.8,
        )
        fact1 = Fact(
            statement="Fact from source 1",
            confidence=0.9,
            source_id=source1.source_id,
        )
        result1.add_fact(fact1, source1)

        result2 = ResearchResult(
            concept_uri="http://example.org/AI",
            concept_label="AI",
        )
        source2 = KnowledgeSource(
            source_name="Source2",
            source_type=SourceType.ACADEMIC,
            reliability_score=0.95,
        )
        fact2 = Fact(
            statement="Fact from source 2",
            confidence=0.85,
            source_id=source2.source_id,
        )
        result2.add_fact(fact2, source2)

        # Aggregate
        aggregated = aggregator.aggregate([result1, result2])

        # Should combine facts from both
        assert aggregated.get_fact_count() >= 2
        assert aggregated.get_source_count() >= 2

    def test_filter_low_quality_facts(self, aggregator):
        """Test filtering low-quality facts."""
        # Create facts with varying confidence
        source = KnowledgeSource(
            source_name="Test Source",
            source_type=SourceType.WEB,
            reliability_score=0.8,
        )

        facts = [
            Fact(
                statement="High confidence fact",
                confidence=0.9,
                source_id=source.source_id,
            ),
            Fact(
                statement="Low confidence fact",
                confidence=0.1,  # Below min_confidence threshold
                source_id=source.source_id,
            ),
            Fact(
                statement="Medium confidence fact",
                confidence=0.5,
                source_id=source.source_id,
            ),
        ]

        filtered = aggregator._filter_low_quality(facts, [source])

        # Should filter out low confidence fact
        assert len(filtered) == 2
        assert all(f.confidence >= aggregator.min_confidence for f in filtered)

    def test_filter_unreliable_sources(self, aggregator):
        """Test filtering facts from unreliable sources."""
        # Create reliable and unreliable sources
        reliable_source = KnowledgeSource(
            source_name="Reliable",
            source_type=SourceType.ACADEMIC,
            reliability_score=0.9,
        )
        unreliable_source = KnowledgeSource(
            source_name="Unreliable",
            source_type=SourceType.WEB,
            reliability_score=0.3,  # Below min_source_reliability threshold
        )

        facts = [
            Fact(
                statement="Fact from reliable source",
                confidence=0.8,
                source_id=reliable_source.source_id,
            ),
            Fact(
                statement="Fact from unreliable source",
                confidence=0.8,
                source_id=unreliable_source.source_id,
            ),
        ]

        filtered = aggregator._filter_low_quality(
            facts, [reliable_source, unreliable_source]
        )

        # Should filter out fact from unreliable source
        assert len(filtered) == 1
        assert filtered[0].source_id == reliable_source.source_id

    def test_resolve_conflicts_no_conflict(self, aggregator):
        """Test conflict resolution when no conflicts exist."""
        source_id = uuid4()
        facts = [
            Fact(
                statement="Fact 1",
                subject="A",
                predicate="relates_to",
                object="B",
                confidence=0.9,
                source_id=source_id,
            ),
            Fact(
                statement="Fact 2",
                subject="C",
                predicate="relates_to",
                object="D",
                confidence=0.8,
                source_id=source_id,
            ),
        ]

        resolved = aggregator._resolve_conflicts(facts)

        # No conflicts, should keep all facts
        assert len(resolved) == 2

    def test_resolve_conflicts_with_conflict(self, aggregator):
        """Test conflict resolution when conflicts exist."""
        source_id = uuid4()

        # Create conflicting facts (same subject-predicate, different objects)
        facts = [
            Fact(
                statement="AI was founded in 1956",
                subject="AI",
                predicate="founded_in",
                object="1956",
                confidence=0.9,
                source_id=source_id,
            ),
            Fact(
                statement="AI was founded in 1950",
                subject="AI",
                predicate="founded_in",
                object="1950",
                confidence=0.6,
                source_id=source_id,
            ),
        ]

        resolved = aggregator._resolve_conflicts(facts)

        # Should keep only the higher confidence fact
        assert len(resolved) == 1
        assert resolved[0].object == "1956"
        assert resolved[0].confidence == 0.9

    def test_apply_source_weighting(self, aggregator, sample_sources):
        """Test applying source reliability weighting."""
        facts = [
            Fact(
                statement="Fact from web",
                confidence=0.8,
                source_id=sample_sources[0].source_id,  # Web: 0.7 reliability
            ),
            Fact(
                statement="Fact from academic",
                confidence=0.8,
                source_id=sample_sources[1].source_id,  # Academic: 0.95 reliability
            ),
        ]

        weighted = aggregator._apply_source_weighting(facts, sample_sources)

        # Web fact: 0.8 * 0.7 = 0.56
        assert weighted[0].confidence == pytest.approx(0.56, rel=0.01)

        # Academic fact: 0.8 * 0.95 = 0.76
        assert weighted[1].confidence == pytest.approx(0.76, rel=0.01)

    def test_calculate_diversity_score_empty(self, aggregator):
        """Test diversity score for empty result."""
        result = ResearchResult(
            concept_uri="http://example.org/test",
            concept_label="Test",
        )

        diversity = aggregator.calculate_diversity_score(result)
        assert diversity == 0.0

    def test_calculate_diversity_score_single_source(self, aggregator, sample_sources):
        """Test diversity score for single source."""
        result = ResearchResult(
            concept_uri="http://example.org/test",
            concept_label="Test",
        )

        fact = Fact(
            statement="Test fact",
            confidence=0.8,
            source_id=sample_sources[0].source_id,
        )
        result.add_fact(fact, sample_sources[0])

        diversity = aggregator.calculate_diversity_score(result)

        # Should have some diversity (1 source type, 1 source)
        assert 0.0 < diversity < 1.0

    def test_calculate_diversity_score_multiple_sources(
        self, aggregator, sample_facts, sample_sources
    ):
        """Test diversity score for multiple diverse sources."""
        result = ResearchResult(
            concept_uri="http://example.org/test",
            concept_label="Test",
        )

        # Add facts from different source types
        for fact, source in zip(sample_facts, sample_sources):
            result.add_fact(fact, source)

        diversity = aggregator.calculate_diversity_score(result)

        # Should have high diversity (3 source types, 3 sources)
        assert diversity > 0.5

    def test_calculate_quality_score(self, aggregator, sample_research_result):
        """Test overall quality score calculation."""
        quality = aggregator.calculate_quality_score(sample_research_result)

        # Should be between 0 and 1
        assert 0.0 <= quality <= 1.0

        # With good sources and facts, should be reasonably high
        assert quality > 0.5

    def test_identify_knowledge_gaps_insufficient_facts(self, aggregator):
        """Test gap identification for insufficient facts."""
        result = ResearchResult(
            concept_uri="http://example.org/test",
            concept_label="Test",
        )

        source = KnowledgeSource(
            source_name="Source",
            source_type=SourceType.WEB,
            reliability_score=0.8,
        )

        # Add only 2 facts (below threshold of 5)
        for i in range(2):
            fact = Fact(
                statement=f"Fact {i}",
                confidence=0.8,
                source_id=source.source_id,
            )
            result.add_fact(fact, source)

        result.calculate_confidence()
        gaps = aggregator.identify_knowledge_gaps(result)

        # Should identify insufficient facts
        assert any("Insufficient facts" in gap for gap in gaps)

    def test_identify_knowledge_gaps_missing_source_types(self, aggregator):
        """Test gap identification for missing source types."""
        result = ResearchResult(
            concept_uri="http://example.org/test",
            concept_label="Test",
        )

        # Only use web source, missing academic and wikidata
        source = KnowledgeSource(
            source_name="Web Source",
            source_type=SourceType.WEB,
            reliability_score=0.8,
        )

        for i in range(10):
            fact = Fact(
                statement=f"Fact {i}",
                confidence=0.8,
                source_id=source.source_id,
            )
            result.add_fact(fact, source)

        result.calculate_confidence()
        gaps = aggregator.identify_knowledge_gaps(result)

        # Should identify missing source types
        assert any("academic" in gap.lower() for gap in gaps)
        assert any("wikidata" in gap.lower() for gap in gaps)

    def test_suggest_additional_research(self, aggregator):
        """Test research suggestions based on gaps."""
        result = ResearchResult(
            concept_uri="http://example.org/test",
            concept_label="Test",
        )

        # Create result with gaps
        source = KnowledgeSource(
            source_name="Web Source",
            source_type=SourceType.WEB,
            reliability_score=0.8,
        )

        for i in range(3):  # Insufficient facts
            fact = Fact(
                statement=f"Fact {i}",
                confidence=0.8,
                source_id=source.source_id,
            )
            result.add_fact(fact, source)

        result.calculate_confidence()
        suggestions = aggregator.suggest_additional_research(result)

        # Should provide suggestions
        assert len(suggestions) > 0
        assert all("type" in s and "reason" in s and "suggestion" in s for s in suggestions)

    def test_enhance_result_workflow(self, aggregator, sample_research_result):
        """Test complete enhancement workflow."""
        # Add duplicate fact
        duplicate_fact = Fact(
            statement=sample_research_result.get_facts()[0].statement,  # Same as first fact
            confidence=0.7,
            source_id=sample_research_result.get_sources()[0].source_id,
        )
        sample_research_result.add_fact(
            duplicate_fact, sample_research_result.get_sources()[0]
        )

        initial_count = sample_research_result.get_fact_count()

        # Enhance
        enhanced = aggregator._enhance_result(sample_research_result)

        # Should have processed the result
        assert enhanced is not None
        assert enhanced.confidence_score > 0

        # Should have removed duplicate
        assert enhanced.get_fact_count() <= initial_count

    def test_merge_results(self, aggregator):
        """Test merging two research results."""
        # Create first result
        result1 = ResearchResult(
            concept_uri="http://example.org/test",
            concept_label="Test",
        )
        source1 = KnowledgeSource(
            source_name="Source1",
            source_type=SourceType.WEB,
            reliability_score=0.8,
        )
        fact1 = Fact(
            statement="Fact 1",
            confidence=0.9,
            source_id=source1.source_id,
        )
        result1.add_fact(fact1, source1)

        # Create second result
        result2 = ResearchResult(
            concept_uri="http://example.org/test",
            concept_label="Test",
        )
        source2 = KnowledgeSource(
            source_name="Source2",
            source_type=SourceType.ACADEMIC,
            reliability_score=0.95,
        )
        fact2 = Fact(
            statement="Fact 2",
            confidence=0.85,
            source_id=source2.source_id,
        )
        result2.add_fact(fact2, source2)

        # Merge
        merged = aggregator._merge_results(result1, result2)

        # Should contain facts from both
        assert merged.get_fact_count() >= 2
        assert merged.get_source_count() >= 2


class TestAggregatorEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_facts_list(self, aggregator):
        """Test handling empty facts list."""
        filtered = aggregator._filter_low_quality([], [])
        assert filtered == []

        resolved = aggregator._resolve_conflicts([])
        assert resolved == []

        weighted = aggregator._apply_source_weighting([], [])
        assert weighted == []

    def test_facts_without_subject_predicate(self, aggregator):
        """Test handling facts without structured fields."""
        source_id = uuid4()
        facts = [
            Fact(
                statement="Unstructured fact",
                confidence=0.8,
                source_id=source_id,
            ),
        ]

        # Should handle gracefully
        resolved = aggregator._resolve_conflicts(facts)
        assert len(resolved) == 1

    def test_source_weighting_missing_source(self, aggregator):
        """Test source weighting with missing source."""
        fact = Fact(
            statement="Fact",
            confidence=0.8,
            source_id=uuid4(),  # Source not in sources list
        )

        # Should handle gracefully (confidence unchanged)
        weighted = aggregator._apply_source_weighting([fact], [])
        assert weighted[0].confidence == 0.8
