"""Unit tests for quality assessment."""

from uuid import uuid4

import pytest

from src.domain.models.report import DomainReport, ReportSection, ReportType
from src.domain.quality.assessor import QualityAssessor, create_default_quality_assessor
from src.domain.quality.citation_checker import CitationQualityChecker
from src.domain.quality.content_checker import ContentQualityChecker
from src.domain.quality.models import (
    DimensionScore,
    IssueSeverity,
    QualityAssessment,
    QualityDimension,
    QualityIssue,
    QualityLevel,
    QualityMetric,
    ReadabilityMetrics,
)
from src.domain.quality.readability_analyzer import ReadabilityAnalyzer
from src.domain.quality.structure_checker import StructureQualityChecker


@pytest.fixture
def sample_report():
    """Create sample report for testing."""
    report = DomainReport(
        report_id=uuid4(),
        report_title="Test Report on AI",
        report_type=ReportType.COMPREHENSIVE,
    )

    # Add sections with content
    section1 = ReportSection(
        section_number="1",
        section_title="Introduction",
        hierarchy_level=0,
        mapped_class_uri="http://example.org/intro",
    )
    section1.add_content({
        "type": "text",
        "text": "This is a comprehensive introduction to artificial intelligence. "
                "AI has revolutionized many fields including healthcare, finance, and education. "
                "Machine learning algorithms enable computers to learn from data without explicit programming.",
    })
    section1.metadata["citation_ids"] = ["cite1", "cite2"]
    report.add_section(section1)

    section2 = ReportSection(
        section_number="2",
        section_title="Machine Learning",
        hierarchy_level=0,
        mapped_class_uri="http://example.org/ml",
    )
    section2.add_content({
        "type": "text",
        "text": "Machine learning is a subset of AI that focuses on enabling systems to learn. "
                "Supervised learning uses labeled data for training models. "
                "Unsupervised learning discovers patterns in unlabeled data.",
    })
    section2.metadata["citation_ids"] = ["cite3"]
    report.add_section(section2)

    section2_1 = ReportSection(
        section_number="2.1",
        section_title="Deep Learning",
        hierarchy_level=1,
        mapped_class_uri="http://example.org/dl",
    )
    section2_1.add_content({
        "type": "text",
        "text": "Deep learning uses neural networks with multiple layers. "
                "Convolutional neural networks excel at image processing tasks.",
    })
    section2_1.metadata["citation_ids"] = ["cite4", "cite5"]
    report.add_section(section2_1)

    # Add bibliography metadata
    report.metadata["bibliography"] = {
        "total_citations": 5,
        "used_citations": 5,
        "unused_citations": 0,
        "citations_by_type": {
            "web": 2,
            "academic": 2,
            "wikidata": 1,
        },
    }

    report.quality_score = 95.0
    report.completeness_score = 98.0

    return report


@pytest.fixture
def minimal_report():
    """Create minimal report with issues."""
    report = DomainReport(
        report_title="Minimal Report",
        report_type=ReportType.COMPREHENSIVE,
    )

    section = ReportSection(
        section_number="1",
        section_title="Only Section",
        hierarchy_level=0,
        mapped_class_uri="test",
    )
    section.add_content({"type": "text", "text": "Short"})
    report.add_section(section)

    return report


