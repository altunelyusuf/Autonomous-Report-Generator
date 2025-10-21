"""Integration tests for end-to-end workflows."""

import pytest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.domain.models.ontology import Concept, DomainOntology, Relationship
from src.domain.models.report import DomainReport, ReportSection
from src.domain.ontology.parser import OntologyParser
from src.domain.structure.extractor import StructureExtractor
from src.domain.citations.formatter import CitationFormatterFactory
from src.domain.citations.bibliography import BibliographyBuilder
from src.domain.citations.models import Author, Citation
from src.domain.assembly.assembler import ReportAssembler
from src.domain.quality.assessor import create_default_quality_assessor
from src.domain.export.models import ExportFormat, ExportOptions
from src.infrastructure.exporters.manager import ExportManager
from src.orchestration.orchestrator import (
    ReportOrchestrator,
    ReportGenerationConfig,
    create_default_orchestrator,
)


@pytest.fixture
def sample_ontology():
    """Create sample ontology for testing."""
    ontology = DomainOntology(
        ontology_id=str(uuid4()),
        name="Machine Learning Ontology",
        description="Test ontology for ML concepts",
    )

    # Create concepts
    ml = Concept(
        concept_id=str(uuid4()),
        name="Machine Learning",
        description="Study of computer algorithms that improve through experience",
        category="field",
    )

    supervised = Concept(
        concept_id=str(uuid4()),
        name="Supervised Learning",
        description="Learning from labeled data",
        category="technique",
    )

    unsupervised = Concept(
        concept_id=str(uuid4()),
        name="Unsupervised Learning",
        description="Learning from unlabeled data",
        category="technique",
    )

    neural_networks = Concept(
        concept_id=str(uuid4()),
        name="Neural Networks",
        description="Computing systems inspired by biological neural networks",
        category="model",
    )

    # Add concepts
    ontology.add_concept(ml)
    ontology.add_concept(supervised)
    ontology.add_concept(unsupervised)
    ontology.add_concept(neural_networks)

    # Create relationships
    ontology.add_relationship(
        Relationship(
            relationship_id=str(uuid4()),
            source_concept_id=ml.concept_id,
            target_concept_id=supervised.concept_id,
            relationship_type="has_subtopic",
        )
    )

    ontology.add_relationship(
        Relationship(
            relationship_id=str(uuid4()),
            source_concept_id=ml.concept_id,
            target_concept_id=unsupervised.concept_id,
            relationship_type="has_subtopic",
        )
    )

    ontology.add_relationship(
        Relationship(
            relationship_id=str(uuid4()),
            source_concept_id=supervised.concept_id,
            target_concept_id=neural_networks.concept_id,
            relationship_type="uses",
        )
    )

    return ontology


