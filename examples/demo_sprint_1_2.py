"""Demonstration of Sprint 1 + Sprint 2: End-to-end structure extraction.

This script demonstrates:
1. Parsing an ontology (Sprint 1)
2. Extracting report structure (Sprint 2)
"""

import logging
from pathlib import Path

from src.domain.ontology.analyzer import OntologyAnalyzer
from src.domain.structure.extractor import StructureExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def print_section_tree(section, indent=0):
    """Print section hierarchy tree.

    Args:
        section: Report section
        indent: Current indentation level
    """
    prefix = "  " * indent
    print(f"{prefix}{section.section_number} {section.section_title}")
    print(f"{prefix}   Mapped to: {section.mapped_class_label}")
    print(f"{prefix}   Level: {section.hierarchy_level}, Status: {section.status.value}")

    if section.section_description:
        desc = section.section_description[:100] + "..." if len(section.section_description) > 100 else section.section_description
        print(f"{prefix}   Description: {desc}")

    print()

    # Print subsections
    for subsection in section.get_subsections():
        print_section_tree(subsection, indent + 1)


def demo_structure_extraction():
    """Demonstrate complete structure extraction pipeline."""
    print("=" * 80)
    print("SPRINT 1 + 2 DEMONSTRATION: Ontology to Report Structure")
    print("=" * 80)
    print()

    # Step 1: Create a simple in-memory ontology for demonstration
    # In real use, you would load from a file
    print("Step 1: Creating sample ontology...")
    print("-" * 80)

    from src.domain.ontology.models import (
        ClassHierarchy,
        OntologyClass,
        OntologyFormat,
        OntologyMetadata,
        OntologyStatistics,
        OntologyStructure,
    )

    # Create sample classes
    root_class = OntologyClass(
        uri="http://example.org/Wine",
        label="Wine",
        comment="An alcoholic beverage made from fermented grapes or other fruits",
    )

    red_wine = OntologyClass(
        uri="http://example.org/RedWine",
        label="Red Wine",
        comment="Wine made from dark-colored grape varieties",
        subclass_of=["http://example.org/Wine"],
    )

    white_wine = OntologyClass(
        uri="http://example.org/WhiteWine",
        label="White Wine",
        comment="Wine made from white or green grapes",
        subclass_of=["http://example.org/Wine"],
    )

    cabernet = OntologyClass(
        uri="http://example.org/CabernetSauvignon",
        label="Cabernet Sauvignon",
        comment="A red wine variety known for its boldness and tannins",
        subclass_of=["http://example.org/RedWine"],
    )

    merlot = OntologyClass(
        uri="http://example.org/Merlot",
        label="Merlot",
        comment="A red wine variety known for its softness and fruitiness",
        subclass_of=["http://example.org/RedWine"],
    )

    chardonnay = OntologyClass(
        uri="http://example.org/Chardonnay",
        label="Chardonnay",
        comment="A white wine variety with a wide range of styles",
        subclass_of=["http://example.org/WhiteWine"],
    )

    sauvignon_blanc = OntologyClass(
        uri="http://example.org/SauvignonBlanc",
        label="Sauvignon Blanc",
        comment="A white wine variety known for its crisp, refreshing character",
        subclass_of=["http://example.org/WhiteWine"],
    )

    # Build hierarchy relationships
    root_class.add_child(red_wine)
    root_class.add_child(white_wine)
    red_wine.add_parent(root_class)
    white_wine.add_parent(root_class)

    red_wine.add_child(cabernet)
    red_wine.add_child(merlot)
    cabernet.add_parent(red_wine)
    merlot.add_parent(red_wine)

    white_wine.add_child(chardonnay)
    white_wine.add_child(sauvignon_blanc)
    chardonnay.add_parent(white_wine)
    sauvignon_blanc.add_parent(white_wine)

    # Set depths
    root_class.depth = 0
    red_wine.depth = 1
    white_wine.depth = 1
    cabernet.depth = 2
    merlot.depth = 2
    chardonnay.depth = 2
    sauvignon_blanc.depth = 2

    # Create hierarchy
    hierarchy = ClassHierarchy(roots=[root_class])
    hierarchy.max_depth = 2
    hierarchy.total_classes = 7

    # Create metadata
    metadata = OntologyMetadata(
        title="Wine Ontology",
        description="A comprehensive ontology describing wines, their varieties, and characteristics",
        creator=["Wine Domain Expert", "Ontology Engineer"],
        version_info="1.0.0",
    )

    # Create statistics
    statistics = OntologyStatistics(
        class_count=7,
        max_hierarchy_depth=2,
        avg_children_per_class=2.0,
    )

    # Create complete ontology structure
    ontology_structure = OntologyStructure(
        uri="http://example.org/wine-ontology",
        format=OntologyFormat.OWL,
        metadata=metadata,
        classes=[root_class, red_wine, white_wine, cabernet, merlot, chardonnay, sauvignon_blanc],
        hierarchy=hierarchy,
        statistics=statistics,
    )

    print(f"✓ Created sample ontology: {metadata.title}")
    print(f"  URI: {ontology_structure.uri}")
    print(f"  Classes: {statistics.class_count}")
    print(f"  Max Depth: {hierarchy.max_depth}")
    print()

    # Step 2: Extract report structure
    print("Step 2: Extracting report structure...")
    print("-" * 80)

    extractor = StructureExtractor(max_depth=5)
    report = extractor.extract_structure(ontology_structure)

    print(f"✓ Report structure extracted: {report.report_title}")
    print(f"  Total sections: {report.section_count}")
    print(f"  Report type: {report.report_type.value}")
    print(f"  Status: {report.status.value}")
    print()

    # Step 3: Display structure
    print("Step 3: Report Structure Tree")
    print("-" * 80)
    print()

    for section in report._sections:
        print_section_tree(section)

    # Step 4: Show statistics
    print("Step 4: Extraction Statistics")
    print("-" * 80)

    stats = extractor.get_extraction_statistics(report)
    print(f"Total sections: {stats['total_sections']}")
    print(f"Top-level sections: {stats['top_level_sections']}")
    print(f"Max depth: {stats['max_depth']}")
    print()
    print("Sections by level:")
    for level, count in stats['sections_by_level'].items():
        print(f"  Level {level}: {count} sections")
    print()

    # Step 5: Show section details
    print("Step 5: Detailed Section Information")
    print("-" * 80)

    all_sections = report.get_all_sections()
    print(f"\nAll {len(all_sections)} sections in order:")
    for section in all_sections:
        print(f"  {section.section_number:6s} | Level {section.hierarchy_level} | {section.section_title}")
        print(f"         | Mapped to: {section.mapped_class_uri}")
    print()

    # Step 6: Demonstrate section queries
    print("Step 6: Section Queries")
    print("-" * 80)

    # Get sections at level 2
    level_2_sections = report.get_sections_by_level(2)
    print(f"\nSections at level 2: {len(level_2_sections)}")
    for section in level_2_sections:
        print(f"  {section.section_number} {section.section_title}")

    # Find section by class URI
    cabernet_section = extractor.get_section_for_class("http://example.org/CabernetSauvignon")
    if cabernet_section:
        print(f"\nFound section for Cabernet Sauvignon:")
        print(f"  Number: {cabernet_section.section_number}")
        print(f"  Title: {cabernet_section.section_title}")
        print(f"  Level: {cabernet_section.hierarchy_level}")

    print()
    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("Next Steps:")
    print("  - Sprint 3: Research Services (gather information for each section)")
    print("  - Sprint 4: Research Aggregation (combine multi-source data)")
    print("  - Sprint 5: LLM Content Generation (generate narrative content)")
    print()


if __name__ == "__main__":
    demo_structure_extraction()