class TestQualityModels:
    """Test quality domain models."""

    def test_quality_metric_creation(self):
        """Test creating quality metric."""
        metric = QualityMetric(
            name="Test Metric",
            dimension=QualityDimension.CONTENT,
            score=85.0,
            weight=1.5,
            threshold=70.0,
        )

        assert metric.score == 85.0
        assert metric.is_passing()
        assert metric.get_level() == QualityLevel.GOOD

    def test_quality_metric_levels(self):
        """Test quality level classification."""
        assert QualityMetric(score=95).get_level() == QualityLevel.EXCELLENT
        assert QualityMetric(score=80).get_level() == QualityLevel.GOOD
        assert QualityMetric(score=65).get_level() == QualityLevel.FAIR
        assert QualityMetric(score=45).get_level() == QualityLevel.POOR
        assert QualityMetric(score=25).get_level() == QualityLevel.INADEQUATE

    def test_quality_issue_creation(self):
        """Test creating quality issue."""
        issue = QualityIssue(
            severity=IssueSeverity.HIGH,
            dimension=QualityDimension.CONTENT,
            title="Test Issue",
            description="Issue description",
            location="Section 1",
            recommendation="Fix suggestion",
        )

        assert issue.severity == IssueSeverity.HIGH
        assert issue.get_severity_score() == 4

    def test_dimension_score_calculation(self):
        """Test dimension score calculation."""
        dim_score = DimensionScore(
            dimension=QualityDimension.CONTENT,
            threshold=70.0,
        )

        # Add metrics
        dim_score.add_metric(QualityMetric(score=80.0, weight=1.0))
        dim_score.add_metric(QualityMetric(score=90.0, weight=1.0))

        # Calculate
        score = dim_score.calculate_score()

        assert score == 85.0  # (80 + 90) / 2
        assert dim_score.level == QualityLevel.GOOD
        assert dim_score.passed

    def test_dimension_score_issues(self):
        """Test dimension score issue management."""
        dim_score = DimensionScore(dimension=QualityDimension.CONTENT)

        dim_score.add_issue(
            QualityIssue(severity=IssueSeverity.CRITICAL, title="Critical")
        )
        dim_score.add_issue(
            QualityIssue(severity=IssueSeverity.LOW, title="Low")
        )

        assert len(dim_score.issues) == 2
        assert len(dim_score.get_critical_issues()) == 1

        counts = dim_score.get_issue_count_by_severity()
        assert counts[IssueSeverity.CRITICAL] == 1
        assert counts[IssueSeverity.LOW] == 1

    def test_quality_assessment_calculation(self):
        """Test overall quality assessment calculation."""
        assessment = QualityAssessment(threshold=75.0)

        # Add dimension scores
        content_score = DimensionScore(dimension=QualityDimension.CONTENT)
        content_score.add_metric(QualityMetric(score=85.0))
        content_score.calculate_score()

        structure_score = DimensionScore(dimension=QualityDimension.STRUCTURE)
        structure_score.add_metric(QualityMetric(score=90.0))
        structure_score.calculate_score()

        assessment.add_dimension_score(content_score)
        assessment.add_dimension_score(structure_score)

        # Calculate overall
        overall = assessment.calculate_overall_score()

        assert overall > 0
        assert assessment.passed
        assert assessment.total_issues == 0

    def test_readability_metrics(self):
        """Test readability metrics."""
        metrics = ReadabilityMetrics(
            flesch_reading_ease=65.0,
            flesch_kincaid_grade=10.5,
        )

        assert metrics.get_overall_readability_score() == 65.0
        assert metrics.get_reading_level() == "High School"


class TestContentQualityChecker:
    """Test content quality checker."""

    def test_check_completeness(self, sample_report):
        """Test content completeness check."""
        checker = ContentQualityChecker()
        dim_score = checker.check(sample_report)

        assert dim_score.dimension == QualityDimension.CONTENT
        assert dim_score.score > 0

        # Should have completeness metric
        metrics = [m for m in dim_score.metrics if m.name == "Content Completeness"]
        assert len(metrics) == 1

    def test_detect_empty_sections(self, minimal_report):
        """Test detection of empty sections."""
        # Add empty section
        empty_section = ReportSection(
            section_number="2",
            section_title="Empty",
            hierarchy_level=0,
            mapped_class_uri="test2",
        )
        minimal_report.add_section(empty_section)

        checker = ContentQualityChecker()
        dim_score = checker.check(minimal_report)

        # Should have issue for empty section
        empty_issues = [i for i in dim_score.issues if "Empty Section" in i.title]
        assert len(empty_issues) == 1

    def test_detect_shallow_content(self, minimal_report):
        """Test detection of shallow content."""
        checker = ContentQualityChecker(min_content_length=100)
        dim_score = checker.check(minimal_report)

        # Should have issue for shallow content
        shallow_issues = [i for i in dim_score.issues if "Shallow" in i.title]
        assert len(shallow_issues) >= 1


