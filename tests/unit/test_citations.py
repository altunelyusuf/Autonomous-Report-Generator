"""Unit tests for citation management."""

import pytest

from src.domain.citations.bibliography import BibliographyBuilder
from src.domain.citations.formatter import (
    APAFormatter,
    ChicagoFormatter,
    CitationFormatterFactory,
    IEEEFormatter,
    MLAFormatter,
)
from src.domain.citations.models import (
    Author,
    Bibliography,
    Citation,
    CitationStyle,
    InlineCitation,
    SourceType,
)
from src.domain.research.models import KnowledgeSource, SourceType as ResearchSourceType


@pytest.fixture
def sample_author():
    """Create sample author."""
    return Author(
        first_name="John",
        last_name="Doe",
        middle_name="A",
    )


@pytest.fixture
def sample_authors():
    """Create sample author list."""
    return [
        Author(first_name="John", last_name="Doe"),
        Author(first_name="Jane", last_name="Smith"),
        Author(first_name="Bob", last_name="Johnson"),
    ]


@pytest.fixture
def sample_citation(sample_authors):
    """Create sample citation."""
    return Citation(
        source_type=SourceType.JOURNAL_ARTICLE,
        title="Machine Learning in Practice",
        authors=sample_authors[:2],  # Two authors
        publication_year=2023,
        journal="Journal of AI Research",
        volume="45",
        issue="3",
        pages="123-145",
        doi="10.1234/jair.2023.123",
    )


@pytest.fixture
def sample_book_citation(sample_authors):
    """Create sample book citation."""
    return Citation(
        source_type=SourceType.BOOK,
        title="Introduction to Artificial Intelligence",
        authors=sample_authors[:1],  # One author
        publication_year=2022,
        publisher="MIT Press",
        location="Cambridge, MA",
        isbn="978-0-262-12345-6",
    )


@pytest.fixture
def sample_website_citation(sample_authors):
    """Create sample website citation."""
    return Citation(
        source_type=SourceType.WEBSITE,
        title="Understanding Neural Networks",
        authors=sample_authors[:1],
        publication_year=2024,
        url="https://example.com/neural-networks",
        publisher="AI Learning Hub",
    )


class TestAuthor:
    """Test Author class."""

    def test_author_creation(self, sample_author):
        """Test creating an author."""
        assert sample_author.first_name == "John"
        assert sample_author.last_name == "Doe"
        assert sample_author.middle_name == "A"

    def test_get_full_name(self, sample_author):
        """Test getting full name."""
        assert sample_author.get_full_name() == "John A Doe"

    def test_get_last_first(self, sample_author):
        """Test getting name in Last, First format."""
        assert sample_author.get_last_first() == "Doe, John A"

    def test_get_initials(self, sample_author):
        """Test getting initials."""
        assert sample_author.get_initials() == "J. A."

    def test_author_without_middle_name(self):
        """Test author without middle name."""
        author = Author(first_name="Jane", last_name="Smith")
        assert author.get_full_name() == "Jane Smith"
        assert author.get_initials() == "J."


class TestCitation:
    """Test Citation class."""

    def test_citation_creation(self, sample_citation):
        """Test creating a citation."""
        assert sample_citation.title == "Machine Learning in Practice"
        assert len(sample_citation.authors) == 2
        assert sample_citation.publication_year == 2023

    def test_add_author(self, sample_citation):
        """Test adding an author."""
        new_author = Author(first_name="Alice", last_name="Brown")
        sample_citation.add_author(new_author)

        assert len(sample_citation.authors) == 3
        assert sample_citation.authors[2] == new_author

    def test_get_author_names(self, sample_citation):
        """Test getting author names."""
        names = sample_citation.get_author_names()

        assert len(names) == 2
        assert "John Doe" in names
        assert "Jane Smith" in names

    def test_has_doi(self, sample_citation):
        """Test DOI check."""
        assert sample_citation.has_doi() is True

        citation_no_doi = Citation(title="Test")
        assert citation_no_doi.has_doi() is False

    def test_has_url(self, sample_website_citation):
        """Test URL check."""
        assert sample_website_citation.has_url() is True

        citation_no_url = Citation(title="Test")
        assert citation_no_url.has_url() is False

    def test_to_dict(self, sample_citation):
        """Test converting citation to dictionary."""
        citation_dict = sample_citation.to_dict()

        assert citation_dict["title"] == "Machine Learning in Practice"
        assert citation_dict["source_type"] == "journal_article"
        assert len(citation_dict["authors"]) == 2
        assert citation_dict["publication_year"] == 2023


