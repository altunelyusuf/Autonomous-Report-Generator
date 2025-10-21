"""Structure quality checker."""

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


class StructureQualityChecker:
    """Check structure quality of report.

    Evaluates:
    - Hierarchical organization
    - Section numbering
    - Logical flow
    - Balanced structure
    - Section depth
    """

    def __init__(
        self,
        max_hierarchy_depth: int = 4,
        min_sections: int = 3,
        max_sections: int = 50,
    ):
        """Initialize structure quality checker.

        Args:
            max_hierarchy_depth: Maximum recommended hierarchy depth
            min_sections: Minimum sections in report
            max_sections: Maximum sections in report
        """
        self.max_hierarchy_depth = max_hierarchy_depth
        self.min_sections = min_sections
        self.max_sections = max_sections

    def check(self, report: DomainReport) -> DimensionScore:
        """Check structure quality.

        Args:
            report: Report to check

        Returns:
            Structure quality dimension score
        """
        logger.info(f"Checking structure quality for report {report.report_id}")

        dimension_score = DimensionScore(
            dimension=QualityDimension.STRUCTURE,
            threshold=70.0,
        )

        # Check organization
        organization_metric = self._check_organization(report, dimension_score)
        dimension_score.add_metric(organization_metric)

        # Check hierarchy
        hierarchy_metric = self._check_hierarchy(report, dimension_score)
        dimension_score.add_metric(hierarchy_metric)

        # Check balance
        balance_metric = self._check_balance(report, dimension_score)
        dimension_score.add_metric(balance_metric)

        # Check section count
        count_metric = self._check_section_count(report, dimension_score)
        dimension_score.add_metric(count_metric)

        # Calculate overall dimension score
        dimension_score.calculate_score()

        logger.info(
            f"Structure quality score: {dimension_score.score:.2f} "
            f"({dimension_score.level.value})"
        )

        return dimension_score

    def _check_organization(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check organizational structure.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Organization metric
        """
        sections = report.get_all_sections()

        # Check for logical section numbering
        numbering_issues = 0
        for i, section in enumerate(sections):
            # Basic check: section number should be reasonable
            if not section.section_number:
                numbering_issues += 1
                dimension_score.add_issue(
                    QualityIssue(
                        severity=IssueSeverity.MEDIUM,
                        dimension=QualityDimension.STRUCTURE,
                        title="Missing Section Number",
                        description=f"Section '{section.section_title}' has no number",
                        location=f"Section index {i}",
                        recommendation="Add proper section numbering",
                        auto_fixable=True,
                    )
                )

        # Calculate organization score
        if not sections:
            score = 0.0
        else:
            properly_numbered = len(sections) - numbering_issues
            score = (properly_numbered / len(sections)) * 100

        return QualityMetric(
            name="Section Organization",
            dimension=QualityDimension.STRUCTURE,
            score=score,
            weight=1.4,
            description="Logical section organization and numbering",
            threshold=80.0,
            metadata={
                "total_sections": len(sections),
                "numbering_issues": numbering_issues,
            },
        )

    def _check_hierarchy(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check hierarchy depth and structure.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Hierarchy metric
        """
        sections = report.get_all_sections()

        if not sections:
            return QualityMetric(
                name="Hierarchy Structure",
                dimension=QualityDimension.STRUCTURE,
                score=0.0,
                weight=1.3,
                description="Appropriate hierarchy depth",
                threshold=70.0,
            )

        # Find maximum depth
        max_depth = max(section.hierarchy_level for section in sections)

        # Check for excessive depth
        if max_depth > self.max_hierarchy_depth:
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.MEDIUM,
                    dimension=QualityDimension.STRUCTURE,
                    title="Excessive Hierarchy Depth",
                    description=f"Maximum hierarchy depth is {max_depth}, recommended is {self.max_hierarchy_depth}",
                    location="Report Structure",
                    recommendation=f"Reduce nesting to maximum {self.max_hierarchy_depth} levels",
                    auto_fixable=False,
                )
            )

        # Calculate hierarchy score
        if max_depth == 0:
            # Flat structure - not ideal
            score = 50.0
        elif max_depth <= self.max_hierarchy_depth:
            # Good hierarchy
            score = 100.0
        else:
            # Too deep
            excess = max_depth - self.max_hierarchy_depth
            score = max(0, 100 - (excess * 15))

        return QualityMetric(
            name="Hierarchy Structure",
            dimension=QualityDimension.STRUCTURE,
            score=score,
            weight=1.3,
            description="Appropriate hierarchy depth",
            threshold=70.0,
            metadata={
                "max_depth": max_depth,
                "recommended_max_depth": self.max_hierarchy_depth,
            },
        )

    def _check_balance(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check structural balance.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Balance metric
        """
        sections = report.get_all_sections()

        if not sections:
            return QualityMetric(
                name="Structural Balance",
                dimension=QualityDimension.STRUCTURE,
                score=0.0,
                weight=1.1,
                description="Balanced section distribution",
                threshold=60.0,
            )

        # Count sections at each level
        level_counts = {}
        for section in sections:
            level = section.hierarchy_level
            level_counts[level] = level_counts.get(level, 0) + 1

        # Check for balance at level 0 (main sections)
        main_sections = level_counts.get(0, 0)

        # Check for orphan sections (single child)
        orphan_count = 0
        for section in sections:
            subsections = section.get_subsections()
            if len(subsections) == 1:
                orphan_count += 1
                dimension_score.add_issue(
                    QualityIssue(
                        severity=IssueSeverity.LOW,
                        dimension=QualityDimension.STRUCTURE,
                        title="Single Subsection",
                        description=f"Section '{section.section_title}' has only one subsection",
                        location=f"Section {section.section_number}",
                        recommendation="Either add more subsections or merge with parent",
                        auto_fixable=False,
                    )
                )

        # Calculate balance score
        if main_sections >= 3:
            balance_score = 100.0
        elif main_sections >= 2:
            balance_score = 80.0
        else:
            balance_score = 50.0

        # Penalize for orphans
        if sections:
            orphan_penalty = (orphan_count / len(sections)) * 30
            balance_score = max(0, balance_score - orphan_penalty)

        return QualityMetric(
            name="Structural Balance",
            dimension=QualityDimension.STRUCTURE,
            score=balance_score,
            weight=1.1,
            description="Balanced section distribution",
            threshold=60.0,
            metadata={
                "main_sections": main_sections,
                "orphan_sections": orphan_count,
                "level_counts": level_counts,
            },
        )

    def _check_section_count(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check section count.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Section count metric
        """
        section_count = report.get_section_count()

        # Check for too few sections
        if section_count < self.min_sections:
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.HIGH,
                    dimension=QualityDimension.STRUCTURE,
                    title="Too Few Sections",
                    description=f"Report has only {section_count} sections, minimum recommended is {self.min_sections}",
                    location="Report",
                    recommendation=f"Add more sections to reach minimum of {self.min_sections}",
                    auto_fixable=False,
                )
            )

        # Check for too many sections
        if section_count > self.max_sections:
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.MEDIUM,
                    dimension=QualityDimension.STRUCTURE,
                    title="Too Many Sections",
                    description=f"Report has {section_count} sections, maximum recommended is {self.max_sections}",
                    location="Report",
                    recommendation="Consider consolidating related sections",
                    auto_fixable=False,
                )
            )

        # Calculate score
        if section_count < self.min_sections:
            score = (section_count / self.min_sections) * 60
        elif section_count > self.max_sections:
            excess = section_count - self.max_sections
            score = max(0, 100 - (excess * 2))
        else:
            score = 100.0

        return QualityMetric(
            name="Section Count",
            dimension=QualityDimension.STRUCTURE,
            score=score,
            weight=1.0,
            description="Appropriate number of sections",
            threshold=70.0,
            metadata={
                "section_count": section_count,
                "min_sections": self.min_sections,
                "max_sections": self.max_sections,
            },
        )
