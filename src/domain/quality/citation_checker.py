"""Citation quality checker."""

import logging

from src.domain.models.report import DomainReport
from src.domain.quality.models import (
    DimensionScore,
    IssueSeverity,
    QualityDimension,
    QualityIssue,
    QualityMetric,
)

logger = logging.getLogger(__name__)


class CitationQualityChecker:
    """Check citation quality of report.

    Evaluates:
    - Citation coverage
    - Citation accuracy
    - Bibliography completeness
    - Source diversity
    - Citation formatting
    """

    def __init__(
        self,
        min_citations_per_section: int = 2,
        min_source_diversity: float = 0.5,
    ):
        """Initialize citation quality checker.

        Args:
            min_citations_per_section: Minimum citations per section
            min_source_diversity: Minimum source diversity ratio
        """
        self.min_citations_per_section = min_citations_per_section
        self.min_source_diversity = min_source_diversity

    def check(self, report: DomainReport) -> DimensionScore:
        """Check citation quality.

        Args:
            report: Report to check

        Returns:
            Citation quality dimension score
        """
        logger.info(f"Checking citation quality for report {report.report_id}")

        dimension_score = DimensionScore(
            dimension=QualityDimension.CITATIONS,
            threshold=70.0,
        )

        # Check citation coverage
        coverage_metric = self._check_citation_coverage(report, dimension_score)
        dimension_score.add_metric(coverage_metric)

        # Check bibliography completeness
        bibliography_metric = self._check_bibliography(report, dimension_score)
        dimension_score.add_metric(bibliography_metric)

        # Check source diversity
        diversity_metric = self._check_source_diversity(report, dimension_score)
        dimension_score.add_metric(diversity_metric)

        # Calculate overall dimension score
        dimension_score.calculate_score()

        logger.info(
            f"Citation quality score: {dimension_score.score:.2f} "
            f"({dimension_score.level.value})"
        )

        return dimension_score

    def _check_citation_coverage(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check citation coverage.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Citation coverage metric
        """
        sections = report.get_all_sections()
        sections_with_citations = 0
        total_citations = 0

        for section in sections:
            # Check if section metadata has citations
            citation_ids = section.metadata.get("citation_ids", [])

            if citation_ids:
                sections_with_citations += 1
                total_citations += len(citation_ids)
            elif len(section.get_content()) > 0:
                # Section has content but no citations
                dimension_score.add_issue(
                    QualityIssue(
                        severity=IssueSeverity.MEDIUM,
                        dimension=QualityDimension.CITATIONS,
                        title="Missing Citations",
                        description=f"Section '{section.section_title}' has no citations",
                        location=f"Section {section.section_number}",
                        recommendation="Add citations to support claims",
                        auto_fixable=False,
                    )
                )

        # Calculate coverage score
        if not sections:
            score = 100.0
        else:
            coverage_ratio = sections_with_citations / len(sections)
            score = coverage_ratio * 100

        return QualityMetric(
            name="Citation Coverage",
            dimension=QualityDimension.CITATIONS,
            score=score,
            weight=1.5,
            description="Percentage of sections with citations",
            threshold=75.0,
            metadata={
                "total_sections": len(sections),
                "sections_with_citations": sections_with_citations,
                "total_citations": total_citations,
                "avg_citations_per_section": total_citations / max(1, len(sections)),
            },
        )

    def _check_bibliography(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check bibliography completeness.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Bibliography metric
        """
        # Check if report has bibliography metadata
        bib_stats = report.metadata.get("bibliography", {})

        total_citations = bib_stats.get("total_citations", 0)
        used_citations = bib_stats.get("used_citations", 0)
        unused_citations = bib_stats.get("unused_citations", 0)

        # Check for unused citations
        if unused_citations > 0:
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.LOW,
                    dimension=QualityDimension.CITATIONS,
                    title="Unused Citations",
                    description=f"{unused_citations} citations in bibliography are not used",
                    location="Bibliography",
                    recommendation="Remove unused citations or reference them in text",
                    auto_fixable=True,
                )
            )

        # Check for adequate number of citations
        if total_citations == 0:
            score = 0.0
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.CRITICAL,
                    dimension=QualityDimension.CITATIONS,
                    title="No Bibliography",
                    description="Report has no bibliography",
                    location="Report",
                    recommendation="Add citations and bibliography",
                    auto_fixable=False,
                )
            )
        elif total_citations < 5:
            score = 50.0
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.MEDIUM,
                    dimension=QualityDimension.CITATIONS,
                    title="Insufficient Citations",
                    description=f"Only {total_citations} citations in bibliography",
                    location="Bibliography",
                    recommendation="Add more citations from diverse sources",
                    auto_fixable=False,
                )
            )
        else:
            # Score based on usage ratio
            if total_citations > 0:
                usage_ratio = used_citations / total_citations
                score = usage_ratio * 100
            else:
                score = 0.0

        return QualityMetric(
            name="Bibliography Completeness",
            dimension=QualityDimension.CITATIONS,
            score=score,
            weight=1.3,
            description="Bibliography completeness and usage",
            threshold=70.0,
            metadata={
                "total_citations": total_citations,
                "used_citations": used_citations,
                "unused_citations": unused_citations,
            },
        )

    def _check_source_diversity(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check source diversity.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Source diversity metric
        """
        bib_stats = report.metadata.get("bibliography", {})
        citations_by_type = bib_stats.get("citations_by_type", {})

        total_citations = sum(citations_by_type.values())
        unique_types = len(citations_by_type)

        # Check diversity
        if total_citations == 0:
            score = 0.0
        elif unique_types == 1:
            score = 40.0
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.MEDIUM,
                    dimension=QualityDimension.CITATIONS,
                    title="Low Source Diversity",
                    description="All citations are from the same source type",
                    location="Bibliography",
                    recommendation="Add citations from diverse source types (web, academic, databases)",
                    auto_fixable=False,
                )
            )
        else:
            # Calculate diversity score
            # Ideal: 3+ different source types
            diversity_ratio = min(unique_types / 3, 1.0)
            score = diversity_ratio * 100

        return QualityMetric(
            name="Source Diversity",
            dimension=QualityDimension.CITATIONS,
            score=score,
            weight=1.2,
            description="Diversity of citation source types",
            threshold=60.0,
            metadata={
                "total_citations": total_citations,
                "unique_source_types": unique_types,
                "citations_by_type": citations_by_type,
            },
        )