@pytest.fixture
def sample_citations():
    """Create sample citations."""
    return [
        Citation(
            citation_id=str(uuid4()),
            title="Deep Learning Fundamentals",
            authors=[
                Author(first_name="John", last_name="Smith"),
                Author(first_name="Jane", last_name="Doe"),
            ],
            year=2020,
            publication_type="book",
            publisher="Tech Press",
        ),
        Citation(
            citation_id=str(uuid4()),
            title="Introduction to Neural Networks",
            authors=[Author(first_name="Alice", last_name="Johnson")],
            year=2019,
            publication_type="journal",
            journal="AI Review",
            volume="12",
            pages="45-67",
        ),
    ]


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""

    def test_structure_extraction_from_ontology(self, sample_ontology):
        """Test extracting report structure from ontology."""
        extractor = StructureExtractor()

        report = extractor.extract_structure(
            sample_ontology,
            max_depth=3,
            report_title="Machine Learning Overview",
        )

        # Verify report created
        assert report is not None
        assert report.report_title == "Machine Learning Overview"

        # Verify sections created
        sections = report.get_all_sections()
        assert len(sections) > 0

        # Verify hierarchy
        root_sections = [s for s in sections if s.hierarchy_level == 0]
        assert len(root_sections) > 0

    def test_citation_formatting_and_bibliography(self, sample_citations):
        """Test citation formatting and bibliography generation."""
        # Test APA formatting
        apa_formatter = CitationFormatterFactory().create_formatter("apa")
        apa_formatted = apa_formatter.format_citation(sample_citations[0])

        assert "Smith" in apa_formatted
        assert "2020" in apa_formatted

        # Test bibliography building
        bib_builder = BibliographyBuilder(apa_formatter)
        bib_builder.add_citation(sample_citations[0], ["intro", "methods"])
        bib_builder.add_citation(sample_citations[1], ["results"])

        bibliography = bib_builder.build()

        assert len(bibliography.citations) == 2
        assert bibliography.total_citations == 2

    def test_report_assembly_with_citations(self, sample_ontology, sample_citations):
        """Test complete report assembly with citations."""
        # Extract structure
        extractor = StructureExtractor()
        report = extractor.extract_structure(
            sample_ontology,
            report_title="ML Report",
        )

        # Add content to sections
        for section in report.get_all_sections()[:2]:
            section.add_content_item({
                "type": "text",
                "text": f"Content for {section.section_title}",
            })

        # Create assembler
        formatter = CitationFormatterFactory().create_formatter("apa")
        bib_builder = BibliographyBuilder(formatter)
        assembler = ReportAssembler(bib_builder)

        # Add citations
        for citation in sample_citations:
            bib_builder.add_citation(citation, ["intro"])

        # Assemble report
        assembled_report = assembler.assemble(report)

        assert assembled_report is not None
        assert assembled_report.get_section_count() > 0

    @pytest.mark.asyncio
    async def test_quality_assessment_workflow(self, sample_ontology):
        """Test quality assessment on generated report."""
        # Create report with content
        extractor = StructureExtractor()
        report = extractor.extract_structure(sample_ontology)

        # Add substantial content
        for section in report.get_all_sections():
            section.add_content_item({
                "type": "text",
                "text": "This is a comprehensive section about the topic. " * 10,
            })

        # Assess quality
        assessor = create_default_quality_assessor()
        assessment = await assessor.assess(report)

        # Verify assessment
        assert assessment is not None
        assert 0 <= assessment.overall_score <= 100
        assert len(assessment.dimension_scores) > 0
        assert assessment.total_issues >= 0

    @pytest.mark.asyncio
    async def test_export_to_multiple_formats(self, sample_ontology, tmp_path):
        """Test exporting report to multiple formats."""
        # Create report
        extractor = StructureExtractor()
        report = extractor.extract_structure(sample_ontology)

        # Add content
        for section in report.get_all_sections():
            section.add_content_item({
                "type": "text",
                "text": f"Content for {section.section_title}",
            })

        # Create export manager
        manager = ExportManager()
        options = ExportOptions(
            include_toc=True,
            include_metadata=True,
        )

        # Test Markdown export
        md_path = tmp_path / "report.md"
        md_result = await manager.export(
            report, ExportFormat.MARKDOWN, md_path, options
        )
        assert md_result.output_path is not None
        assert md_result.output_path.exists()

        # Test HTML export
        html_path = tmp_path / "report.html"
        html_result = await manager.export(
            report, ExportFormat.HTML, html_path, options
        )
        assert html_result.output_path is not None
        assert html_result.output_path.exists()

    @pytest.mark.asyncio
    async def test_full_orchestrator_workflow(self):
        """Test complete workflow through orchestrator."""
        # Create orchestrator
        orchestrator = create_default_orchestrator()

        # Create configuration
        config = ReportGenerationConfig(
            query="Machine Learning Basics",
            max_depth=2,
            research_enabled=False,  # Disable research for testing
            citation_style="apa",
            include_bibliography=True,
            quality_threshold=60.0,
        )

        # Generate report
        report, assessment = await orchestrator.generate_report(config)

        # Verify report
        assert report is not None
        assert report.get_section_count() > 0

        # Verify assessment
        assert assessment is not None
        assert assessment.overall_score >= 0


class TestComponentIntegration:
    """Test integration between components."""

    def test_ontology_to_structure_to_citations(self, sample_ontology, sample_citations):
        """Test data flow from ontology to structure to citations."""
        # Step 1: Extract structure
        extractor = StructureExtractor()
        report = extractor.extract_structure(sample_ontology)

        # Step 2: Add content
        section = report.get_all_sections()[0]
        section.add_content_item({
            "type": "text",
            "text": "Machine learning content",
        })

        # Step 3: Add citations
        formatter = CitationFormatterFactory().create_formatter("mla")
        bib_builder = BibliographyBuilder(formatter)

        for citation in sample_citations:
            bib_builder.add_citation(citation, [section.section_id])

        # Step 4: Build bibliography
        bibliography = bib_builder.build()

        assert bibliography.total_citations == len(sample_citations)

    @pytest.mark.asyncio
    async def test_quality_to_export_integration(self, sample_ontology, tmp_path):
        """Test quality assessment before export."""
        # Create report
        extractor = StructureExtractor()
        report = extractor.extract_structure(sample_ontology)

        # Add content
        for section in report.get_all_sections():
            section.add_content_item({
                "type": "text",
                "text": "Section content with sufficient length for quality analysis. " * 15,
            })

        # Assess quality
        assessor = create_default_quality_assessor()
        assessment = await assessor.assess(report)

        # Only export if quality passes
        if assessment.passed:
            manager = ExportManager()
            result = await manager.export(
                report,
                ExportFormat.HTML,
                tmp_path / "quality_report.html",
                ExportOptions(),
            )
            assert result.output_path is not None

    def test_citation_styles_consistency(self, sample_citations):
        """Test consistency across different citation styles."""
        factory = CitationFormatterFactory()

        styles = ["apa", "mla", "chicago", "ieee"]
        formatted_citations = {}

        for style in styles:
            formatter = factory.create_formatter(style)
            formatted = formatter.format_citation(sample_citations[0])
            formatted_citations[style] = formatted

            # Verify basic content
            assert "Smith" in formatted
            assert "2020" in formatted

        # Verify each style is different
        assert len(set(formatted_citations.values())) == len(styles)