class TestInlineCitation:
    """Test InlineCitation class."""

    def test_inline_citation_creation(self, sample_citation):
        """Test creating inline citation."""
        inline = InlineCitation(
            citation_id=sample_citation.citation_id,
            citation_number=1,
        )

        assert inline.citation_number == 1
        assert inline.exact_quote is False

    def test_format_apa_inline(self, sample_citation):
        """Test APA inline citation formatting."""
        inline = InlineCitation(
            citation_id=sample_citation.citation_id,
            citation_number=1,
        )

        authors = [a.last_name for a in sample_citation.authors]
        formatted = inline.format_inline(
            CitationStyle.APA,
            authors,
            sample_citation.publication_year,
        )

        assert "Doe" in formatted
        assert "Smith" in formatted
        assert "2023" in formatted

    def test_format_mla_inline(self, sample_citation):
        """Test MLA inline citation formatting."""
        inline = InlineCitation(
            citation_id=sample_citation.citation_id,
            citation_number=1,
            page_numbers="125",
        )

        authors = [a.last_name for a in sample_citation.authors]
        formatted = inline.format_inline(
            CitationStyle.MLA,
            authors,
            sample_citation.publication_year,
        )

        assert "Doe" in formatted
        assert "125" in formatted

    def test_format_ieee_inline(self, sample_citation):
        """Test IEEE inline citation formatting."""
        inline = InlineCitation(
            citation_id=sample_citation.citation_id,
            citation_number=5,
        )

        formatted = inline.format_inline(
            CitationStyle.IEEE,
            [],
            None,
        )

        assert formatted == "[5]"


class TestBibliography:
    """Test Bibliography class."""

    def test_bibliography_creation(self):
        """Test creating a bibliography."""
        bib = Bibliography(style=CitationStyle.APA)

        assert bib.style == CitationStyle.APA
        assert bib.get_citation_count() == 0

    def test_add_citation(self, sample_citation):
        """Test adding a citation."""
        bib = Bibliography()
        bib.add_citation(sample_citation)

        assert bib.get_citation_count() == 1

    def test_remove_citation(self, sample_citation):
        """Test removing a citation."""
        bib = Bibliography()
        bib.add_citation(sample_citation)

        result = bib.remove_citation(sample_citation.citation_id)

        assert result is True
        assert bib.get_citation_count() == 0

    def test_get_citation(self, sample_citation):
        """Test retrieving a citation."""
        bib = Bibliography()
        bib.add_citation(sample_citation)

        retrieved = bib.get_citation(sample_citation.citation_id)

        assert retrieved is not None
        assert retrieved.title == sample_citation.title

    def test_sort_citations(self, sample_authors):
        """Test sorting citations."""
        bib = Bibliography()

        # Add citations in non-alphabetical order
        bib.add_citation(Citation(
            title="Z Paper",
            authors=[sample_authors[2]],  # Johnson
        ))
        bib.add_citation(Citation(
            title="A Paper",
            authors=[sample_authors[0]],  # Doe
        ))

        bib.sort_citations()

        # Should be sorted by author last name
        assert bib.citations[0].authors[0].last_name == "Doe"
        assert bib.citations[1].authors[0].last_name == "Johnson"

    def test_filter_by_type(self, sample_citation, sample_book_citation):
        """Test filtering citations by type."""
        bib = Bibliography()
        bib.add_citation(sample_citation)
        bib.add_citation(sample_book_citation)

        journal_articles = bib.filter_by_type(SourceType.JOURNAL_ARTICLE)
        books = bib.filter_by_type(SourceType.BOOK)

        assert len(journal_articles) == 1
        assert len(books) == 1

    def test_get_title_by_style(self):
        """Test getting bibliography title based on style."""
        bib_apa = Bibliography(style=CitationStyle.APA)
        assert bib_apa.get_title_by_style() == "References"

        bib_mla = Bibliography(style=CitationStyle.MLA)
        assert bib_mla.get_title_by_style() == "Works Cited"

        bib_chicago = Bibliography(style=CitationStyle.CHICAGO)
        assert bib_chicago.get_title_by_style() == "Bibliography"


