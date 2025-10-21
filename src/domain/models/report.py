"""Domain models for report generation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ReportType(Enum):
    """Types of reports that can be generated."""

    COMPREHENSIVE = "comprehensive"
    EXECUTIVE = "executive"
    TARGETED = "targeted"
    COMPARATIVE = "comparative"


class ReportStatus(Enum):
    """Report generation status."""

    CREATED = "created"
    ANALYZING = "analyzing"
    RESEARCHING = "researching"
    GENERATING = "generating"
    QUALITY_CHECK = "quality_check"
    NEEDS_IMPROVEMENT = "needs_improvement"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SectionStatus(Enum):
    """Section generation status."""

    PENDING = "pending"
    RESEARCHING = "researching"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SemanticVersion:
    """Semantic version number."""

    major: int = 1
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        """String representation."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def increment_major(self) -> None:
        """Increment major version."""
        self.major += 1
        self.minor = 0
        self.patch = 0

    def increment_minor(self) -> None:
        """Increment minor version."""
        self.minor += 1
        self.patch = 0

    def increment_patch(self) -> None:
        """Increment patch version."""
        self.patch += 1


@dataclass
class ReportSection:
    """Single section in a report.

    Represents a hierarchical section that maps to an ontology class.
    Supports nested subsections and various content types.
    """

    section_id: UUID = field(default_factory=uuid4)
    section_number: str = ""
    section_title: str = ""
    section_description: Optional[str] = None
    hierarchy_level: int = 1
    order_index: int = 0

    # Ontology mapping
    mapped_class_uri: str = ""
    mapped_class_label: str = ""

    # Parent relationship
    parent_section_id: Optional[UUID] = None

    # Status
    status: SectionStatus = SectionStatus.PENDING

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_modified: datetime = field(default_factory=datetime.utcnow)

    # Content collections (populated later)
    _subsections: List["ReportSection"] = field(default_factory=list)
    _content: List[Any] = field(default_factory=list)  # List[ReportContent]

    # Metrics
    word_count: int = 0
    content_count: int = 0
    completeness_score: float = 0.0

    def add_subsection(self, section: "ReportSection") -> None:
        """Add a subsection.

        Args:
            section: Subsection to add
        """
        section.parent_section_id = self.section_id
        section.hierarchy_level = self.hierarchy_level + 1
        if section not in self._subsections:
            self._subsections.append(section)

    def remove_subsection(self, section_id: UUID) -> bool:
        """Remove a subsection.

        Args:
            section_id: ID of section to remove

        Returns:
            True if removed, False if not found
        """
        for i, section in enumerate(self._subsections):
            if section.section_id == section_id:
                self._subsections.pop(i)
                return True
        return False

    def get_subsections(self) -> List["ReportSection"]:
        """Get all direct subsections.

        Returns:
            List of subsections
        """
        return self._subsections.copy()

    def add_content(self, content: Any) -> None:
        """Add content to this section.

        Args:
            content: Content to add
        """
        self._content.append(content)
        self.content_count = len(self._content)

    def get_all_content(self) -> List[Any]:
        """Get all content in this section.

        Returns:
            List of content items
        """
        return self._content.copy()

    def calculate_completeness(self) -> float:
        """Calculate section completeness score.

        Returns:
            Completeness score (0-100)
        """
        score = 0.0

        # Has title
        if self.section_title:
            score += 20.0

        # Has description
        if self.section_description:
            score += 10.0

        # Has content
        if self._content:
            score += 40.0

        # Has subsections (if not a leaf)
        if self._subsections:
            score += 20.0
        elif self.hierarchy_level > 3:  # Leaf sections don't need subsections
            score += 20.0

        # All subsections complete
        if self._subsections:
            complete_subsections = sum(
                1 for s in self._subsections if s.status == SectionStatus.COMPLETED
            )
            score += 10.0 * (complete_subsections / len(self._subsections))

        self.completeness_score = min(score, 100.0)
        return self.completeness_score

    def has_minimum_content(self) -> bool:
        """Check if section has minimum required content.

        Returns:
            True if has minimum content
        """
        return len(self._content) > 0 or len(self._subsections) > 0

    def get_depth(self) -> int:
        """Get maximum depth of this section's tree.

        Returns:
            Maximum depth
        """
        if not self._subsections:
            return self.hierarchy_level

        return max(s.get_depth() for s in self._subsections)

    def get_ancestor_path(self) -> List["ReportSection"]:
        """Get path from root to this section.

        Note: This requires access to parent sections, which would
        typically be provided by the containing report.

        Returns:
            List of ancestor sections
        """
        # This is a placeholder - actual implementation would need
        # access to the parent report to traverse upward
        return [self]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "section_id": str(self.section_id),
            "section_number": self.section_number,
            "section_title": self.section_title,
            "section_description": self.section_description,
            "hierarchy_level": self.hierarchy_level,
            "order_index": self.order_index,
            "mapped_class_uri": self.mapped_class_uri,
            "mapped_class_label": self.mapped_class_label,
            "parent_section_id": str(self.parent_section_id) if self.parent_section_id else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "subsection_count": len(self._subsections),
            "content_count": self.content_count,
            "word_count": self.word_count,
            "completeness_score": self.completeness_score,
        }


