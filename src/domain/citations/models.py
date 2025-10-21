"""Domain models for citations and bibliography."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4


class CitationStyle(str, Enum):
    """Citation formatting styles."""

    APA = "apa"  # American Psychological Association
    MLA = "mla"  # Modern Language Association
    CHICAGO = "chicago"  # Chicago Manual of Style
    IEEE = "ieee"  # Institute of Electrical and Electronics Engineers
    HARVARD = "harvard"  # Harvard referencing


class SourceType(str, Enum):
    """Types of citation sources."""

    BOOK = "book"
    JOURNAL_ARTICLE = "journal_article"
    WEBSITE = "website"
    CONFERENCE_PAPER = "conference_paper"
    THESIS = "thesis"
    REPORT = "report"
    DATABASE = "database"
    OTHER = "other"


@dataclass
class Author:
    """Author information.

    Attributes:
        first_name: Author's first name
        last_name: Author's last name
        middle_name: Author's middle name/initial
        suffix: Suffix (Jr., Sr., III, etc.)
    """

    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    suffix: Optional[str] = None

    def get_full_name(self) -> str:
        """Get full name.

        Returns:
            Full name as string
        """
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(parts)

    def get_last_first(self) -> str:
        """Get name in 'Last, First' format.

        Returns:
            Name as 'Last, First'
        """
        name = self.last_name
        if self.first_name:
            name += f", {self.first_name}"
            if self.middle_name:
                name += f" {self.middle_name}"
        if self.suffix:
            name += f", {self.suffix}"
        return name

    def get_initials(self) -> str:
        """Get author initials.

        Returns:
            Initials (e.g., 'J. D.')
        """
        initials = []
        if self.first_name:
            initials.append(f"{self.first_name[0]}.")
        if self.middle_name:
            initials.append(f"{self.middle_name[0]}.")
        return " ".join(initials)


@dataclass
class Citation:
    """Citation information.

    Attributes:
        citation_id: Unique citation identifier
        source_type: Type of source
        title: Source title
        authors: List of authors
        publication_year: Year of publication
        publisher: Publisher name
        url: URL if available
        doi: DOI if available
        access_date: Date accessed (for web sources)
        pages: Page numbers
        volume: Volume number
        issue: Issue number
        journal: Journal name
        conference: Conference name
        location: Publication location
        isbn: ISBN for books
        metadata: Additional metadata
    """

    citation_id: UUID = field(default_factory=uuid4)
    source_type: SourceType = SourceType.OTHER
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    publication_year: Optional[int] = None
    publisher: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    access_date: Optional[datetime] = None
    pages: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    journal: Optional[str] = None
    conference: Optional[str] = None
    location: Optional[str] = None
    isbn: Optional[str] = None
    metadata: Dict[str, any] = field(default_factory=dict)

    def add_author(self, author: Author) -> None:
        """Add an author.

        Args:
            author: Author to add
        """
        self.authors.append(author)

    def get_author_names(self) -> List[str]:
        """Get list of author names.

        Returns:
            List of full author names
        """
        return [author.get_full_name() for author in self.authors]

    def has_doi(self) -> bool:
        """Check if citation has DOI.

        Returns:
            True if DOI exists
        """
        return bool(self.doi)

    def has_url(self) -> bool:
        """Check if citation has URL.

        Returns:
            True if URL exists
        """
        return bool(self.url)

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "citation_id": str(self.citation_id),
            "source_type": self.source_type.value,
            "title": self.title,
            "authors": [author.get_full_name() for author in self.authors],
            "publication_year": self.publication_year,
            "publisher": self.publisher,
            "url": self.url,
            "doi": self.doi,
            "journal": self.journal,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
        }


@dataclass
class InlineCitation:
    """Inline citation reference.

    Attributes:
        citation_id: Reference to full citation
        citation_number: Citation number in text
        page_numbers: Specific page numbers cited
        context: Context where citation appears
        exact_quote: Whether this is an exact quote
    """

    citation_id: UUID
    citation_number: int
    page_numbers: Optional[str] = None
    context: Optional[str] = None
    exact_quote: bool = False

    def format_inline(self, style: CitationStyle, authors: List[str], year: Optional[int]) -> str:
        """Format as inline citation.

        Args:
            style: Citation style to use
            authors: List of author last names
            year: Publication year

        Returns:
            Formatted inline citation
        """
        if style == CitationStyle.APA:
            return self._format_apa_inline(authors, year)
        elif style == CitationStyle.MLA:
            return self._format_mla_inline(authors)
        elif style == CitationStyle.CHICAGO:
            return self._format_chicago_inline(authors, year)
        elif style == CitationStyle.IEEE:
            return f"[{self.citation_number}]"
        else:
            return f"[{self.citation_number}]"

    def _format_apa_inline(self, authors: List[str], year: Optional[int]) -> str:
        """Format APA inline citation.

        Args:
            authors: Author last names
            year: Publication year

        Returns:
            APA inline citation
        """
        if not authors:
            return f"(n.d.)"

        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} & {authors[1]}"
        else:
            author_str = f"{authors[0]} et al."

        year_str = str(year) if year else "n.d."

        if self.page_numbers:
            return f"({author_str}, {year_str}, p. {self.page_numbers})"
        else:
            return f"({author_str}, {year_str})"

    def _format_mla_inline(self, authors: List[str]) -> str:
        """Format MLA inline citation.

        Args:
            authors: Author last names

        Returns:
            MLA inline citation
        """
        if not authors:
            return "(Unknown)"

        author_str = authors[0] if len(authors) == 1 else f"{authors[0]} et al."

        if self.page_numbers:
            return f"({author_str} {self.page_numbers})"
        else:
            return f"({author_str})"

    def _format_chicago_inline(self, authors: List[str], year: Optional[int]) -> str:
        """Format Chicago inline citation.

        Args:
            authors: Author last names
            year: Publication year

        Returns:
            Chicago inline citation
        """
        if not authors:
            return f"(n.d.)"

        author_str = authors[0] if len(authors) == 1 else f"{authors[0]} et al."
        year_str = str(year) if year else "n.d."

        if self.page_numbers:
            return f"({author_str} {year_str}, {self.page_numbers})"
        else:
            return f"({author_str} {year_str})"


@dataclass
class Bibliography:
    """Bibliography/References section.

    Attributes:
        bibliography_id: Unique identifier
        style: Citation style used
        citations: List of citations
        title: Bibliography title
        sorted: Whether citations are sorted
    """

    bibliography_id: UUID = field(default_factory=uuid4)
    style: CitationStyle = CitationStyle.APA
    citations: List[Citation] = field(default_factory=list)
    title: str = "References"
    sorted: bool = False

    def add_citation(self, citation: Citation) -> None:
        """Add a citation.

        Args:
            citation: Citation to add
        """
        self.citations.append(citation)
        self.sorted = False

    def remove_citation(self, citation_id: UUID) -> bool:
        """Remove a citation.

        Args:
            citation_id: ID of citation to remove

        Returns:
            True if removed
        """
        original_length = len(self.citations)
        self.citations = [c for c in self.citations if c.citation_id != citation_id]
        return len(self.citations) < original_length

    def get_citation(self, citation_id: UUID) -> Optional[Citation]:
        """Get citation by ID.

        Args:
            citation_id: Citation ID

        Returns:
            Citation if found
        """
        for citation in self.citations:
            if citation.citation_id == citation_id:
                return citation
        return None

    def sort_citations(self) -> None:
        """Sort citations alphabetically by author last name."""
        self.citations.sort(
            key=lambda c: (
                c.authors[0].last_name.lower() if c.authors else c.title.lower(),
                c.publication_year or 9999,
            )
        )
        self.sorted = True

    def get_citation_count(self) -> int:
        """Get number of citations.

        Returns:
            Citation count
        """
        return len(self.citations)

    def filter_by_type(self, source_type: SourceType) -> List[Citation]:
        """Filter citations by source type.

        Args:
            source_type: Source type to filter by

        Returns:
            List of matching citations
        """
        return [c for c in self.citations if c.source_type == source_type]

    def get_title_by_style(self) -> str:
        """Get bibliography title based on style.

        Returns:
            Appropriate title for the citation style
        """
        if self.style == CitationStyle.APA:
            return "References"
        elif self.style == CitationStyle.MLA:
            return "Works Cited"
        elif self.style == CitationStyle.CHICAGO:
            return "Bibliography"
        elif self.style == CitationStyle.IEEE:
            return "References"
        else:
            return "References"
