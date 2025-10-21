"""Unit tests for structure extraction (Sprint 2)."""

import pytest

from src.domain.models.report import ReportType, SectionStatus
from src.domain.ontology.models import (
    ClassHierarchy,
    OntologyClass,
    OntologyFormat,
    OntologyMetadata,
    OntologyStatistics,
    OntologyStructure,
)
from src.domain.structure.extractor import StructureExtractor
from src.domain.structure.numbering import SectionNumberGenerator


@pytest.fixture
def sample_ontology_structure():
    """Create a sample ontology structure for testing."""
    # Create some sample classes
    root_class = OntologyClass(
        uri="http://example.org/Wine",
        label="Wine",
        comment="A wine is an alcoholic beverage",
    )

    red_wine = OntologyClass(
        uri="http://example.org/RedWine",
        label="Red Wine",
        comment="Wine made from red grapes",
        subclass_of=["http://example.org/Wine"],
    )

    white_wine = OntologyClass(
        uri="http://example.org/WhiteWine",
        label="White Wine",
        comment="Wine made from white grapes",
        subclass_of=["http://example.org/Wine"],
    )

    cabernet = OntologyClass(
        uri="http://example.org/Cabernet",
        label="Cabernet Sauvignon",
        comment="A type of red wine",
        subclass_of=["http://example.org/RedWine"],
    )

    chardonnay = OntologyClass(
        uri="http://example.org/Chardonnay",
        label="Chardonnay",
        comment="A type of white wine",
        subclass_of=["http://example.org/WhiteWine"],
    )

    # Build hierarchy
    root_class.add_child(red_wine)
    root_class.add_child(white_wine)
    red_wine.add_parent(root_class)
    white_wine.add_parent(root_class)

    red_wine.add_child(cabernet)
    cabernet.add_parent(red_wine)

    white_wine.add_child(chardonnay)
    chardonnay.add_parent(white_wine)

    # Set depths
    root_class.depth = 0
    red_wine.depth = 1
    white_wine.depth = 1
    cabernet.depth = 2
    chardonnay.depth = 2

    # Create hierarchy
    hierarchy = ClassHierarchy(roots=[root_class])
    hierarchy.max_depth = 2
    hierarchy.total_classes = 5

    # Create metadata
    metadata = OntologyMetadata(
        title="Wine Ontology",
        description="An ontology about wines",
        creator=["Wine Expert"],
    )

    # Create statistics
    statistics = OntologyStatistics(
        class_count=5,
        max_hierarchy_depth=2,
    )

    # Create structure
    structure = OntologyStructure(
        uri="http://example.org/wine",
        format=OntologyFormat.OWL,
        metadata=metadata,
        classes=[root_class, red_wine, white_wine, cabernet, chardonnay],
        hierarchy=hierarchy,
        statistics=statistics,
    )

    return structure


class TestSectionNumberGenerator:
    """Test section number generation."""

    def test_basic_numbering(self):
        """Test basic section numbering."""
        generator = SectionNumberGenerator()

        # Level 1 sections
        assert generator.get_next_number(1) == "1"
        assert generator.get_next_number(1) == "2"
        assert generator.get_next_number(1) == "3"

    def test_nested_numbering(self):
        """Test nested section numbering."""
        generator = SectionNumberGenerator()

        # 1
        assert generator.get_next_number(1) == "1"

        # 1.1, 1.2
        assert generator.get_next_number(2) == "1.1"
        assert generator.get_next_number(2) == "1.2"

        # 1.2.1
        assert generator.get_next_number(3) == "1.2.1"

        # 2
        assert generator.get_next_number(1) == "2"

        # 2.1
        assert generator.get_next_number(2) == "2.1"

    def test_reset(self):
        """Test resetting numbering."""
        generator = SectionNumberGenerator()

        generator.get_next_number(1)
        generator.get_next_number(1)

        generator.reset()

        assert generator.get_next_number(1) == "1"

    def test_parent_number(self):
        """Test getting parent section number."""
        generator = SectionNumberGenerator()

        assert generator.get_parent_number("1.2.3") == "1.2"
        assert generator.get_parent_number("1.2") == "1"
        assert generator.get_parent_number("1") == ""

    def test_level_from_number(self):
        """Test getting level from section number."""
        generator = SectionNumberGenerator()

        assert generator.get_level_from_number("1") == 1
        assert generator.get_level_from_number("1.2") == 2
        assert generator.get_level_from_number("1.2.3") == 3

    def test_subsection_check(self):
        """Test subsection relationship."""
        generator = SectionNumberGenerator()

        assert generator.is_subsection_of("1.1", "1") is True
        assert generator.is_subsection_of("1.1.1", "1.1") is True
        assert generator.is_subsection_of("1.1.1", "1") is False  # Not direct
        assert generator.is_subsection_of("2.1", "1") is False

    def test_descendant_check(self):
        """Test descendant relationship."""
        generator = SectionNumberGenerator()

        assert generator.is_descendant_of("1.1", "1") is True
        assert generator.is_descendant_of("1.1.1", "1") is True
        assert generator.is_descendant_of("1.1.1", "1.1") is True
        assert generator.is_descendant_of("2.1", "1") is False

    def test_section_comparison(self):
        """Test section number comparison."""
        generator = SectionNumberGenerator()

        assert generator.compare_sections("1", "2") == -1
        assert generator.compare_sections("2", "1") == 1
        assert generator.compare_sections("1", "1") == 0
        assert generator.compare_sections("1.1", "1.2") == -1
        assert generator.compare_sections("1.10", "1.2") == 1

    def test_sort_sections(self):
        """Test sorting section numbers."""
        generator = SectionNumberGenerator()

        sections = ["1.10", "1.2", "2", "1", "1.1"]
        sorted_sections = generator.sort_section_numbers(sections)

        assert sorted_sections == ["1", "1.1", "1.2", "1.10", "2"]