class TestAPAFormatter:
    """Test APA formatter."""

    def test_format_journal_article(self, sample_citation):
        """Test formatting journal article in APA."""
        formatter = APAFormatter()
        formatted = formatter.format_citation(sample_citation)

        assert "Doe, J., & Smith, J." in formatted
        assert "(2023)" in formatted
        assert "Machine Learning in Practice" in formatted
        assert "*Journal of AI Research*" in formatted
        assert "45" in formatted
        assert "10.1234/jair.2023.123" in formatted

    def test_format_book(self, sample_book_citation):
        """Test formatting book in APA."""
        formatter = APAFormatter()
        formatted = formatter.format_citation(sample_book_citation)

        assert "Doe, J." in formatted
        assert "(2022)" in formatted
        assert "*Introduction to Artificial Intelligence*" in formatted
        assert "MIT Press" in formatted

    def test_get_style_name(self):
        """Test getting formatter style name."""
        formatter = APAFormatter()
        assert formatter.get_style_name() == "APA"


class TestMLAFormatter:
    """Test MLA formatter."""

    def test_format_journal_article(self, sample_citation):
        """Test formatting journal article in MLA."""
        formatter = MLAFormatter()
        formatted = formatter.format_citation(sample_citation)

        assert "Doe, John, et al." in formatted
        assert '"Machine Learning in Practice."' in formatted
        assert "*Journal of AI Research*" in formatted
        assert "2023" in formatted

    def test_get_style_name(self):
        """Test getting formatter style name."""
        formatter = MLAFormatter()
        assert formatter.get_style_name() == "MLA"


class TestChicagoFormatter:
    """Test Chicago formatter."""

    def test_format_book(self, sample_book_citation):
        """Test formatting book in Chicago style."""
        formatter = ChicagoFormatter()
        formatted = formatter.format_citation(sample_book_citation)

        assert "Doe, John." in formatted
        assert "*Introduction to Artificial Intelligence*" in formatted
        assert "MIT Press" in formatted
        assert "2022" in formatted

    def test_get_style_name(self):
        """Test getting formatter style name."""
        formatter = ChicagoFormatter()
        assert formatter.get_style_name() == "Chicago"


class TestIEEEFormatter:
    """Test IEEE formatter."""

    def test_format_journal_article(self, sample_citation):
        """Test formatting journal article in IEEE."""
        formatter = IEEEFormatter()
        formatted = formatter.format_citation(sample_citation)

        assert "J. Doe and J. Smith" in formatted
        assert '"Machine Learning in Practice,"' in formatted
        assert "*Journal of AI Research*" in formatted
        assert "vol. 45" in formatted

    def test_format_bibliography_entry_with_number(self, sample_citation):
        """Test formatting numbered bibliography entry."""
        formatter = IEEEFormatter()
        formatted = formatter.format_bibliography_entry(sample_citation, 5)

        assert formatted.startswith("[5]")

    def test_get_style_name(self):
        """Test getting formatter style name."""
        formatter = IEEEFormatter()
        assert formatter.get_style_name() == "IEEE"


class TestCitationFormatterFactory:
    """Test CitationFormatterFactory."""

    def test_create_apa_formatter(self):
        """Test creating APA formatter."""
        formatter = CitationFormatterFactory.create_formatter(CitationStyle.APA)
        assert isinstance(formatter, APAFormatter)

    def test_create_mla_formatter(self):
        """Test creating MLA formatter."""
        formatter = CitationFormatterFactory.create_formatter(CitationStyle.MLA)
        assert isinstance(formatter, MLAFormatter)

    def test_create_chicago_formatter(self):
        """Test creating Chicago formatter."""
        formatter = CitationFormatterFactory.create_formatter(CitationStyle.CHICAGO)
        assert isinstance(formatter, ChicagoFormatter)

    def test_create_ieee_formatter(self):
        """Test creating IEEE formatter."""
        formatter = CitationFormatterFactory.create_formatter(CitationStyle.IEEE)
        assert isinstance(formatter, IEEEFormatter)

    def test_get_supported_styles(self):
        """Test getting supported styles."""
        styles = CitationFormatterFactory.get_supported_styles()

        assert CitationStyle.APA in styles
        assert CitationStyle.MLA in styles
        assert CitationStyle.CHICAGO in styles
        assert CitationStyle.IEEE in styles


