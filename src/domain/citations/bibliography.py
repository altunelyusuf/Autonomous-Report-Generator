"""Bibliography builder and manager."""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from src.domain.citations.formatter import CitationFormatterFactory, ICitationFormatter
from src.domain.citations.models import (
    Author,
    Bibliography,
    Citation,
    CitationStyle,
    InlineCitation,
    SourceType,
)
from src.domain.research.models import KnowledgeSource

logger = logging.getLogger(__name__)


class BibliographyBuilder:
    """Build and manage bibliography.

    Features:
    - Add citations from various sources
    - Convert KnowledgeSource to Citation
    - Format citations in multiple styles
    - Generate inline citations
    - Sort and organize bibliography
    - Track citation usage
    """

    def __init__(self, style: CitationStyle = CitationStyle.APA):
        """Initialize bibliography builder.

        Args:
            style: Citation style to use
        """
        self.bibliography = Bibliography(style=style)
        self.formatter = CitationFormatterFactory.create_formatter(style)

        # Track citation usage (citation_id -> count)
        self.usage_count: Dict[UUID, int] = {}

        # Map source_id to citation_id for quick lookup
        self.source_to_citation: Dict[UUID, UUID] = {}

        logger.info(f"Bibliography builder initialized with {style.value} style")

    def add_citation(self, citation: Citation) -> UUID:
        """Add a citation to bibliography.

        Args:
            citation: Citation to add

        Returns:
            Citation ID
        """
        self.bibliography.add_citation(citation)
        self.usage_count[citation.citation_id] = 0

        logger.debug(f"Added citation: {citation.title}")

        return citation.citation_id

    def add_from_knowledge_source(self, source: KnowledgeSource) -> UUID:
        """Add citation from KnowledgeSource.

        Args:
            source: KnowledgeSource to convert

        Returns:
            Citation ID
        """
        # Check if already added
        if source.source_id in self.source_to_citation:
            return self.source_to_citation[source.source_id]

        # Create citation from source
        citation = self._convert_source_to_citation(source)

        # Add to bibliography
        citation_id = self.add_citation(citation)

        # Track mapping
        self.source_to_citation[source.source_id] = citation_id

        return citation_id

    def add_from_knowledge_sources(self, sources: List[KnowledgeSource]) -> List[UUID]:
        """Add multiple citations from KnowledgeSources.

        Args:
            sources: List of sources

        Returns:
            List of citation IDs
        """
        citation_ids = []
        for source in sources:
            citation_id = self.add_from_knowledge_source(source)
            citation_ids.append(citation_id)

        logger.info(f"Added {len(citation_ids)} citations from knowledge sources")

        return citation_ids

    def create_inline_citation(
        self,
        citation_id: UUID,
        page_numbers: Optional[str] = None,
        exact_quote: bool = False,
    ) -> Optional[InlineCitation]:
        """Create inline citation.

        Args:
            citation_id: ID of citation to reference
            page_numbers: Specific page numbers
            exact_quote: Whether this is an exact quote

        Returns:
            InlineCitation object, or None if citation not found
        """
        citation = self.bibliography.get_citation(citation_id)
        if not citation:
            logger.warning(f"Citation {citation_id} not found")
            return None

        # Increment usage count
        self.usage_count[citation_id] = self.usage_count.get(citation_id, 0) + 1

        # Get citation number (1-based)
        citation_number = self._get_citation_number(citation_id)

        # Create inline citation
        inline = InlineCitation(
            citation_id=citation_id,
            citation_number=citation_number,
            page_numbers=page_numbers,
            exact_quote=exact_quote,
        )

        return inline

    def format_inline_citation(
        self,
        citation_id: UUID,
        page_numbers: Optional[str] = None,
    ) -> str:
        """Format inline citation text.

        Args:
            citation_id: Citation ID
            page_numbers: Page numbers

        Returns:
            Formatted inline citation
        """
        citation = self.bibliography.get_citation(citation_id)
        if not citation:
            return "[?]"

        inline = self.create_inline_citation(citation_id, page_numbers)
        if not inline:
            return "[?]"

        # Get author last names
        authors = [a.last_name for a in citation.authors]

        return inline.format_inline(
            self.bibliography.style,
            authors,
            citation.publication_year,
        )

    def generate_bibliography(self, sort: bool = True) -> str:
        """Generate formatted bibliography.

        Args:
            sort: Whether to sort citations

        Returns:
            Formatted bibliography text
        """
        if sort:
            self.bibliography.sort_citations()

        # Get title based on style
        title = self.bibliography.get_title_by_style()

        lines = [f"# {title}\n"]

        # Format each citation
        for i, citation in enumerate(self.bibliography.citations, 1):
            formatted = self.formatter.format_bibliography_entry(citation, i)
            lines.append(formatted)
            lines.append("")  # Blank line between entries

        return "\n".join(lines)

    def get_unused_citations(self) -> List[Citation]:
        """Get citations that haven't been used.

        Returns:
            List of unused citations
        """
        unused = []
        for citation in self.bibliography.citations:
            if self.usage_count.get(citation.citation_id, 0) == 0:
                unused.append(citation)

        return unused

    def remove_unused_citations(self) -> int:
        """Remove citations that haven't been referenced.

        Returns:
            Number of citations removed
        """
        unused = self.get_unused_citations()
        removed = 0

        for citation in unused:
            if self.bibliography.remove_citation(citation.citation_id):
                removed += 1
                # Clean up tracking
                self.usage_count.pop(citation.citation_id, None)

        logger.info(f"Removed {removed} unused citations")

        return removed

    def get_statistics(self) -> Dict[str, any]:
        """Get bibliography statistics.

        Returns:
            Dictionary with statistics
        """
        total = self.bibliography.get_citation_count()
        used = sum(1 for count in self.usage_count.values() if count > 0)
        unused = total - used

        # Count by source type
        type_counts = {}
        for citation in self.bibliography.citations:
            type_name = citation.source_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_citations": total,
            "used_citations": used,
            "unused_citations": unused,
            "citations_by_type": type_counts,
            "most_cited": self._get_most_cited(limit=5),
        }

    def change_style(self, new_style: CitationStyle) -> None:
        """Change citation style.

        Args:
            new_style: New citation style
        """
        self.bibliography.style = new_style
        self.formatter = CitationFormatterFactory.create_formatter(new_style)

        logger.info(f"Changed citation style to {new_style.value}")

    def _convert_source_to_citation(self, source: KnowledgeSource) -> Citation:
        """Convert KnowledgeSource to Citation.

        Args:
            source: KnowledgeSource

        Returns:
            Citation object
        """
        # Determine source type
        source_type = self._map_source_type(source.source_type.value)

        # Extract metadata
        metadata = source.metadata or {}

        # Parse authors if available
        authors = []
        if "authors" in metadata:
            authors = self._parse_authors(metadata["authors"])

        # Create citation
        citation = Citation(
            source_type=source_type,
            title=metadata.get("title", source.source_name),
            authors=authors,
            publication_year=metadata.get("year"),
            publisher=metadata.get("publisher"),
            url=metadata.get("url", source.url),
            doi=metadata.get("doi"),
            journal=metadata.get("journal"),
            volume=metadata.get("volume"),
            issue=metadata.get("issue"),
            pages=metadata.get("pages"),
            metadata=metadata,
        )

        return citation

    def _map_source_type(self, source_type_str: str) -> SourceType:
        """Map source type string to SourceType enum.

        Args:
            source_type_str: Source type as string

        Returns:
            SourceType enum
        """
        mapping = {
            "web": SourceType.WEBSITE,
            "academic": SourceType.JOURNAL_ARTICLE,
            "wikidata": SourceType.DATABASE,
            "book": SourceType.BOOK,
            "database": SourceType.DATABASE,
        }

        return mapping.get(source_type_str.lower(), SourceType.OTHER)

    def _parse_authors(self, authors_data: any) -> List[Author]:
        """Parse authors from various formats.

        Args:
            authors_data: Authors in various formats

        Returns:
            List of Author objects
        """
        authors = []

        if isinstance(authors_data, list):
            for author_item in authors_data:
                if isinstance(author_item, dict):
                    # Dictionary format
                    author = Author(
                        first_name=author_item.get("first_name", ""),
                        last_name=author_item.get("last_name", "Unknown"),
                        middle_name=author_item.get("middle_name"),
                    )
                    authors.append(author)
                elif isinstance(author_item, str):
                    # String format: try to parse
                    author = self._parse_author_string(author_item)
                    if author:
                        authors.append(author)

        elif isinstance(authors_data, str):
            # Single author as string
            author = self._parse_author_string(authors_data)
            if author:
                authors.append(author)

        return authors

    def _parse_author_string(self, author_str: str) -> Optional[Author]:
        """Parse author from string.

        Args:
            author_str: Author as string (e.g., "John Doe" or "Doe, John")

        Returns:
            Author object or None
        """
        author_str = author_str.strip()
        if not author_str:
            return None

        # Check for "Last, First" format
        if "," in author_str:
            parts = author_str.split(",", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
            return Author(first_name=first_name, last_name=last_name)

        # "First Last" format
        parts = author_str.split()
        if len(parts) >= 2:
            return Author(
                first_name=parts[0],
                last_name=" ".join(parts[1:])
            )
        elif len(parts) == 1:
            return Author(first_name="", last_name=parts[0])

        return None

    def _get_citation_number(self, citation_id: UUID) -> int:
        """Get citation number (1-based).

        Args:
            citation_id: Citation ID

        Returns:
            Citation number
        """
        for i, citation in enumerate(self.bibliography.citations, 1):
            if citation.citation_id == citation_id:
                return i

        return 0

    def _get_most_cited(self, limit: int = 5) -> List[Dict[str, any]]:
        """Get most cited sources.

        Args:
            limit: Maximum number to return

        Returns:
            List of citation info with usage counts
        """
        # Sort by usage count
        sorted_citations = sorted(
            self.usage_count.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

        results = []
        for citation_id, count in sorted_citations:
            citation = self.bibliography.get_citation(citation_id)
            if citation:
                results.append({
                    "title": citation.title,
                    "authors": citation.get_author_names(),
                    "usage_count": count,
                })

        return results