@dataclass
class DomainReport:
    """Complete domain report.

    Represents a generated report with hierarchical sections,
    content, and metadata.
    """

    report_id: UUID = field(default_factory=uuid4)
    report_title: str = ""
    report_description: Optional[str] = None
    source_ontology_uri: str = ""
    report_type: ReportType = ReportType.COMPREHENSIVE

    # Status
    status: ReportStatus = ReportStatus.CREATED

    # Timestamps
    generation_date: datetime = field(default_factory=datetime.utcnow)
    last_modified_date: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Version
    version: SemanticVersion = field(default_factory=SemanticVersion)

    # User
    author_id: Optional[UUID] = None

    # Collections
    _sections: List[ReportSection] = field(default_factory=list)
    _output_formats: List[Any] = field(default_factory=list)  # List[OutputFormat]

    # Metrics
    quality_score: float = 0.0
    completeness_score: float = 0.0
    section_count: int = 0
    total_word_count: int = 0

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_section(self, section: ReportSection) -> None:
        """Add a top-level section.

        Args:
            section: Section to add
        """
        section.order_index = len(self._sections)
        self._sections.append(section)
        self.section_count = len(self._sections)

    def remove_section(self, section_id: UUID) -> bool:
        """Remove a section.

        Args:
            section_id: ID of section to remove

        Returns:
            True if removed, False if not found
        """
        for i, section in enumerate(self._sections):
            if section.section_id == section_id:
                self._sections.pop(i)
                self.section_count = len(self._sections)
                return True
        return False

    def get_section(self, section_id: UUID) -> Optional[ReportSection]:
        """Get a section by ID.

        Args:
            section_id: Section ID

        Returns:
            Section or None if not found
        """
        # Search top-level sections
        for section in self._sections:
            if section.section_id == section_id:
                return section
            # Search subsections recursively
            found = self._search_subsections(section, section_id)
            if found:
                return found
        return None

    def _search_subsections(
        self, section: ReportSection, section_id: UUID
    ) -> Optional[ReportSection]:
        """Recursively search subsections.

        Args:
            section: Current section
            section_id: Target section ID

        Returns:
            Section or None
        """
        for subsection in section.get_subsections():
            if subsection.section_id == section_id:
                return subsection
            found = self._search_subsections(subsection, section_id)
            if found:
                return found
        return None

    def get_all_sections(self) -> List[ReportSection]:
        """Get all sections (flattened).

        Returns:
            List of all sections
        """
        sections = []
        for section in self._sections:
            sections.append(section)
            sections.extend(self._get_all_subsections(section))
        return sections

    def _get_all_subsections(self, section: ReportSection) -> List[ReportSection]:
        """Recursively get all subsections.

        Args:
            section: Parent section

        Returns:
            List of all subsections
        """
        subsections = []
        for subsection in section.get_subsections():
            subsections.append(subsection)
            subsections.extend(self._get_all_subsections(subsection))
        return subsections

    def get_sections_by_level(self, level: int) -> List[ReportSection]:
        """Get all sections at a specific hierarchy level.

        Args:
            level: Hierarchy level

        Returns:
            List of sections at that level
        """
        return [s for s in self.get_all_sections() if s.hierarchy_level == level]

    def calculate_quality_score(self) -> float:
        """Calculate overall quality score.

        Returns:
            Quality score (0-100)
        """
        # This is a placeholder - actual implementation would
        # involve comprehensive quality checks
        scores = []

        # Completeness
        completeness = self.calculate_completeness()
        scores.append(completeness)

        # Structure quality (all sections have content)
        all_sections = self.get_all_sections()
        if all_sections:
            sections_with_content = sum(1 for s in all_sections if s.has_minimum_content())
            structure_score = (sections_with_content / len(all_sections)) * 100
            scores.append(structure_score)

        self.quality_score = sum(scores) / len(scores) if scores else 0.0
        return self.quality_score

    def calculate_completeness(self) -> float:
        """Calculate report completeness.

        Returns:
            Completeness score (0-100)
        """
        if not self._sections:
            return 0.0

        # Calculate completeness for all sections
        section_scores = [s.calculate_completeness() for s in self.get_all_sections()]

        self.completeness_score = sum(section_scores) / len(section_scores)
        return self.completeness_score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "report_id": str(self.report_id),
            "report_title": self.report_title,
            "report_description": self.report_description,
            "source_ontology_uri": self.source_ontology_uri,
            "report_type": self.report_type.value,
            "status": self.status.value,
            "generation_date": self.generation_date.isoformat(),
            "last_modified_date": self.last_modified_date.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "version": str(self.version),
            "author_id": str(self.author_id) if self.author_id else None,
            "quality_score": self.quality_score,
            "completeness_score": self.completeness_score,
            "section_count": self.section_count,
            "total_word_count": self.total_word_count,
            "sections": [s.to_dict() for s in self._sections],
            "config": self.config,
            "metadata": self.metadata,
        }