class TestCitationQualityChecker:
    """Test citation quality checker."""

    def test_check_citation_coverage(self, sample_report):
        """Test citation coverage check."""
        checker = CitationQualityChecker()
        dim_score = checker.check(sample_report)

        assert dim_score.dimension == QualityDimension.CITATIONS
        assert dim_score.score > 0

        # Should have coverage metric
        metrics = [m for m in dim_score.metrics if m.name == "Citation Coverage"]
        assert len(metrics) == 1

    def test_detect_missing_citations(self, minimal_report):
        """Test detection of missing citations."""
        checker = CitationQualityChecker()
        dim_score = checker.check(minimal_report)

        # Should have issue for missing citations
        missing_issues = [i for i in dim_score.issues if "Missing Citations" in i.title]
        assert len(missing_issues) >= 1

    def test_detect_low_diversity(self):
        """Test detection of low source diversity."""
        report = DomainReport(
            report_title="Test",
            report_type=ReportType.COMPREHENSIVE,
        )

        # Add bibliography with low diversity
        report.metadata["bibliography"] = {
            "total_citations": 5,
            "used_citations": 5,
            "unused_citations": 0,
            "citations_by_type": {
                "web": 5,  # All same type
            },
        }

        section = ReportSection(
            section_number="1",
            section_title="Test",
            hierarchy_level=0,
            mapped_class_uri="test",
        )
        section.add_content({"type": "text", "text": "Content"})
        section.metadata["citation_ids"] = ["cite1"]
        report.add_section(section)

        checker = CitationQualityChecker()
        dim_score = checker.check(report)

        # Should have issue for low diversity
        diversity_issues = [i for i in dim_score.issues if "Diversity" in i.title]
        assert len(diversity_issues) >= 1


class TestStructureQualityChecker:
    """Test structure quality checker."""

    def test_check_organization(self, sample_report):
        """Test organizational structure check."""
        checker = StructureQualityChecker()
        dim_score = checker.check(sample_report)

        assert dim_score.dimension == QualityDimension.STRUCTURE
        assert dim_score.score > 0

    def test_detect_excessive_depth(self):
        """Test detection of excessive hierarchy depth."""
        report = DomainReport(
            report_title="Deep Report",
            report_type=ReportType.COMPREHENSIVE,
        )

        # Create deeply nested sections
        for i in range(6):
            section = ReportSection(
                section_number=f"{'1.' * (i + 1)}",
                section_title=f"Level {i}",
                hierarchy_level=i,
                mapped_class_uri=f"test{i}",
            )
            section.add_content({"type": "text", "text": "Content"})
            report.add_section(section)

        checker = StructureQualityChecker(max_hierarchy_depth=4)
        dim_score = checker.check(report)

        # Should have issue for excessive depth
        depth_issues = [i for i in dim_score.issues if "Hierarchy Depth" in i.title]
        assert len(depth_issues) >= 1

    def test_detect_too_few_sections(self):
        """Test detection of too few sections."""
        report = DomainReport(
            report_title="Tiny Report",
            report_type=ReportType.COMPREHENSIVE,
        )

        section = ReportSection(
            section_number="1",
            section_title="Only Section",
            hierarchy_level=0,
            mapped_class_uri="test",
        )
        section.add_content({"type": "text", "text": "Content"})
        report.add_section(section)

        checker = StructureQualityChecker(min_sections=3)
        dim_score = checker.check(report)

        # Should have issue for too few sections
        count_issues = [i for i in dim_score.issues if "Too Few" in i.title]
        assert len(count_issues) >= 1


class TestReadabilityAnalyzer:
    """Test readability analyzer."""

    def test_analyze_readability(self, sample_report):
        """Test readability analysis."""
        analyzer = ReadabilityAnalyzer()
        dim_score = analyzer.check(sample_report)

        assert dim_score.dimension == QualityDimension.READABILITY
        assert dim_score.score >= 0

        # Should have readability metrics
        reading_ease = [m for m in dim_score.metrics if m.name == "Reading Ease"]
        assert len(reading_ease) == 1

        grade_level = [m for m in dim_score.metrics if m.name == "Grade Level"]
        assert len(grade_level) == 1

    def test_calculate_flesch_reading_ease(self):
        """Test Flesch Reading Ease calculation."""
        analyzer = ReadabilityAnalyzer()

        # Create report with simple text
        report = DomainReport(
            report_title="Simple Report",
            report_type=ReportType.COMPREHENSIVE,
        )

        section = ReportSection(
            section_number="1",
            section_title="Test",
            hierarchy_level=0,
            mapped_class_uri="test",
        )
        section.add_content({
            "type": "text",
            "text": "This is a simple sentence. It is easy to read. "
                    "Short words help. Clear writing matters.",
        })
        report.add_section(section)

        dim_score = analyzer.check(report)

        # Simple text should have higher reading ease
        reading_ease_metric = [m for m in dim_score.metrics if m.name == "Reading Ease"][0]
        assert reading_ease_metric.score > 50

    def test_detect_long_sentences(self):
        """Test detection of long sentences."""
        analyzer = ReadabilityAnalyzer(max_sentence_length=15)

        report = DomainReport(
            report_title="Complex Report",
            report_type=ReportType.COMPREHENSIVE,
        )

        section = ReportSection(
            section_number="1",
            section_title="Test",
            hierarchy_level=0,
            mapped_class_uri="test",
        )
        section.add_content({
            "type": "text",
            "text": "This is an extremely long sentence that contains many words and clauses "
                    "and keeps going on and on without stopping and makes it difficult to read "
                    "and understand the main point being communicated to the reader.",
        })
        report.add_section(section)

        dim_score = analyzer.check(report)

        # Should have issue for long sentences
        long_sentence_issues = [i for i in dim_score.issues if "Long Sentences" in i.title]
        assert len(long_sentence_issues) >= 1