class TestErrorHandling:
    """Test error handling in integrated workflows."""

    @pytest.mark.asyncio
    async def test_empty_ontology_handling(self):
        """Test handling of empty ontology."""
        ontology = DomainOntology(
            ontology_id=str(uuid4()),
            name="Empty Ontology",
            description="Test empty ontology",
        )

        extractor = StructureExtractor()
        report = extractor.extract_structure(ontology)

        # Should create report with minimal structure
        assert report is not None

    @pytest.mark.asyncio
    async def test_quality_assessment_on_empty_report(self):
        """Test quality assessment on report with no content."""
        report = DomainReport(
            report_id=uuid4(),
            report_title="Empty Report",
            created_at=datetime.utcnow(),
        )

        section = ReportSection(
            section_id=uuid4(),
            section_number="1",
            section_title="Empty Section",
            hierarchy_level=0,
        )
        report.add_section(section)

        assessor = create_default_quality_assessor()
        assessment = await assessor.assess(report)

        # Should identify quality issues
        assert assessment.total_issues > 0
        assert not assessment.passed

    @pytest.mark.asyncio
    async def test_export_nonexistent_path_handling(self, sample_ontology):
        """Test export to non-existent directory."""
        report = StructureExtractor().extract_structure(sample_ontology)

        # Add content
        for section in report.get_all_sections():
            section.add_content_item({"type": "text", "text": "Content"})

        # Export to path with non-existent parent
        manager = ExportManager()
        deep_path = Path("/tmp/deep/nested/path/report.md")

        result = await manager.export(
            report, ExportFormat.MARKDOWN, deep_path, ExportOptions()
        )

        # Should create parent directories
        assert result.output_path is not None
        assert result.output_path.exists()


class TestPerformance:
    """Basic performance tests."""

    @pytest.mark.asyncio
    async def test_large_ontology_processing(self):
        """Test processing of large ontology."""
        # Create large ontology
        ontology = DomainOntology(
            ontology_id=str(uuid4()),
            name="Large Ontology",
            description="Performance test ontology",
        )

        # Add many concepts
        concepts = []
        for i in range(100):
            concept = Concept(
                concept_id=str(uuid4()),
                name=f"Concept {i}",
                description=f"Description for concept {i}",
                category="test",
            )
            ontology.add_concept(concept)
            concepts.append(concept)

        # Add relationships
        for i in range(len(concepts) - 1):
            ontology.add_relationship(
                Relationship(
                    relationship_id=str(uuid4()),
                    source_concept_id=concepts[i].concept_id,
                    target_concept_id=concepts[i + 1].concept_id,
                    relationship_type="related_to",
                )
            )

        # Extract structure
        import time
        start = time.time()

        extractor = StructureExtractor()
        report = extractor.extract_structure(ontology, max_depth=3)

        duration = time.time() - start

        # Should complete in reasonable time
        assert duration < 5.0  # 5 seconds
        assert report.get_section_count() > 0

    @pytest.mark.asyncio
    async def test_multiple_export_formats_performance(self, sample_ontology, tmp_path):
        """Test performance of exporting to multiple formats."""
        # Create report
        report = StructureExtractor().extract_structure(sample_ontology)

        # Add content
        for section in report.get_all_sections():
            section.add_content_item({
                "type": "text",
                "text": "Content for performance test. " * 100,
            })

        import time
        manager = ExportManager()
        formats = [
            (ExportFormat.MARKDOWN, ".md"),
            (ExportFormat.HTML, ".html"),
        ]

        for format_type, ext in formats:
            start = time.time()

            result = await manager.export(
                report,
                format_type,
                tmp_path / f"perf_test{ext}",
                ExportOptions(),
            )

            duration = time.time() - start

            # Each export should complete quickly
            assert duration < 2.0  # 2 seconds
            assert result.output_path is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
