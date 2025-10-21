"""Citation formatters for various styles."""

import logging
from abc import ABC, abstractmethod
from typing import List

from src.domain.citations.models import Author, Citation, CitationStyle, SourceType

logger = logging.getLogger(__name__)


class ICitationFormatter(ABC):
    """Interface for citation formatters."""

    @abstractmethod
    def format_citation(self, citation: Citation) -> str:
        """Format a full citation.

        Args:
            citation: Citation to format

        Returns:
            Formatted citation string
        """
        pass

    @abstractmethod
    def format_bibliography_entry(self, citation: Citation, number: int) -> str:
        """Format a bibliography entry.

        Args:
            citation: Citation to format
            number: Entry number (if numbered)

        Returns:
            Formatted bibliography entry
        """
        pass

    @abstractmethod
    def get_style_name(self) -> str:
        """Get style name.

        Returns:
            Style name
        """
        pass


class APAFormatter(ICitationFormatter):
    """APA (American Psychological Association) citation formatter.

    7th Edition format.
    """

    def format_citation(self, citation: Citation) -> str:
        """Format citation in APA style.

        Args:
            citation: Citation to format

        Returns:
            APA formatted citation
        """
        parts = []

        # Authors
        authors_str = self._format_authors(citation.authors)
        if authors_str:
            parts.append(authors_str)

        # Year
        year = f"({citation.publication_year})" if citation.publication_year else "(n.d.)"
        parts.append(year)

        # Title
        if citation.title:
            if citation.source_type == SourceType.BOOK:
                parts.append(f"*{citation.title}*")
            else:
                parts.append(citation.title)

        # Source-specific formatting
        if citation.source_type == SourceType.JOURNAL_ARTICLE:
            if citation.journal:
                journal_str = f"*{citation.journal}*"
                if citation.volume:
                    journal_str += f", *{citation.volume}*"
                    if citation.issue:
                        journal_str += f"({citation.issue})"
                if citation.pages:
                    journal_str += f", {citation.pages}"
                parts.append(journal_str)

        elif citation.source_type == SourceType.BOOK:
            if citation.publisher:
                parts.append(citation.publisher)

        elif citation.source_type == SourceType.WEBSITE:
            if citation.url:
                parts.append(citation.url)

        # DOI or URL
        if citation.doi:
            parts.append(f"https://doi.org/{citation.doi}")
        elif citation.url and citation.source_type != SourceType.WEBSITE:
            parts.append(citation.url)

        return ". ".join(parts) + "."

    def format_bibliography_entry(self, citation: Citation, number: int) -> str:
        """Format APA bibliography entry.

        Args:
            citation: Citation
            number: Entry number (not used in APA)

        Returns:
            Formatted entry
        """
        return self.format_citation(citation)

    def _format_authors(self, authors: List[Author]) -> str:
        """Format authors in APA style.

        Args:
            authors: List of authors

        Returns:
            Formatted author string
        """
        if not authors:
            return ""

        if len(authors) == 1:
            return authors[0].get_last_first()

        if len(authors) <= 20:
            # List all authors
            author_strs = [a.get_last_first() for a in authors[:-1]]
            return ", ".join(author_strs) + f", & {authors[-1].get_last_first()}"

        # More than 20 authors: list first 19, then ..., then last
        author_strs = [a.get_last_first() for a in authors[:19]]
        return ", ".join(author_strs) + f", ... {authors[-1].get_last_first()}"

    def get_style_name(self) -> str:
        """Get style name."""
        return "APA"