class TestQualityAssessor:
    """Test quality assessor."""

    @pytest.mark.asyncio
    async def test_comprehensive_assessment(self, sample_report):
        """Test comprehensive quality assessment."""
        assessor = create_default_quality_assessor()

        assessment = await assessor.assess(sample_report)

        assert assessment.overall_score > 0
        assert assessment.overall_score <= 100
        assert len(assessment.dimension_scores) >= 4

        # Should have all dimensions
        assert QualityDimension.CONTENT in assessment.dimension_scores
        assert QualityDimension.CITATIONS in assessment.dimension_scores
        assert QualityDimension.STRUCTURE in assessment.dimension_scores
        assert QualityDimension.READABILITY in assessment.dimension_scores

    @pytest.mark.asyncio
    async def test_assessment_with_issues(self, minimal_report):
        """Test assessment of report with issues."""
        assessor = create_default_quality_assessor()

        assessment = await assessor.assess(minimal_report)

        # Should have lower score and issues
        assert assessment.overall_score < 90
        assert assessment.total_issues > 0

    @pytest.mark.asyncio
    async def test_recommendations_generation(self, minimal_report):
        """Test recommendations generation."""
        assessor = create_default_quality_assessor()

        assessment = await assessor.assess(minimal_report)

        # Should have recommendations
        assert len(assessment.recommendations) > 0

    def test_dimension_summary(self, sample_report):
        """Test dimension summary generation."""
        assessor = create_default_quality_assessor()

        # Create simple assessment
        assessment = QualityAssessment(report_id=sample_report.report_id)
        content_score = DimensionScore(dimension=QualityDimension.CONTENT)
        content_score.add_metric(QualityMetric(score=85.0))
        content_score.calculate_score()
        assessment.add_dimension_score(content_score)
        assessment.calculate_overall_score()

        summary = assessor.get_dimension_summary(assessment)

        assert "Overall Score" in summary
        assert "content" in summary.lower()

    def test_issue_summary(self):
        """Test issue summary generation."""
        assessor = create_default_quality_assessor()

        assessment = QualityAssessment()
        dim_score = DimensionScore(dimension=QualityDimension.CONTENT)
        dim_score.add_issue(
            QualityIssue(
                severity=IssueSeverity.HIGH,
                title="Test Issue",
                description="Issue description",
            )
        )
        assessment.add_dimension_score(dim_score)

        summary = assessor.get_issue_summary(assessment)

        assert "Test Issue" in summary

    @pytest.mark.asyncio
    async def test_assessment_summary(self, sample_report):
        """Test assessment summary conversion."""
        assessor = create_default_quality_assessor()

        assessment = await assessor.assess(sample_report)
        summary = assessment.to_summary()

        assert "overall_score" in summary
        assert "overall_level" in summary
        assert "passed" in summary
        assert "dimensions" in summary
        assert isinstance(summary["dimensions"], dict)


class TestQualityEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_report_assessment(self):
        """Test assessment of empty report."""
        report = DomainReport(
            report_title="Empty Report",
            report_type=ReportType.COMPREHENSIVE,
        )

        assessor = create_default_quality_assessor()
        assessment = await assessor.assess(report)

        # Should complete without errors
        assert assessment.overall_score >= 0

    def test_metric_without_threshold(self):
        """Test metric that doesn't meet threshold."""
        metric = QualityMetric(score=50.0, threshold=70.0)

        assert not metric.is_passing()
        assert metric.get_level() == QualityLevel.FAIR

    def test_dimension_score_no_metrics(self):
        """Test dimension score with no metrics."""
        dim_score = DimensionScore(dimension=QualityDimension.CONTENT)

        score = dim_score.calculate_score()

        assert score == 0.0
        assert not dim_score.passed
