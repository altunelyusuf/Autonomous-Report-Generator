"""Structure extractor for mapping ontology to report structure."""

import logging
from typing import Dict, List, Optional
from uuid import uuid4

from src.domain.models.report import DomainReport, ReportSection, ReportType, SectionStatus
from src.domain.ontology.models import ClassHierarchy, OntologyClass, OntologyStructure
from src.domain.structure.numbering import SectionNumberGenerator

logger = logging.getLogger(__name__)


class StructureExtractor:
    """Extract report structure from ontology structure.

    Maps ontology class hierarchy to report section hierarchy,
    creating a navigable document structure.

    Features:
    - Maps each ontology class to a report section
    - Preserves hierarchy relationships
    - Generates section numbers
    - Configurable max depth
    - Handles multiple root classes
    """

    def __init__(
        self,
        max_depth: int = 5,
        include_deprecated: bool = False,
        numbering_generator: Optional[SectionNumberGenerator] = None,
    ):
        """Initialize structure extractor.

        Args:
            max_depth: Maximum hierarchy depth to extract (default: 5)
            include_deprecated: Whether to include deprecated classes (default: False)
            numbering_generator: Optional custom numbering generator
        """
        self.max_depth = max_depth
        self.include_deprecated = include_deprecated
        self.numbering_generator = numbering_generator or SectionNumberGenerator()

        # Mapping cache
        self._class_to_section: Dict[str, ReportSection] = {}

    def extract_structure(
        self,
        ontology_structure: OntologyStructure,
        report_type: ReportType = ReportType.COMPREHENSIVE,
    ) -> DomainReport:
        """Extract report structure from ontology.

        Process:
        1. Create report instance
        2. Map root classes to top-level sections
        3. Recursively map child classes to subsections
        4. Generate section numbers
        5. Calculate statistics

        Args:
            ontology_structure: Analyzed ontology structure
            report_type: Type of report to generate

        Returns:
            DomainReport with complete section structure
        """
        logger.info("Extracting report structure from ontology")

        # Clear cache
        self._class_to_section = {}

        # Create report
        report = DomainReport(
            report_id=uuid4(),
            report_title=self._generate_report_title(ontology_structure),
            report_description=ontology_structure.metadata.description,
            source_ontology_uri=ontology_structure.uri,
            report_type=report_type,
        )

        # Map classes to sections
        sections = self._map_classes_to_sections(
            ontology_structure.hierarchy, ontology_structure.classes
        )

        # Add sections to report
        for section in sections:
            report.add_section(section)

        # Generate section numbers
        self._generate_section_numbers(report)

        # Calculate statistics
        report.section_count = len(report.get_all_sections())

        logger.info(
            f"Structure extraction complete: {report.section_count} sections created"
        )

        return report

    def _generate_report_title(self, ontology_structure: OntologyStructure) -> str:
        """Generate report title from ontology metadata.

        Args:
            ontology_structure: Ontology structure

        Returns:
            Report title
        """
        if ontology_structure.metadata.title:
            return f"{ontology_structure.metadata.title} - Domain Report"
        return "Ontology Domain Report"

    def _map_classes_to_sections(
        self, hierarchy: ClassHierarchy, all_classes: List[OntologyClass]
    ) -> List[ReportSection]:
        """Map ontology classes to report sections.

        Args:
            hierarchy: Class hierarchy
            all_classes: All ontology classes

        Returns:
            List of top-level sections
        """
        sections = []

        # Process each root class
        for i, root_class in enumerate(hierarchy.roots):
            # Skip deprecated if configured
            if not self.include_deprecated and root_class.deprecated:
                logger.debug(f"Skipping deprecated class: {root_class.label}")
                continue

            # Create section for root class
            section = self._create_section_from_class(root_class, level=1, order=i)
            sections.append(section)

            # Recursively process children
            self._process_children(root_class, section, current_depth=1)

        return sections

    def _create_section_from_class(
        self, ont_class: OntologyClass, level: int, order: int
    ) -> ReportSection:
        """Create a report section from an ontology class.

        Args:
            ont_class: Ontology class
            level: Hierarchy level
            order: Order index

        Returns:
            ReportSection
        """
        section = ReportSection(
            section_id=uuid4(),
            section_title=ont_class.label,
            section_description=ont_class.comment,
            hierarchy_level=level,
            order_index=order,
            mapped_class_uri=ont_class.uri,
            mapped_class_label=ont_class.label,
            status=SectionStatus.PENDING,
        )

        # Cache mapping
        self._class_to_section[ont_class.uri] = section

        logger.debug(
            f"Created section '{section.section_title}' at level {level} "
            f"(mapped to {ont_class.uri})"
        )

        return section

    def _process_children(
        self, ont_class: OntologyClass, parent_section: ReportSection, current_depth: int
    ) -> None:
        """Recursively process child classes.

        Args:
            ont_class: Parent ontology class
            parent_section: Parent report section
            current_depth: Current depth in hierarchy
        """
        # Check max depth
        if current_depth >= self.max_depth:
            logger.debug(
                f"Max depth {self.max_depth} reached, stopping at {ont_class.label}"
            )
            return

        # Process each child
        for i, child_class in enumerate(ont_class.children):
            # Skip deprecated if configured
            if not self.include_deprecated and child_class.deprecated:
                logger.debug(f"Skipping deprecated class: {child_class.label}")
                continue

            # Create subsection
            child_section = self._create_section_from_class(
                child_class, level=current_depth + 1, order=i
            )

            # Add to parent
            parent_section.add_subsection(child_section)

            # Recursively process children
            self._process_children(child_class, child_section, current_depth + 1)

    def _generate_section_numbers(self, report: DomainReport) -> None:
        """Generate section numbers for all sections.

        Args:
            report: Domain report
        """
        logger.info("Generating section numbers")

        # Reset numbering generator
        self.numbering_generator.reset()

        # Number top-level sections
        for section in report._sections:
            self._number_section_tree(section)

        logger.info("Section numbering complete")

    def _number_section_tree(self, section: ReportSection) -> None:
        """Recursively number section and subsections.

        Args:
            section: Section to number
        """
        # Get number for this section
        section.section_number = self.numbering_generator.get_next_number(
            section.hierarchy_level
        )

        # Number subsections
        for subsection in section.get_subsections():
            self._number_section_tree(subsection)

    def get_section_for_class(self, class_uri: str) -> Optional[ReportSection]:
        """Get the report section for an ontology class.

        Args:
            class_uri: Ontology class URI

        Returns:
            ReportSection or None
        """
        return self._class_to_section.get(class_uri)

    def identify_relationships(
        self, ontology_structure: OntologyStructure
    ) -> List[Dict[str, str]]:
        """Identify key relationships between concepts.

        This can be used to generate relationship diagrams or
        cross-reference sections.

        Args:
            ontology_structure: Ontology structure

        Returns:
            List of relationship dictionaries
        """
        relationships = []

        for ont_class in ontology_structure.classes:
            # Parent-child relationships
            for parent_uri in ont_class.subclass_of:
                relationships.append(
                    {
                        "type": "subClassOf",
                        "source": ont_class.uri,
                        "source_label": ont_class.label,
                        "target": parent_uri,
                        "target_label": self._get_class_label(
                            parent_uri, ontology_structure.classes
                        ),
                    }
                )

            # Equivalent relationships
            for equiv_uri in ont_class.equivalent_to:
                relationships.append(
                    {
                        "type": "equivalentTo",
                        "source": ont_class.uri,
                        "source_label": ont_class.label,
                        "target": equiv_uri,
                        "target_label": self._get_class_label(
                            equiv_uri, ontology_structure.classes
                        ),
                    }
                )

            # Disjoint relationships
            for disj_uri in ont_class.disjoint_with:
                relationships.append(
                    {
                        "type": "disjointWith",
                        "source": ont_class.uri,
                        "source_label": ont_class.label,
                        "target": disj_uri,
                        "target_label": self._get_class_label(
                            disj_uri, ontology_structure.classes
                        ),
                    }
                )

        logger.info(f"Identified {len(relationships)} relationships")
        return relationships

    def _get_class_label(self, class_uri: str, all_classes: List[OntologyClass]) -> str:
        """Get label for a class URI.

        Args:
            class_uri: Class URI
            all_classes: All classes

        Returns:
            Class label or URI
        """
        for cls in all_classes:
            if cls.uri == class_uri:
                return cls.label
        return class_uri

    def get_extraction_statistics(self, report: DomainReport) -> Dict[str, int]:
        """Get statistics about the extraction.

        Args:
            report: Generated report

        Returns:
            Statistics dictionary
        """
        all_sections = report.get_all_sections()

        stats = {
            "total_sections": len(all_sections),
            "top_level_sections": len(report._sections),
            "max_depth": max((s.hierarchy_level for s in all_sections), default=0),
            "sections_by_level": {},
        }

        # Count sections by level
        for level in range(1, stats["max_depth"] + 1):
            sections_at_level = report.get_sections_by_level(level)
            stats["sections_by_level"][level] = len(sections_at_level)

        return stats
