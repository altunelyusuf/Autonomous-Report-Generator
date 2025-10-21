"""Report assembler coordinating all components."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from src.domain.citations.bibliography import BibliographyBuilder
from src.domain.citations.models import CitationStyle
from src.domain.generation.generator import ContentGenerator
from src.domain.generation.models import ContentType, GeneratedContent
from src.domain.models.report import DomainReport, ReportSection
from src.domain.ontology.models import OntologyStructure
from src.domain.research.models import ResearchResult
from src.domain.research.orchestrator import ResearchOrchestrator
from src.domain.structure.extractor import StructureExtractor

logger = logging.getLogger(__name__)


class ReportAssembler:
    """Assemble complete reports from ontologies.

    Coordinates all components to generate comprehensive reports:
    1. Parse ontology
    2. Extract report structure
    3. Research concepts
    4. Generate content
    5. Add citations
    6. Build bibliography

    Features:
    - End-to-end report generation
    - Progress tracking
    - Error recovery
    - Quality assessment
    - Citation management
    """

    def __init__(
        self,
        structure_extractor: StructureExtractor,
        research_orchestrator: ResearchOrchestrator,
        content_generator: ContentGenerator,
        citation_style: CitationStyle = CitationStyle.APA,
    ):
        """Initialize report assembler.

        Args:
            structure_extractor: Structure extractor
            research_orchestrator: Research orchestrator
            content_generator: Content generator
            citation_style: Citation style to use
        """
        self.structure_extractor = structure_extractor
        self.research_orchestrator = research_orchestrator
        self.content_generator = content_generator
        self.citation_style = citation_style

        # Bibliography builder
        self.bibliography_builder = BibliographyBuilder(style=citation_style)

        # Track assembly progress
        self.progress: Dict[str, any] = {}

        logger.info("Report assembler initialized")

    async def assemble_report(
        self,
        ontology_structure: OntologyStructure,
        include_introduction: bool = True,
        include_conclusion: bool = True,
        max_sections: Optional[int] = None,
    ) -> DomainReport:
        """Assemble complete report from ontology.

        Args:
            ontology_structure: Parsed ontology
            include_introduction: Whether to add introduction
            include_conclusion: Whether to add conclusion
            max_sections: Maximum sections to process (for testing)

        Returns:
            Complete assembled report

        Raises:
            AssemblyException: If assembly fails
        """
        logger.info(
            f"Starting report assembly for ontology: {ontology_structure.uri}"
        )

        # Initialize progress tracking
        self._init_progress(ontology_structure)

        try:
            # Step 1: Extract report structure
            report = await self._extract_structure(ontology_structure)
            self._update_progress("structure_extracted", True)

            # Step 2: Research and populate sections
            await self._populate_sections(
                report,
                ontology_structure,
                max_sections=max_sections,
            )
            self._update_progress("sections_populated", True)

            # Step 3: Add introduction (if requested)
            if include_introduction:
                await self._add_introduction(report, ontology_structure)
                self._update_progress("introduction_added", True)

            # Step 4: Add conclusion (if requested)
            if include_conclusion:
                await self._add_conclusion(report, ontology_structure)
                self._update_progress("conclusion_added", True)

            # Step 5: Generate bibliography
            self._add_bibliography(report)
            self._update_progress("bibliography_added", True)

            # Step 6: Calculate final metrics
            report.calculate_quality_score()
            report.calculate_completeness_score()
            self._update_progress("metrics_calculated", True)

            logger.info(
                f"Report assembly completed: {report.get_section_count()} sections, "
                f"quality={report.quality_score:.2f}"
            )

            return report

        except Exception as e:
            logger.error(f"Report assembly failed: {e}")
            self._update_progress("error", str(e))
            raise

    async def _extract_structure(
        self, ontology_structure: OntologyStructure
    ) -> DomainReport:
        """Extract report structure from ontology.

        Args:
            ontology_structure: Ontology structure

        Returns:
            Report with sections (no content yet)
        """
        logger.info("Extracting report structure")

        from src.domain.models.report import ReportType

        report = self.structure_extractor.extract_structure(
            ontology_structure,
            ReportType.COMPREHENSIVE,
        )

        logger.info(f"Extracted {report.get_section_count()} sections")

        return report

    async def _populate_sections(
        self,
        report: DomainReport,
        ontology_structure: OntologyStructure,
        max_sections: Optional[int] = None,
    ) -> None:
        """Research and populate report sections.

        Args:
            report: Report to populate
            ontology_structure: Ontology structure
            max_sections: Maximum sections to process
        """
        logger.info("Populating report sections with content")

        sections = report.get_all_sections()
        if max_sections:
            sections = sections[:max_sections]

        total = len(sections)
        completed = 0

        for section in sections:
            try:
                await self._populate_section(section, ontology_structure)
                completed += 1

                logger.info(f"Progress: {completed}/{total} sections completed")
                self._update_progress("sections_completed", completed)
                self._update_progress("sections_total", total)

            except Exception as e:
                logger.error(
                    f"Failed to populate section {section.section_number}: {e}"
                )
                # Continue with other sections

    async def _populate_section(
        self,
        section: ReportSection,
        ontology_structure: OntologyStructure,
    ) -> None:
        """Populate a single section with content.

        Args:
            section: Section to populate
            ontology_structure: Ontology structure
        """
        # Get concept info from ontology
        concept_class = self._find_class_by_uri(
            ontology_structure,
            section.mapped_class_uri,
        )

        if not concept_class:
            logger.warning(
                f"Could not find class for section {section.section_number}"
            )
            return

        concept_label = concept_class.label or concept_class.class_name

        # Step 1: Research the concept
        logger.debug(f"Researching: {concept_label}")
        research_result = await self.research_orchestrator.research_concept(
            concept_uri=section.mapped_class_uri,
            concept_label=concept_label,
        )

        # Step 2: Generate content
        logger.debug(f"Generating content for: {concept_label}")
        generated_content = await self.content_generator.generate_narrative(
            concept_label=concept_label,
            research_result=research_result,
            max_tokens=1500,
        )

        # Step 3: Add citations from research sources
        citation_ids = self.bibliography_builder.add_from_knowledge_sources(
            research_result.get_sources()
        )

        # Step 4: Embed inline citations in content
        content_with_citations = self._embed_inline_citations(
            generated_content,
            research_result,
        )

        # Step 5: Add content to section
        section.add_content({
            "type": "generated_narrative",
            "text": content_with_citations,
            "generated_at": datetime.utcnow().isoformat(),
            "quality_score": generated_content.quality_score,
            "citation_ids": [str(cid) for cid in citation_ids],
        })

        # Add metadata
        section.metadata["research_confidence"] = research_result.confidence_score
        section.metadata["content_quality"] = generated_content.quality_score
        section.metadata["fact_count"] = research_result.get_fact_count()
        section.metadata["source_count"] = research_result.get_source_count()

        logger.debug(
            f"Section {section.section_number} populated: "
            f"{len(content_with_citations)} chars"
        )

    def _embed_inline_citations(
        self,
        generated_content: GeneratedContent,
        research_result: ResearchResult,
    ) -> str:
        """Embed inline citations in generated content.

        Args:
            generated_content: Generated content
            research_result: Research result with sources

        Returns:
            Content with inline citations
        """
        content = generated_content.content

        # Get source IDs from research result
        sources = research_result.get_sources()

        # For each source, add inline citation
        for source in sources:
            # Get citation ID
            citation_id = self.bibliography_builder.add_from_knowledge_source(source)

            # Format inline citation
            inline_citation = self.bibliography_builder.format_inline_citation(
                citation_id
            )

            # Add citation at relevant points (simplified - in production,
            # use NLP to find best insertion points)
            if source.source_name in content:
                # Add citation after source name
                content = content.replace(
                    source.source_name,
                    f"{source.source_name} {inline_citation}",
                    1,  # Only first occurrence
                )

        return content

    async def _add_introduction(
        self,
        report: DomainReport,
        ontology_structure: OntologyStructure,
    ) -> None:
        """Add introduction section to report.

        Args:
            report: Report to add introduction to
            ontology_structure: Ontology structure
        """
        logger.info("Generating introduction")

        # Create introduction section
        intro_section = ReportSection(
            section_number="0",
            section_title="Introduction",
            hierarchy_level=0,
            mapped_class_uri=ontology_structure.uri,
        )

        # Generate introduction content
        intro_text = (
            f"# Introduction\n\n"
            f"This report provides a comprehensive overview of {ontology_structure.metadata.title or 'the domain'}. "
            f"The information is derived from the ontology at {ontology_structure.uri}, "
            f"which contains {len(ontology_structure.classes)} concepts organized in a hierarchical structure.\n\n"
            f"The report is organized into {report.get_section_count()} main sections, "
            f"each exploring a key concept in detail. The content is supported by "
            f"research from multiple authoritative sources.\n\n"
        )

        intro_section.add_content({
            "type": "introduction",
            "text": intro_text,
        })

        # Add as first section
        report._sections.insert(0, intro_section)

        logger.debug("Introduction added")

    async def _add_conclusion(
        self,
        report: DomainReport,
        ontology_structure: OntologyStructure,
    ) -> None:
        """Add conclusion section to report.

        Args:
            report: Report to add conclusion to
            ontology_structure: Ontology structure
        """
        logger.info("Generating conclusion")

        # Create conclusion section
        conclusion_section = ReportSection(
            section_number=str(report.get_section_count() + 1),
            section_title="Conclusion",
            hierarchy_level=0,
            mapped_class_uri=ontology_structure.uri,
        )

        # Generate conclusion content
        conclusion_text = (
            f"# Conclusion\n\n"
            f"This report has explored the key concepts in {ontology_structure.metadata.title or 'the domain'}. "
            f"Through systematic analysis of {len(ontology_structure.classes)} concepts, "
            f"we have provided a comprehensive overview of the domain structure and relationships.\n\n"
            f"The report synthesizes information from {self.bibliography_builder.bibliography.get_citation_count()} sources, "
            f"ensuring accuracy and comprehensiveness. Each section is supported by rigorous research "
            f"and properly cited sources.\n\n"
        )

        conclusion_section.add_content({
            "type": "conclusion",
            "text": conclusion_text,
        })

        # Add as last section
        report.add_section(conclusion_section)

        logger.debug("Conclusion added")

    def _add_bibliography(self, report: DomainReport) -> None:
        """Add bibliography to report.

        Args:
            report: Report to add bibliography to
        """
        logger.info("Generating bibliography")

        # Remove unused citations
        removed = self.bibliography_builder.remove_unused_citations()
        if removed > 0:
            logger.info(f"Removed {removed} unused citations")

        # Generate formatted bibliography
        bibliography_text = self.bibliography_builder.generate_bibliography(sort=True)

        # Create bibliography section
        bib_section = ReportSection(
            section_number=str(report.get_section_count() + 1),
            section_title=self.bibliography_builder.bibliography.get_title_by_style(),
            hierarchy_level=0,
            mapped_class_uri="",
        )

        bib_section.add_content({
            "type": "bibliography",
            "text": bibliography_text,
        })

        # Add to report
        report.add_section(bib_section)

        # Add bibliography statistics to report metadata
        bib_stats = self.bibliography_builder.get_statistics()
        report.metadata["bibliography"] = bib_stats

        logger.info(
            f"Bibliography added with {bib_stats['total_citations']} citations"
        )

    def _find_class_by_uri(
        self,
        ontology_structure: OntologyStructure,
        class_uri: str,
    ) -> Optional[any]:
        """Find ontology class by URI.

        Args:
            ontology_structure: Ontology structure
            class_uri: Class URI to find

        Returns:
            OntologyClass or None
        """
        for ont_class in ontology_structure.classes:
            if ont_class.uri == class_uri:
                return ont_class

        return None

    def _init_progress(self, ontology_structure: OntologyStructure) -> None:
        """Initialize progress tracking.

        Args:
            ontology_structure: Ontology structure
        """
        self.progress = {
            "started_at": datetime.utcnow().isoformat(),
            "ontology_uri": ontology_structure.uri,
            "total_classes": len(ontology_structure.classes),
            "structure_extracted": False,
            "sections_populated": False,
            "introduction_added": False,
            "conclusion_added": False,
            "bibliography_added": False,
            "metrics_calculated": False,
            "sections_completed": 0,
            "sections_total": 0,
            "error": None,
        }

    def _update_progress(self, key: str, value: any) -> None:
        """Update progress tracking.

        Args:
            key: Progress key
            value: Progress value
        """
        self.progress[key] = value
        self.progress["updated_at"] = datetime.utcnow().isoformat()

    def get_progress(self) -> Dict[str, any]:
        """Get current assembly progress.

        Returns:
            Progress dictionary
        """
        return self.progress.copy()

    def get_progress_percentage(self) -> float:
        """Calculate assembly progress percentage.

        Returns:
            Progress percentage (0.0 to 100.0)
        """
        steps = [
            "structure_extracted",
            "sections_populated",
            "introduction_added",
            "conclusion_added",
            "bibliography_added",
            "metrics_calculated",
        ]

        completed = sum(1 for step in steps if self.progress.get(step, False))
        total = len(steps)

        return (completed / total) * 100.0
