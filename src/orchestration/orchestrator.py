"""Report generation orchestrator."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from src.domain.assembly.assembler import ReportAssembler
from src.domain.citations.bibliography import BibliographyBuilder
from src.domain.citations.formatter import CitationFormatterFactory
from src.domain.generation.generator import ContentGenerator
from src.domain.generation.models import GenerationRequest
from src.domain.models.ontology import DomainOntology
from src.domain.models.report import DomainReport
from src.domain.ontology.parser import OntologyParser
from src.domain.quality.assessor import QualityAssessor, create_default_quality_assessor
from src.domain.quality.models import QualityAssessment
from src.domain.research.aggregator import ResearchAggregator
from src.domain.structure.extractor import StructureExtractor

logger = logging.getLogger(__name__)


class ReportGenerationConfig:
    """Configuration for report generation."""

    def __init__(
        self,
        query: str,
        ontology_source: Optional[str] = None,
        ontology_content: Optional[str] = None,
        max_depth: int = 3,
        research_enabled: bool = True,
        max_sources: int = 10,
        llm_provider: str = "openai",
        llm_model: Optional[str] = None,
        citation_style: str = "apa",
        include_bibliography: bool = True,
        quality_threshold: float = 75.0,
    ):
        """Initialize configuration."""
        self.query = query
        self.ontology_source = ontology_source
        self.ontology_content = ontology_content
        self.max_depth = max_depth
        self.research_enabled = research_enabled
        self.max_sources = max_sources
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.citation_style = citation_style
        self.include_bibliography = include_bibliography
        self.quality_threshold = quality_threshold


class ReportOrchestrator:
    """Orchestrate end-to-end report generation.

    Coordinates all components:
    1. Ontology parsing
    2. Structure extraction
    3. Research aggregation
    4. Content generation
    5. Citation management
    6. Report assembly
    7. Quality assessment

    Features:
    - Async workflow execution
    - Progress tracking
    - Error handling
    - Quality validation
    - Citation integration
    """

    def __init__(
        self,
        ontology_parser: Optional[OntologyParser] = None,
        structure_extractor: Optional[StructureExtractor] = None,
        research_aggregator: Optional[ResearchAggregator] = None,
        content_generator: Optional[ContentGenerator] = None,
        quality_assessor: Optional[QualityAssessor] = None,
    ):
        """Initialize orchestrator.

        Args:
            ontology_parser: Ontology parser
            structure_extractor: Structure extractor
            research_aggregator: Research aggregator
            content_generator: Content generator
            quality_assessor: Quality assessor
        """
        self.ontology_parser = ontology_parser or OntologyParser()
        self.structure_extractor = structure_extractor or StructureExtractor()
        self.research_aggregator = research_aggregator or ResearchAggregator()
        self.content_generator = content_generator
        self.quality_assessor = quality_assessor or create_default_quality_assessor()

        self._current_status = "idle"
        self._progress = 0.0

        logger.info("Report orchestrator initialized")

    async def generate_report(
        self, config: ReportGenerationConfig
    ) -> tuple[DomainReport, QualityAssessment]:
        """Generate complete report.

        Args:
            config: Generation configuration

        Returns:
            Tuple of (report, quality_assessment)

        Raises:
            Exception: If generation fails
        """
        logger.info(f"Starting report generation for query: {config.query}")

        try:
            # Step 1: Parse ontology
            self._update_status("parsing_ontology", 0.1)
            ontology = await self._parse_ontology(config)

            # Step 2: Extract structure
            self._update_status("extracting_structure", 0.2)
            structure = await self._extract_structure(ontology, config)

            # Step 3: Research (if enabled)
            research_data = None
            if config.research_enabled:
                self._update_status("researching", 0.3)
                research_data = await self._conduct_research(config)

            # Step 4: Generate content
            self._update_status("generating_content", 0.5)
            report = await self._generate_content(
                structure, research_data, ontology, config
            )

            # Step 5: Assemble report
            self._update_status("assembling", 0.7)
            report = await self._assemble_report(report, config)

            # Step 6: Assess quality
            self._update_status("assessing_quality", 0.9)
            assessment = await self._assess_quality(report, config)

            # Step 7: Complete
            self._update_status("completed", 1.0)

            logger.info(
                f"Report generation completed. Quality: {assessment.overall_score:.2f}/100"
            )

            return report, assessment

        except Exception as e:
            self._update_status("failed", 0.0)
            logger.error(f"Report generation failed: {e}")
            raise

    async def _parse_ontology(
        self, config: ReportGenerationConfig
    ) -> DomainOntology:
        """Parse ontology from source.

        Args:
            config: Configuration

        Returns:
            Parsed ontology
        """
        logger.info("Parsing ontology")

        if config.ontology_content:
            # Parse from content
            ontology = self.ontology_parser.parse_from_string(
                config.ontology_content, format="xml"
            )
        elif config.ontology_source:
            # Parse from URL/file
            ontology = self.ontology_parser.parse(config.ontology_source)
        else:
            # Create minimal ontology from query
            ontology = self._create_minimal_ontology(config.query)

        logger.info(
            f"Ontology parsed: {len(ontology.concepts)} concepts, "
            f"{len(ontology.relationships)} relationships"
        )

        return ontology

    def _create_minimal_ontology(self, query: str) -> DomainOntology:
        """Create minimal ontology from query.

        Args:
            query: Research query

        Returns:
            Minimal ontology
        """
        from src.domain.models.ontology import Concept

        ontology = DomainOntology(
            ontology_id=str(uuid4()),
            name=f"Query Ontology: {query}",
            description=f"Minimal ontology for query: {query}",
        )

        # Create root concept
        root_concept = Concept(
            concept_id=str(uuid4()),
            name=query,
            description=f"Main topic: {query}",
            category="topic",
        )
        ontology.add_concept(root_concept)

        return ontology

    async def _extract_structure(
        self, ontology: DomainOntology, config: ReportGenerationConfig
    ) -> DomainReport:
        """Extract report structure from ontology.

        Args:
            ontology: Domain ontology
            config: Configuration

        Returns:
            Report structure
        """
        logger.info("Extracting report structure")

        report = self.structure_extractor.extract_structure(
            ontology,
            max_depth=config.max_depth,
            report_title=f"Research Report: {config.query}",
        )

        logger.info(f"Structure extracted: {report.get_section_count()} sections")

        return report

    async def _conduct_research(
        self, config: ReportGenerationConfig
    ) -> dict:
        """Conduct research for query.

        Args:
            config: Configuration

        Returns:
            Research data
        """
        logger.info(f"Conducting research for: {config.query}")

        # This is a placeholder - in a real implementation,
        # this would call research services
        research_data = {
            "query": config.query,
            "sources": [],
            "max_sources": config.max_sources,
        }

        logger.info("Research completed")

        return research_data

    async def _generate_content(
        self,
        report: DomainReport,
        research_data: Optional[dict],
        ontology: DomainOntology,
        config: ReportGenerationConfig,
    ) -> DomainReport:
        """Generate content for report sections.

        Args:
            report: Report structure
            research_data: Research data
            ontology: Domain ontology
            config: Configuration

        Returns:
            Report with content
        """
        logger.info("Generating report content")

        if not self.content_generator:
            logger.warning("Content generator not configured, using placeholder content")
            # Add placeholder content
            for section in report.get_all_sections():
                section.add_content_item(
                    {
                        "type": "text",
                        "text": f"Content for section: {section.section_title}",
                    }
                )
            return report

        # Generate content for each section
        for section in report.get_all_sections():
            generation_request = GenerationRequest(
                section_title=section.section_title,
                context=research_data or {},
                max_length=1000,
            )

            # Generate content (this would be async in real implementation)
            # For now, add placeholder
            section.add_content_item(
                {
                    "type": "text",
                    "text": f"Generated content for: {section.section_title}",
                }
            )

        logger.info("Content generation completed")

        return report

    async def _assemble_report(
        self, report: DomainReport, config: ReportGenerationConfig
    ) -> DomainReport:
        """Assemble final report with citations.

        Args:
            report: Report with content
            config: Configuration

        Returns:
            Assembled report
        """
        logger.info("Assembling report")

        if config.include_bibliography:
            # Create citation formatter
            formatter_factory = CitationFormatterFactory()
            formatter = formatter_factory.create_formatter(config.citation_style)

            # Create bibliography builder
            bib_builder = BibliographyBuilder(formatter)

            # Create assembler
            assembler = ReportAssembler(bib_builder)

            # Assemble report
            report = assembler.assemble(report)

        logger.info("Report assembly completed")

        return report

    async def _assess_quality(
        self, report: DomainReport, config: ReportGenerationConfig
    ) -> QualityAssessment:
        """Assess report quality.

        Args:
            report: Generated report
            config: Configuration

        Returns:
            Quality assessment
        """
        logger.info("Assessing report quality")

        assessment = await self.quality_assessor.assess(report)

        if not assessment.passed:
            logger.warning(
                f"Report quality below threshold: {assessment.overall_score:.2f} < {config.quality_threshold}"
            )
        else:
            logger.info(
                f"Report quality acceptable: {assessment.overall_score:.2f} >= {config.quality_threshold}"
            )

        return assessment

    def _update_status(self, status: str, progress: float) -> None:
        """Update generation status.

        Args:
            status: Status message
            progress: Progress (0.0-1.0)
        """
        self._current_status = status
        self._progress = progress
        logger.debug(f"Status: {status}, Progress: {progress:.1%}")

    def get_status(self) -> dict:
        """Get current status.

        Returns:
            Status dictionary
        """
        return {
            "status": self._current_status,
            "progress": self._progress,
        }


def create_default_orchestrator() -> ReportOrchestrator:
    """Create orchestrator with default configuration.

    Returns:
        Configured orchestrator
    """
    return ReportOrchestrator(
        ontology_parser=OntologyParser(),
        structure_extractor=StructureExtractor(),
        research_aggregator=ResearchAggregator(),
        content_generator=None,  # Will use placeholder
        quality_assessor=create_default_quality_assessor(),
    )
