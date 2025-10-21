"""Quality assessment orchestrator."""

import logging
from typing import Optional

from src.domain.models.report import DomainReport
from src.domain.quality.citation_checker import CitationQualityChecker
from src.domain.quality.content_checker import ContentQualityChecker
from src.domain.quality.models import QualityAssessment, QualityDimension
from src.domain.quality.readability_analyzer import ReadabilityAnalyzer
from src.domain.quality.structure_checker import StructureQualityChecker

logger = logging.getLogger(__name__)


class QualityAssessor:
    """Orchestrate comprehensive quality assessment.

    Coordinates multiple quality checkers to produce
    a complete quality assessment report.

    Features:
    - Multi-dimensional quality analysis
    - Automated issue detection
    - Quality scoring
    - Recommendations generation
    """

    def __init__(
        self,
        content_checker: Optional[ContentQualityChecker] = None,
        citation_checker: Optional[CitationQualityChecker] = None,
        structure_checker: Optional[StructureQualityChecker] = None,
        readability_analyzer: Optional[ReadabilityAnalyzer] = None,
        overall_threshold: float = 75.0,
    ):
        """Initialize quality assessor.

        Args:
            content_checker: Content quality checker
            citation_checker: Citation quality checker
            structure_checker: Structure quality checker
            readability_analyzer: Readability analyzer
            overall_threshold: Overall quality threshold
        """
        self.content_checker = content_checker or ContentQualityChecker()
        self.citation_checker = citation_checker or CitationQualityChecker()
        self.structure_checker = structure_checker or StructureQualityChecker()
        self.readability_analyzer = readability_analyzer or ReadabilityAnalyzer()
        self.overall_threshold = overall_threshold

        logger.info("Quality assessor initialized")

    async def assess(self, report: DomainReport) -> QualityAssessment:
        """Perform comprehensive quality assessment.

        Args:
            report: Report to assess

        Returns:
            Quality assessment result
        """
        logger.info(f"Starting quality assessment for report {report.report_id}")

        assessment = QualityAssessment(
            report_id=report.report_id,
            threshold=self.overall_threshold,
        )

        # Run all quality checks
        # Content quality
        content_score = self.content_checker.check(report)
        assessment.add_dimension_score(content_score)

        # Citation quality
        citation_score = self.citation_checker.check(report)
        assessment.add_dimension_score(citation_score)

        # Structure quality
        structure_score = self.structure_checker.check(report)
        assessment.add_dimension_score(structure_score)

        # Readability
        readability_score = self.readability_analyzer.check(report)
        assessment.add_dimension_score(readability_score)

        # Calculate overall score
        assessment.calculate_overall_score()

        # Generate recommendations
        self._generate_recommendations(assessment)

        # Log results
        logger.info(
            f"Quality assessment complete: {assessment.overall_score:.2f}/100 "
            f"({assessment.overall_level.value}), "
            f"{assessment.total_issues} issues found"
        )

        return assessment

    def _generate_recommendations(self, assessment: QualityAssessment) -> None:
        """Generate improvement recommendations.

        Args:
            assessment: Quality assessment
        """
        recommendations = []

        # Check each dimension
        for dimension, dim_score in assessment.dimension_scores.items():
            if not dim_score.passed:
                # Generate dimension-specific recommendations
                if dimension == QualityDimension.CONTENT:
                    recommendations.append(
                        f"Improve content quality (currently {dim_score.score:.1f}/100). "
                        "Add more detailed information to sections."
                    )

                elif dimension == QualityDimension.CITATIONS:
                    recommendations.append(
                        f"Improve citation quality (currently {dim_score.score:.1f}/100). "
                        "Add more citations from diverse sources."
                    )

                elif dimension == QualityDimension.STRUCTURE:
                    recommendations.append(
                        f"Improve structure quality (currently {dim_score.score:.1f}/100). "
                        "Review section organization and hierarchy."
                    )

                elif dimension == QualityDimension.READABILITY:
                    recommendations.append(
                        f"Improve readability (currently {dim_score.score:.1f}/100). "
                        "Simplify complex sentences and use clearer language."
                    )

        # Priority recommendations based on critical issues
        if assessment.critical_issues > 0:
            recommendations.insert(
                0,
                f"CRITICAL: Address {assessment.critical_issues} critical issues immediately."
            )

        # Check overall score
        if assessment.overall_score < 60:
            recommendations.insert(
                0,
                "Overall quality is inadequate. Comprehensive revision recommended."
            )
        elif assessment.overall_score < 75:
            recommendations.insert(
                0,
                "Overall quality is fair. Focus on improving low-scoring dimensions."
            )

        # Add all recommendations
        for rec in recommendations:
            assessment.add_recommendation(rec)

    def get_dimension_summary(self, assessment: QualityAssessment) -> str:
        """Get formatted dimension summary.

        Args:
            assessment: Quality assessment

        Returns:
            Formatted summary
        """
        lines = [
            f"Overall Score: {assessment.overall_score:.2f}/100 ({assessment.overall_level.value})",
            f"Pass Status: {'PASS' if assessment.passed else 'FAIL'}",
            f"Total Issues: {assessment.total_issues} ({assessment.critical_issues} critical)",
            "",
            "Dimension Scores:",
        ]

        for dimension, dim_score in assessment.dimension_scores.items():
            status = "✓" if dim_score.passed else "✗"
            lines.append(
                f"  {status} {dimension.value.capitalize()}: "
                f"{dim_score.score:.2f}/100 ({dim_score.level.value}) "
                f"- {len(dim_score.issues)} issues"
            )

        return "\n".join(lines)

    def get_issue_summary(self, assessment: QualityAssessment) -> str:
        """Get formatted issue summary.

        Args:
            assessment: Quality assessment

        Returns:
            Formatted summary
        """
        lines = ["Quality Issues:"]

        # Group by severity
        all_issues = assessment.get_all_issues()

        if not all_issues:
            lines.append("  No issues found")
            return "\n".join(lines)

        # Sort by severity
        sorted_issues = sorted(
            all_issues,
            key=lambda x: x.get_severity_score(),
            reverse=True,
        )

        # Display top 10 issues
        for i, issue in enumerate(sorted_issues[:10], 1):
            lines.append(
                f"  {i}. [{issue.severity.value.upper()}] {issue.title}"
            )
            lines.append(f"     {issue.description}")
            if issue.location:
                lines.append(f"     Location: {issue.location}")
            if issue.recommendation:
                lines.append(f"     Fix: {issue.recommendation}")
            lines.append("")

        if len(sorted_issues) > 10:
            lines.append(f"  ... and {len(sorted_issues) - 10} more issues")

        return "\n".join(lines)

    def get_recommendations_summary(self, assessment: QualityAssessment) -> str:
        """Get formatted recommendations.

        Args:
            assessment: Quality assessment

        Returns:
            Formatted recommendations
        """
        lines = ["Recommendations:"]

        if not assessment.recommendations:
            lines.append("  No specific recommendations")
            return "\n".join(lines)

        for i, rec in enumerate(assessment.recommendations, 1):
            lines.append(f"  {i}. {rec}")

        return "\n".join(lines)


def create_default_quality_assessor() -> QualityAssessor:
    """Create quality assessor with default settings.

    Returns:
        Configured quality assessor
    """
    return QualityAssessor(
        content_checker=ContentQualityChecker(
            min_section_content_items=1,
            min_content_length=100,
            min_depth_score=60.0,
        ),
        citation_checker=CitationQualityChecker(
            min_citations_per_section=2,
            min_source_diversity=0.5,
        ),
        structure_checker=StructureQualityChecker(
            max_hierarchy_depth=4,
            min_sections=3,
            max_sections=50,
        ),
        readability_analyzer=ReadabilityAnalyzer(
            target_reading_level=12.0,
            max_sentence_length=25,
        ),
        overall_threshold=75.0,
    )
