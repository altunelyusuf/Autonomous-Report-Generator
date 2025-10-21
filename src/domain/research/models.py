"""Domain models for research and knowledge gathering."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class SourceType(Enum):
    """Types of knowledge sources."""

    WEB = "web"
    ACADEMIC = "academic"
    WIKIDATA = "wikidata"
    ONTOLOGY_ANNOTATION = "ontology_annotation"
    MANUAL = "manual"


class ResearchStatus(Enum):
    """Research process status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class KnowledgeSource:
    """A source of knowledge/information.

    Represents a specific source like Wikipedia, Semantic Scholar,
    or Wikidata that provides factual information.
    """

    source_id: UUID = field(default_factory=uuid4)
    source_name: str = ""
    source_type: SourceType = SourceType.WEB
    source_url: Optional[str] = None

    # Quality metrics
    reliability_score: float = 0.5  # 0.0 to 1.0
    domain_authority: float = 0.5  # 0.0 to 1.0

    # Access metadata
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    failure_count: int = 0

    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_id": str(self.source_id),
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "source_url": self.source_url,
            "reliability_score": self.reliability_score,
            "domain_authority": self.domain_authority,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
            "failure_count": self.failure_count,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }


@dataclass
class Fact:
    """A single factual statement.

    Represents an atomic piece of information extracted from a source.
    """

    fact_id: UUID = field(default_factory=uuid4)
    statement: str = ""

    # Optional structured representation
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None

    # Provenance
    source_id: UUID = field(default_factory=uuid4)
    confidence: float = 0.5  # 0.0 to 1.0

    # Metadata
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_conflicting(self, other: "Fact") -> bool:
        """Check if this fact conflicts with another.

        Args:
            other: Another fact

        Returns:
            True if facts conflict
        """
        # Simple heuristic: same subject and predicate but different object
        if self.subject and other.subject and self.predicate and other.predicate:
            return (
                self.subject == other.subject
                and self.predicate == other.predicate
                and self.object != other.object
            )
        return False

    def merge(self, other: "Fact") -> "Fact":
        """Merge with another fact (for duplicate handling).

        Args:
            other: Another fact to merge with

        Returns:
            Merged fact
        """
        # Take higher confidence
        if other.confidence > self.confidence:
            return other
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fact_id": str(self.fact_id),
            "statement": self.statement,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "source_id": str(self.source_id),
            "confidence": self.confidence,
            "extracted_at": self.extracted_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class SearchResult:
    """A single search result from a knowledge source."""

    result_id: UUID = field(default_factory=uuid4)
    title: str = ""
    snippet: str = ""
    url: Optional[str] = None
    source_name: str = ""
    relevance_score: float = 0.0  # 0.0 to 1.0

    # Content
    full_text: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None

    # Metadata
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "result_id": str(self.result_id),
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
            "source_name": self.source_name,
            "relevance_score": self.relevance_score,
            "author": self.author,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "retrieved_at": self.retrieved_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ResearchResult:
    """Aggregated research results for a concept.

    Contains facts and sources gathered from multiple knowledge sources.
    """

    research_id: UUID = field(default_factory=uuid4)

    # What was researched
    concept_uri: str = ""
    concept_label: str = ""

    # Collected data
    _facts: List[Fact] = field(default_factory=list)
    _sources: List[KnowledgeSource] = field(default_factory=list)
    _raw_results: List[SearchResult] = field(default_factory=list)

    # Metrics
    confidence_score: float = 0.0  # Overall confidence
    relevance_score: float = 0.0  # Overall relevance

    # Status
    status: ResearchStatus = ResearchStatus.PENDING

    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Cache
    expires_at: Optional[datetime] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_fact(self, fact: Fact, source: KnowledgeSource) -> None:
        """Add a fact with its source.

        Args:
            fact: Fact to add
            source: Source of the fact
        """
        self._facts.append(fact)

        # Add source if not already present
        if not any(s.source_id == source.source_id for s in self._sources):
            self._sources.append(source)

    def get_facts(self) -> List[Fact]:
        """Get all facts.

        Returns:
            List of facts
        """
        return self._facts.copy()

    def get_sources(self) -> List[KnowledgeSource]:
        """Get all sources.

        Returns:
            List of sources
        """
        return self._sources.copy()

    def add_raw_result(self, result: SearchResult) -> None:
        """Add a raw search result.

        Args:
            result: Search result to add
        """
        self._raw_results.append(result)

    def get_raw_results(self) -> List[SearchResult]:
        """Get all raw search results.

        Returns:
            List of search results
        """
        return self._raw_results.copy()

    def rank_by_relevance(self) -> None:
        """Sort facts by relevance/confidence."""
        self._facts.sort(key=lambda f: f.confidence, reverse=True)

    def remove_duplicates(self) -> int:
        """Remove duplicate facts.

        Returns:
            Number of duplicates removed
        """
        seen = set()
        unique_facts = []
        duplicates = 0

        for fact in self._facts:
            # Use statement as key for deduplication
            if fact.statement not in seen:
                seen.add(fact.statement)
                unique_facts.append(fact)
            else:
                duplicates += 1

        self._facts = unique_facts
        return duplicates

    def calculate_confidence(self) -> float:
        """Calculate overall confidence score.

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not self._facts:
            self.confidence_score = 0.0
            return 0.0

        # Average confidence of all facts
        total_confidence = sum(f.confidence for f in self._facts)
        self.confidence_score = total_confidence / len(self._facts)

        return self.confidence_score

    def get_fact_count(self) -> int:
        """Get number of facts.

        Returns:
            Fact count
        """
        return len(self._facts)

    def get_source_count(self) -> int:
        """Get number of unique sources.

        Returns:
            Source count
        """
        return len(self._sources)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "research_id": str(self.research_id),
            "concept_uri": self.concept_uri,
            "concept_label": self.concept_label,
            "facts": [f.to_dict() for f in self._facts],
            "sources": [s.to_dict() for s in self._sources],
            "fact_count": len(self._facts),
            "source_count": len(self._sources),
            "confidence_score": self.confidence_score,
            "relevance_score": self.relevance_score,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


@dataclass
class ResearchContext:
    """Context for research operations.

    Provides additional information to guide research.
    """

    domain: Optional[str] = None  # Domain/field (e.g., "wine", "medicine")
    language: str = "en"  # Preferred language
    max_results: int = 10  # Maximum results per source
    include_types: List[str] = field(default_factory=list)  # Preferred content types
    exclude_domains: List[str] = field(default_factory=list)  # Domains to exclude
    date_range: Optional[tuple] = None  # (start_date, end_date)

    # Additional context
    related_concepts: List[str] = field(default_factory=list)
    parent_concept: Optional[str] = None
    child_concepts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "language": self.language,
            "max_results": self.max_results,
            "include_types": self.include_types,
            "exclude_domains": self.exclude_domains,
            "related_concepts": self.related_concepts,
            "parent_concept": self.parent_concept,
            "child_concepts": self.child_concepts,
        }


@dataclass
class ResearchProcess:
    """A single research process execution.

    Tracks the execution of research from one source.
    """

    process_id: UUID = field(default_factory=uuid4)
    source_type: SourceType = SourceType.WEB
    query: str = ""

    # Status
    status: ResearchStatus = ResearchStatus.PENDING

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Results
    result_count: int = 0
    success: bool = False
    error_message: Optional[str] = None

    # Metrics
    api_calls: int = 0
    tokens_used: int = 0
    cost: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_started(self) -> None:
        """Mark process as started."""
        self.started_at = datetime.utcnow()
        self.status = ResearchStatus.IN_PROGRESS

    def mark_completed(self, result_count: int) -> None:
        """Mark process as completed.

        Args:
            result_count: Number of results obtained
        """
        self.completed_at = datetime.utcnow()
        self.status = ResearchStatus.COMPLETED
        self.result_count = result_count
        self.success = True

        if self.started_at:
            duration = self.completed_at - self.started_at
            self.duration_seconds = duration.total_seconds()

    def mark_failed(self, error_message: str) -> None:
        """Mark process as failed.

        Args:
            error_message: Error description
        """
        self.completed_at = datetime.utcnow()
        self.status = ResearchStatus.FAILED
        self.success = False
        self.error_message = error_message

        if self.started_at:
            duration = self.completed_at - self.started_at
            self.duration_seconds = duration.total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "process_id": str(self.process_id),
            "source_type": self.source_type.value,
            "query": self.query,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "result_count": self.result_count,
            "success": self.success,
            "error_message": self.error_message,
            "api_calls": self.api_calls,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "metadata": self.metadata,
        }