class MLAFormatter(ICitationFormatter):
    """MLA (Modern Language Association) citation formatter.

    9th Edition format.
    """

    def format_citation(self, citation: Citation) -> str:
        """Format citation in MLA style.

        Args:
            citation: Citation to format

        Returns:
            MLA formatted citation
        """
        parts = []

        # Authors
        authors_str = self._format_authors(citation.authors)
        if authors_str:
            parts.append(authors_str + ".")

        # Title
        if citation.title:
            if citation.source_type == SourceType.BOOK:
                parts.append(f"*{citation.title}*.")
            elif citation.source_type == SourceType.JOURNAL_ARTICLE:
                parts.append(f'"{citation.title}."')
            else:
                parts.append(f'"{citation.title}."')

        # Container (journal, website, etc.)
        if citation.source_type == SourceType.JOURNAL_ARTICLE and citation.journal:
            container = f"*{citation.journal}*"
            if citation.volume:
                container += f", vol. {citation.volume}"
            if citation.issue:
                container += f", no. {citation.issue}"
            if citation.publication_year:
                container += f", {citation.publication_year}"
            if citation.pages:
                container += f", pp. {citation.pages}"
            parts.append(container + ".")

        elif citation.source_type == SourceType.BOOK:
            if citation.publisher:
                pub_str = citation.publisher
                if citation.publication_year:
                    pub_str += f", {citation.publication_year}"
                parts.append(pub_str + ".")

        elif citation.source_type == SourceType.WEBSITE:
            if citation.publisher:
                parts.append(f"*{citation.publisher}*,")
            if citation.publication_year:
                parts.append(f"{citation.publication_year}.")

        # URL or DOI
        if citation.url:
            parts.append(citation.url + ".")

        return " ".join(parts)

    def format_bibliography_entry(self, citation: Citation, number: int) -> str:
        """Format MLA bibliography entry.

        Args:
            citation: Citation
            number: Entry number (not used in MLA)

        Returns:
            Formatted entry
        """
        return self.format_citation(citation)

    def _format_authors(self, authors: List[Author]) -> str:
        """Format authors in MLA style.

        Args:
            authors: List of authors

        Returns:
            Formatted author string
        """
        if not authors:
            return ""

        if len(authors) == 1:
            return authors[0].get_last_first()

        if len(authors) == 2:
            return f"{authors[0].get_last_first()}, and {authors[1].get_full_name()}"

        # Three or more authors
        return f"{authors[0].get_last_first()}, et al"

    def get_style_name(self) -> str:
        """Get style name."""
        return "MLA"


class ChicagoFormatter(ICitationFormatter):
    """Chicago Manual of Style citation formatter.

    17th Edition format (Notes and Bibliography).
    """

    def format_citation(self, citation: Citation) -> str:
        """Format citation in Chicago style.

        Args:
            citation: Citation to format

        Returns:
            Chicago formatted citation
        """
        parts = []

        # Authors
        authors_str = self._format_authors(citation.authors)
        if authors_str:
            parts.append(authors_str + ".")

        # Title
        if citation.title:
            if citation.source_type == SourceType.BOOK:
                parts.append(f"*{citation.title}*.")
            elif citation.source_type == SourceType.JOURNAL_ARTICLE:
                parts.append(f'"{citation.title}."')
            else:
                parts.append(f'"{citation.title}."')

        # Publication info
        if citation.source_type == SourceType.JOURNAL_ARTICLE and citation.journal:
            journal_parts = [f"*{citation.journal}*"]
            if citation.volume:
                journal_parts.append(f"{citation.volume}")
                if citation.issue:
                    journal_parts.append(f"no. {citation.issue}")
            if citation.publication_year:
                journal_parts.append(f"({citation.publication_year})")
            journal_str = ", ".join(journal_parts)
            if citation.pages:
                journal_str += f": {citation.pages}"
            parts.append(journal_str + ".")

        elif citation.source_type == SourceType.BOOK:
            pub_parts = []
            if citation.location:
                pub_parts.append(citation.location)
            if citation.publisher:
                pub_parts.append(citation.publisher)
            if citation.publication_year:
                pub_parts.append(str(citation.publication_year))
            if pub_parts:
                parts.append(": ".join(pub_parts) + ".")

        # DOI or URL
        if citation.doi:
            parts.append(f"https://doi.org/{citation.doi}.")
        elif citation.url:
            parts.append(citation.url + ".")

        return " ".join(parts)

    def format_bibliography_entry(self, citation: Citation, number: int) -> str:
        """Format Chicago bibliography entry.

        Args:
            citation: Citation
            number: Entry number (not used in bibliography)

        Returns:
            Formatted entry
        """
        return self.format_citation(citation)

    def _format_authors(self, authors: List[Author]) -> str:
        """Format authors in Chicago style.

        Args:
            authors: List of authors

        Returns:
            Formatted author string
        """
        if not authors:
            return ""

        if len(authors) == 1:
            return authors[0].get_last_first()

        if len(authors) <= 10:
            author_strs = [authors[0].get_last_first()]
            author_strs.extend([a.get_full_name() for a in authors[1:-1]])
            author_strs.append(f"and {authors[-1].get_full_name()}")
            return ", ".join(author_strs)

        # More than 10 authors
        author_strs = [authors[0].get_last_first()]
        author_strs.extend([a.get_full_name() for a in authors[1:7]])
        return ", ".join(author_strs) + ", et al"

    def get_style_name(self) -> str:
        """Get style name."""
        return "Chicago"