class TestBibliographyBuilder:
    """Test BibliographyBuilder."""

    def test_builder_initialization(self):
        """Test initializing bibliography builder."""
        builder = BibliographyBuilder(style=CitationStyle.APA)

        assert builder.bibliography.style == CitationStyle.APA
        assert builder.bibliography.get_citation_count() == 0

    def test_add_citation(self, sample_citation):
        """Test adding citation to builder."""
        builder = BibliographyBuilder()
        citation_id = builder.add_citation(sample_citation)

        assert citation_id == sample_citation.citation_id
        assert builder.bibliography.get_citation_count() == 1

    def test_add_from_knowledge_source(self):
        """Test adding citation from KnowledgeSource."""
        builder = BibliographyBuilder()

        source = KnowledgeSource(
            source_name="Wikipedia",
            source_type=ResearchSourceType.WEB,
            url="https://wikipedia.org",
            metadata={
                "title": "Machine Learning",
                "authors": ["John Doe"],
                "year": 2023,
            },
        )

        citation_id = builder.add_from_knowledge_source(source)

        assert builder.bibliography.get_citation_count() == 1

        # Adding same source again should return same ID
        citation_id2 = builder.add_from_knowledge_source(source)
        assert citation_id == citation_id2
        assert builder.bibliography.get_citation_count() == 1

    def test_create_inline_citation(self, sample_citation):
        """Test creating inline citation."""
        builder = BibliographyBuilder()
        builder.add_citation(sample_citation)

        inline = builder.create_inline_citation(sample_citation.citation_id)

        assert inline is not None
        assert inline.citation_number == 1

    def test_format_inline_citation(self, sample_citation):
        """Test formatting inline citation."""
        builder = BibliographyBuilder(style=CitationStyle.APA)
        builder.add_citation(sample_citation)

        formatted = builder.format_inline_citation(sample_citation.citation_id)

        assert "Doe" in formatted
        assert "2023" in formatted

    def test_generate_bibliography(self, sample_citation, sample_book_citation):
        """Test generating formatted bibliography."""
        builder = BibliographyBuilder(style=CitationStyle.APA)
        builder.add_citation(sample_citation)
        builder.add_citation(sample_book_citation)

        bibliography_text = builder.generate_bibliography(sort=True)

        assert "# References" in bibliography_text
        assert "Machine Learning in Practice" in bibliography_text
        assert "Introduction to Artificial Intelligence" in bibliography_text

    def test_get_unused_citations(self, sample_citation):
        """Test getting unused citations."""
        builder = BibliographyBuilder()
        builder.add_citation(sample_citation)

        unused = builder.get_unused_citations()

        # Should be unused since we haven't created inline citations
        assert len(unused) == 1

        # Create inline citation (marks as used)
        builder.create_inline_citation(sample_citation.citation_id)

        unused = builder.get_unused_citations()
        assert len(unused) == 0

    def test_remove_unused_citations(self, sample_citation, sample_book_citation):
        """Test removing unused citations."""
        builder = BibliographyBuilder()
        builder.add_citation(sample_citation)
        builder.add_citation(sample_book_citation)

        # Use only the first citation
        builder.create_inline_citation(sample_citation.citation_id)

        # Remove unused
        removed = builder.remove_unused_citations()

        assert removed == 1
        assert builder.bibliography.get_citation_count() == 1

    def test_get_statistics(self, sample_citation, sample_book_citation):
        """Test getting bibliography statistics."""
        builder = BibliographyBuilder()
        builder.add_citation(sample_citation)
        builder.add_citation(sample_book_citation)

        # Use one citation
        builder.create_inline_citation(sample_citation.citation_id)

        stats = builder.get_statistics()

        assert stats["total_citations"] == 2
        assert stats["used_citations"] == 1
        assert stats["unused_citations"] == 1
        assert "citations_by_type" in stats

    def test_change_style(self, sample_citation):
        """Test changing citation style."""
        builder = BibliographyBuilder(style=CitationStyle.APA)
        builder.add_citation(sample_citation)

        # Change to MLA
        builder.change_style(CitationStyle.MLA)

        assert builder.bibliography.style == CitationStyle.MLA
        assert isinstance(builder.formatter, MLAFormatter)
