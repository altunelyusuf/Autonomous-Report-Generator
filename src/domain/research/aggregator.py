"""Research aggregator for combining multi-source results."""

import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from src.domain.research.models import Fact, KnowledgeSource, ResearchResult, SearchResult

logger = logging.getLogger(__name__)


class ResearchAggregator:
    """Aggregate and enhance research results from multiple sources.

    Features:
    - Duplicate detection and removal
    - Conflict resolution
    - Source reliability weighting
    - Fact ranking and scoring
    - Quality assessment
    """

    def __init__(
        self,
        min_confidence: float = 0.3,
        min_source_reliability: float = 0.5,
    ):
        """Initialize research aggregator.

        Args:
            min_confidence: Minimum confidence threshold for facts
            min_source_reliability: Minimum source reliability threshold
        """
        self.min_confidence = min_confidence
        self.min_source_reliability = min_source_reliability

    def aggregate(self, results: List[ResearchResult]) -> ResearchResult:
        """Aggregate multiple research results into one.

        Args:
            results: List of research results from different sources

        Returns:
            Aggregated research result
        """
        if not results:
            logger.warning("No results to aggregate")
            return ResearchResult()

        # Use first result as base
        aggregated = results[0]

        # Merge remaining results
        for result in results[1:]:
            aggregated = self._merge_results(aggregated, result)

        # Enhanced processing
        aggregated = self._enhance_result(aggregated)

        logger.info(
            f"Aggregated {len(results)} results into "
            f"{aggregated.get_fact_count()} facts from "
            f"{aggregated.get_source_count()} sources"
        )

        return aggregated

    def _merge_results(
        self, result1: ResearchResult, result2: ResearchResult
    ) -> ResearchResult:
        """Merge two research results.

        Args:
            result1: First result
            result2: Second result

        Returns:
            Merged result
        """
        # Add facts and sources from result2 to result1
        for fact in result2.get_facts():
            # Find corresponding source
            source = next(
                (s for s in result2.get_sources() if s.source_id == fact.source_id),
                None,
            )
            if source:
                result1.add_fact(fact, source)

        # Add raw results
        for raw_result in result2.get_raw_results():
            result1.add_raw_result(raw_result)

        return result1

    def _enhance_result(self, result: ResearchResult) -> ResearchResult:
        """Enhance result with aggregation improvements.

        Args:
            result: Research result to enhance

        Returns:
            Enhanced result
        """
        # 1. Remove duplicates
        removed = result.remove_duplicates()
        logger.debug(f"Removed {removed} duplicate facts")

        # 2. Filter low-quality facts
        facts = result.get_facts()
        filtered_facts = self._filter_low_quality(facts, result.get_sources())

        # Update facts
        result._facts = filtered_facts

        # 3. Resolve conflicts
        resolved_facts = self._resolve_conflicts(filtered_facts)
        result._facts = resolved_facts

        # 4. Apply source reliability weighting
        weighted_facts = self._apply_source_weighting(resolved_facts, result.get_sources())
        result._facts = weighted_facts

        # 5. Rank by relevance
        result.rank_by_relevance()

        # 6. Calculate final confidence
        result.calculate_confidence()

        return result

    def _filter_low_quality(
        self, facts: List[Fact], sources: List[KnowledgeSource]
    ) -> List[Fact]:
        """Filter out low-quality facts.

        Args:
            facts: List of facts
            sources: List of sources

        Returns:
            Filtered facts
        """
        source_map = {s.source_id: s for s in sources}
        filtered = []

        for fact in facts:
            # Check fact confidence
            if fact.confidence < self.min_confidence:
                logger.debug(
                    f"Filtering low-confidence fact: {fact.statement[:50]}..."
                )
                continue

            # Check source reliability
            source = source_map.get(fact.source_id)
            if source and source.reliability_score < self.min_source_reliability:
                logger.debug(
                    f"Filtering fact from unreliable source: {source.source_name}"
                )
                continue

            filtered.append(fact)

        logger.debug(f"Filtered {len(facts) - len(filtered)} low-quality facts")
        return filtered

    def _resolve_conflicts(self, facts: List[Fact]) -> List[Fact]:
        """Resolve conflicting facts.

        Args:
            facts: List of facts

        Returns:
            Facts with conflicts resolved
        """
        # Group facts by subject-predicate
        groups: Dict[Tuple[str, str], List[Fact]] = defaultdict(list)

        for fact in facts:
            if fact.subject and fact.predicate:
                key = (fact.subject, fact.predicate)
                groups[key].append(fact)

        resolved = []

        for key, group_facts in groups.items():
            if len(group_facts) == 1:
                # No conflict
                resolved.append(group_facts[0])
            else:
                # Potential conflict - check if objects differ
                objects = set(f.object for f in group_facts if f.object)

                if len(objects) <= 1:
                    # No actual conflict
                    resolved.extend(group_facts)
                else:
                    # Conflict exists - keep highest confidence
                    logger.debug(
                        f"Resolving conflict for {key}: {len(group_facts)} facts"
                    )
                    best_fact = max(group_facts, key=lambda f: f.confidence)
                    resolved.append(best_fact)

        # Add facts without subject-predicate structure
        for fact in facts:
            if not fact.subject or not fact.predicate:
                resolved.append(fact)

        conflicts_resolved = len(facts) - len(resolved)
        if conflicts_resolved > 0:
            logger.info(f"Resolved {conflicts_resolved} conflicting facts")

        return resolved

    def _apply_source_weighting(
        self, facts: List[Fact], sources: List[KnowledgeSource]
    ) -> List[Fact]:
        """Apply source reliability weighting to fact confidence.

        Args:
            facts: List of facts
            sources: List of sources

        Returns:
            Facts with weighted confidence
        """
        source_map = {s.source_id: s for s in sources}

        for fact in facts:
            source = source_map.get(fact.source_id)
            if source:
                # Adjust confidence based on source reliability
                # Formula: weighted_confidence = fact_confidence * source_reliability
                original_confidence = fact.confidence
                fact.confidence = original_confidence * source.reliability_score

                logger.debug(
                    f"Weighted fact confidence: {original_confidence:.2f} -> "
                    f"{fact.confidence:.2f} (source: {source.source_name})"
                )

        return facts

    def calculate_diversity_score(self, result: ResearchResult) -> float:
        """Calculate diversity score for research result.

        Measures how diverse the sources are.

        Args:
            result: Research result

        Returns:
            Diversity score (0.0 to 1.0)
        """
        sources = result.get_sources()
        if not sources:
            return 0.0

        # Count unique source types
        source_types = set(s.source_type for s in sources)
        type_diversity = len(source_types) / 3.0  # Assuming 3 source types max

        # Count unique sources
        source_count = len(sources)
        source_diversity = min(source_count / 5.0, 1.0)  # Cap at 5 sources

        # Combined score
        diversity = (type_diversity + source_diversity) / 2.0

        return min(diversity, 1.0)

    def calculate_quality_score(self, result: ResearchResult) -> float:
        """Calculate overall quality score for research result.

        Args:
            result: Research result

        Returns:
            Quality score (0.0 to 1.0)
        """
        scores = []

        # 1. Confidence score
        scores.append(result.confidence_score)

        # 2. Diversity score
        diversity = self.calculate_diversity_score(result)
        scores.append(diversity)

        # 3. Completeness score (fact count)
        fact_count = result.get_fact_count()
        completeness = min(fact_count / 20.0, 1.0)  # Cap at 20 facts
        scores.append(completeness)

        # 4. Source reliability average
        sources = result.get_sources()
        if sources:
            avg_reliability = sum(s.reliability_score for s in sources) / len(sources)
            scores.append(avg_reliability)

        # Calculate average
        quality = sum(scores) / len(scores) if scores else 0.0

        logger.info(f"Quality score: {quality:.2f}")
        return quality

    def identify_knowledge_gaps(self, result: ResearchResult) -> List[str]:
        """Identify potential knowledge gaps in research.

        Args:
            result: Research result

        Returns:
            List of identified gaps
        """
        gaps = []

        # Check fact count
        if result.get_fact_count() < 5:
            gaps.append("Insufficient facts (< 5)")

        # Check source diversity
        diversity = self.calculate_diversity_score(result)
        if diversity < 0.5:
            gaps.append("Low source diversity")

        # Check source types
        sources = result.get_sources()
        source_types = set(s.source_type for s in sources)

        from src.domain.research.models import SourceType

        if SourceType.ACADEMIC not in source_types:
            gaps.append("No academic sources")

        if SourceType.WIKIDATA not in source_types:
            gaps.append("No structured knowledge (Wikidata)")

        # Check confidence
        if result.confidence_score < 0.6:
            gaps.append("Low overall confidence")

        if gaps:
            logger.warning(f"Knowledge gaps identified: {', '.join(gaps)}")

        return gaps

    def suggest_additional_research(
        self, result: ResearchResult
    ) -> List[Dict[str, str]]:
        """Suggest additional research based on gaps.

        Args:
            result: Research result

        Returns:
            List of research suggestions
        """
        suggestions = []
        gaps = self.identify_knowledge_gaps(result)

        for gap in gaps:
            if "academic" in gap.lower():
                suggestions.append(
                    {
                        "type": "academic",
                        "reason": gap,
                        "suggestion": "Search academic databases for peer-reviewed content",
                    }
                )
            elif "wikidata" in gap.lower():
                suggestions.append(
                    {
                        "type": "wikidata",
                        "reason": gap,
                        "suggestion": "Query Wikidata for structured facts",
                    }
                )
            elif "fact" in gap.lower():
                suggestions.append(
                    {
                        "type": "web",
                        "reason": gap,
                        "suggestion": "Broaden web search to gather more facts",
                    }
                )

        return suggestions