class IEEEFormatter(ICitationFormatter):
    """IEEE citation formatter.

    Numbered citation style.
    """

    def format_citation(self, citation: Citation) -> str:
        """Format citation in IEEE style.

        Args:
            citation: Citation to format

        Returns:
            IEEE formatted citation
        """
        parts = []

        # Authors
        authors_str = self._format_authors(citation.authors)
        if authors_str:
            parts.append(authors_str + ",")

        # Title
        if citation.title:
            if citation.source_type == SourceType.BOOK:
                parts.append(f"*{citation.title}*,")
            else:
                parts.append(f'"{citation.title},"')

        # Source info
        if citation.source_type == SourceType.JOURNAL_ARTICLE and citation.journal:
            journal_str = f"*{citation.journal}*"
            if citation.volume:
                journal_str += f", vol. {citation.volume}"
            if citation.issue:
                journal_str += f", no. {citation.issue}"
            if citation.pages:
                journal_str += f", pp. {citation.pages}"
            if citation.publication_year:
                journal_str += f", {citation.publication_year}"
            parts.append(journal_str + ".")

        elif citation.source_type == SourceType.BOOK:
            if citation.publisher:
                pub_str = citation.publisher
                if citation.publication_year:
                    pub_str += f", {citation.publication_year}"
                parts.append(pub_str + ".")

        # DOI or URL
        if citation.doi:
            parts.append(f"doi: {citation.doi}.")
        elif citation.url:
            parts.append(f"[Online]. Available: {citation.url}")

        return " ".join(parts)

    def format_bibliography_entry(self, citation: Citation, number: int) -> str:
        """Format IEEE bibliography entry.

        Args:
            citation: Citation
            number: Entry number

        Returns:
            Formatted entry with number
        """
        citation_text = self.format_citation(citation)
        return f"[{number}] {citation_text}"

    def _format_authors(self, authors: List[Author]) -> str:
        """Format authors in IEEE style.

        Args:
            authors: List of authors

        Returns:
            Formatted author string
        """
        if not authors:
            return ""

        # IEEE uses First Initial. Last Name format
        if len(authors) == 1:
            return f"{authors[0].get_initials()} {authors[0].last_name}"

        if len(authors) <= 6:
            author_strs = [
                f"{a.get_initials()} {a.last_name}"
                for a in authors
            ]
            return ", ".join(author_strs[:-1]) + f", and {author_strs[-1]}"

        # More than 6 authors
        author_strs = [
            f"{a.get_initials()} {a.last_name}"
            for a in authors[:6]
        ]
        return ", ".join(author_strs) + ", et al"

    def get_style_name(self) -> str:
        """Get style name."""
        return "IEEE"


class CitationFormatterFactory:
    """Factory for creating citation formatters."""

    @staticmethod
    def create_formatter(style: CitationStyle) -> ICitationFormatter:
        """Create formatter for given style.

        Args:
            style: Citation style

        Returns:
            Citation formatter

        Raises:
            ValueError: If style not supported
        """
        if style == CitationStyle.APA:
            return APAFormatter()
        elif style == CitationStyle.MLA:
            return MLAFormatter()
        elif style == CitationStyle.CHICAGO:
            return ChicagoFormatter()
        elif style == CitationStyle.IEEE:
            return IEEEFormatter()
        else:
            logger.warning(f"Unsupported style {style}, defaulting to APA")
            return APAFormatter()

    @staticmethod
    def get_supported_styles() -> List[CitationStyle]:
        """Get list of supported citation styles.

        Returns:
            List of supported styles
        """
        return [
            CitationStyle.APA,
            CitationStyle.MLA,
            CitationStyle.CHICAGO,
            CitationStyle.IEEE,
        ]