class TestStructureExtractor:
    """Test structure extraction."""

    def test_extract_basic_structure(self, sample_ontology_structure):
        """Test extracting basic report structure."""
        extractor = StructureExtractor(max_depth=5)

        report = extractor.extract_structure(sample_ontology_structure)

        # Check report created
        assert report is not None
        assert report.report_title == "Wine Ontology - Domain Report"
        assert report.source_ontology_uri == "http://example.org/wine"

        # Check sections created
        assert len(report._sections) == 1  # One root class
        root_section = report._sections[0]
        assert root_section.section_title == "Wine"
        assert root_section.section_number == "1"
        assert root_section.hierarchy_level == 1

    def test_section_hierarchy(self, sample_ontology_structure):
        """Test section hierarchy is correct."""
        extractor = StructureExtractor(max_depth=5)

        report = extractor.extract_structure(sample_ontology_structure)

        # Get root section
        root_section = report._sections[0]

        # Check subsections
        subsections = root_section.get_subsections()
        assert len(subsections) == 2  # Red and White wine

        # Check subsection titles
        subsection_titles = {s.section_title for s in subsections}
        assert "Red Wine" in subsection_titles
        assert "White Wine" in subsection_titles

        # Check numbering
        for subsection in subsections:
            assert subsection.section_number in ["1.1", "1.2"]
            assert subsection.hierarchy_level == 2

    def test_deep_hierarchy(self, sample_ontology_structure):
        """Test deep hierarchy extraction."""
        extractor = StructureExtractor(max_depth=5)

        report = extractor.extract_structure(sample_ontology_structure)

        # Find Red Wine section
        root_section = report._sections[0]
        red_wine_section = None
        for subsection in root_section.get_subsections():
            if subsection.section_title == "Red Wine":
                red_wine_section = subsection
                break

        assert red_wine_section is not None

        # Check it has Cabernet subsection
        cabernet_sections = red_wine_section.get_subsections()
        assert len(cabernet_sections) == 1
        assert cabernet_sections[0].section_title == "Cabernet Sauvignon"
        assert cabernet_sections[0].hierarchy_level == 3

    def test_max_depth_limit(self, sample_ontology_structure):
        """Test max depth limiting."""
        extractor = StructureExtractor(max_depth=2)

        report = extractor.extract_structure(sample_ontology_structure)

        # Get all sections
        all_sections = report.get_all_sections()

        # Check no sections beyond depth 2
        for section in all_sections:
            assert section.hierarchy_level <= 2

    def test_class_to_section_mapping(self, sample_ontology_structure):
        """Test class to section mapping."""
        extractor = StructureExtractor(max_depth=5)

        report = extractor.extract_structure(sample_ontology_structure)

        # Check mapping exists
        wine_section = extractor.get_section_for_class("http://example.org/Wine")
        assert wine_section is not None
        assert wine_section.section_title == "Wine"

        red_wine_section = extractor.get_section_for_class("http://example.org/RedWine")
        assert red_wine_section is not None
        assert red_wine_section.section_title == "Red Wine"

    def test_section_count(self, sample_ontology_structure):
        """Test section count calculation."""
        extractor = StructureExtractor(max_depth=5)

        report = extractor.extract_structure(sample_ontology_structure)

        # Should have 5 sections (all 5 classes)
        assert report.section_count == 5

    def test_statistics(self, sample_ontology_structure):
        """Test extraction statistics."""
        extractor = StructureExtractor(max_depth=5)

        report = extractor.extract_structure(sample_ontology_structure)

        stats = extractor.get_extraction_statistics(report)

        assert stats["total_sections"] == 5
        assert stats["top_level_sections"] == 1
        assert stats["max_depth"] == 3
        assert stats["sections_by_level"][1] == 1
        assert stats["sections_by_level"][2] == 2
        assert stats["sections_by_level"][3] == 2


class TestReportModels:
    """Test report domain models."""

    def test_report_creation(self):
        """Test creating a report."""
        from src.domain.models.report import DomainReport

        report = DomainReport(
            report_title="Test Report",
            source_ontology_uri="http://example.org/test",
        )

        assert report.report_title == "Test Report"
        assert report.source_ontology_uri == "http://example.org/test"
        assert report.status.value == "created"

    def test_section_creation(self):
        """Test creating a section."""
        from src.domain.models.report import ReportSection

        section = ReportSection(
            section_title="Introduction",
            mapped_class_uri="http://example.org/Intro",
            hierarchy_level=1,
        )

        assert section.section_title == "Introduction"
        assert section.hierarchy_level == 1
        assert section.status == SectionStatus.PENDING

    def test_subsection_management(self):
        """Test managing subsections."""
        from src.domain.models.report import ReportSection

        parent = ReportSection(
            section_title="Parent",
            mapped_class_uri="http://example.org/Parent",
            hierarchy_level=1,
        )

        child = ReportSection(
            section_title="Child",
            mapped_class_uri="http://example.org/Child",
            hierarchy_level=2,
        )

        parent.add_subsection(child)

        assert len(parent.get_subsections()) == 1
        assert child.parent_section_id == parent.section_id
        assert child.hierarchy_level == 2

    def test_completeness_calculation(self):
        """Test completeness calculation."""
        from src.domain.models.report import ReportSection

        section = ReportSection(
            section_title="Test Section",
            section_description="Test description",
            mapped_class_uri="http://example.org/Test",
            hierarchy_level=1,
        )

        # Empty section
        completeness = section.calculate_completeness()
        assert completeness < 100.0

        # Add content (mocked)
        section._content = ["Some content"]
        section.content_count = 1

        completeness = section.calculate_completeness()
        assert completeness > 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
