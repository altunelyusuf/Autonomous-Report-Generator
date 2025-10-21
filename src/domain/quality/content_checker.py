"""Content quality checker."""

import logging
from typing import List

from src.domain.models.report import DomainReport, ReportSection
from src.domain.quality.models import (
    DimensionScore,
    IssueSeverity,
    QualityDimension,
    QualityIssue,
    QualityMetric,
)

logger = logging.getLogger(__name__)


class ContentQualityChecker:
    """Check content quality of report.

    Evaluates:
    - Content completeness
    - Content depth
    - Content coherence
    - Content relevance
    - Information density
    """

    def __init__(
        self,
        min_section_content_items: int = 1,
        min_content_length: int = 100,
        min_depth_score: float = 60.0,
    ):
        """Initialize content quality checker.

        Args:
            min_section_content_items: Minimum content items per section
            min_content_length: Minimum content length (characters)
            min_depth_score: Minimum depth score
        """
        self.min_section_content_items = min_section_content_items
        self.min_content_length = min_content_length
        self.min_depth_score = min_depth_score

    def check(self, report: DomainReport) -> DimensionScore:
        """Check content quality.

        Args:
            report: Report to check

        Returns:
            Content quality dimension score
        """
        logger.info(f"Checking content quality for report {report.report_id}")

        dimension_score = DimensionScore(
            dimension=QualityDimension.CONTENT,
            threshold=self.min_depth_score,
        )

        # Check completeness
        completeness_metric = self._check_completeness(report, dimension_score)
        dimension_score.add_metric(completeness_metric)

        # Check depth
        depth_metric = self._check_depth(report, dimension_score)
        dimension_score.add_metric(depth_metric)

        # Check coherence
        coherence_metric = self._check_coherence(report, dimension_score)
        dimension_score.add_metric(coherence_metric)

        # Check information density
        density_metric = self._check_information_density(report, dimension_score)
        dimension_score.add_metric(density_metric)

        # Calculate overall dimension score
        dimension_score.calculate_score()

        logger.info(
            f"Content quality score: {dimension_score.score:.2f} "
            f"({dimension_score.level.value})"
        )

        return dimension_score

    def _check_completeness(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check content completeness.

        Args:
            report: Report
            dimension_score: Dimension score to add issues to

        Returns:
            Completeness metric
        """
        sections = report.get_all_sections()
        total_sections = len(sections)
        empty_sections = 0
        incomplete_sections = 0

        for section in sections:
            content_items = section.get_content()

            # Check if section has no content
            if not content_items:
                empty_sections += 1
                dimension_score.add_issue(
                    QualityIssue(
                        severity=IssueSeverity.HIGH,
                        dimension=QualityDimension.CONTENT,
                        title="Empty Section",
                        description=f"Section '{section.section_title}' has no content",
                        location=f"Section {section.section_number}",
                        recommendation="Add content to this section or remove it",
                        auto_fixable=False,
                    )
                )

            # Check if section has insufficient content
            elif len(content_items) < self.min_section_content_items:
                incomplete_sections += 1
                dimension_score.add_issue(
                    QualityIssue(
                        severity=IssueSeverity.MEDIUM,
                        dimension=QualityDimension.CONTENT,
                        title="Insufficient Content",
                        description=f"Section '{section.section_title}' has only {len(content_items)} content items",
                        location=f"Section {section.section_number}",
                        recommendation=f"Add at least {self.min_section_content_items} content items",
                        auto_fixable=False,
                    )
                )

        # Calculate completeness score
        if total_sections == 0:
            score = 0.0
        else:
            complete_sections = total_sections - empty_sections - incomplete_sections
            score = (complete_sections / total_sections) * 100

        return QualityMetric(
            name="Content Completeness",
            dimension=QualityDimension.CONTENT,
            score=score,
            weight=1.5,
            description="Percentage of sections with adequate content",
            threshold=80.0,
            metadata={
                "total_sections": total_sections,
                "empty_sections": empty_sections,
                "incomplete_sections": incomplete_sections,
            },
        )

    def _check_depth(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check content depth.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Depth metric
        """
        sections = report.get_all_sections()
        total_content_length = 0
        shallow_sections = 0

        for section in sections:
            content_length = self._get_section_content_length(section)
            total_content_length += content_length

            # Check if section is too shallow
            if content_length > 0 and content_length < self.min_content_length:
                shallow_sections += 1
                dimension_score.add_issue(
                    QualityIssue(
                        severity=IssueSeverity.LOW,
                        dimension=QualityDimension.CONTENT,
                        title="Shallow Content",
                        description=f"Section '{section.section_title}' has only {content_length} characters",
                        location=f"Section {section.section_number}",
                        recommendation=f"Expand content to at least {self.min_content_length} characters",
                        auto_fixable=False,
                    )
                )

        # Calculate depth score based on average content length
        if not sections:
            score = 0.0
        else:
            avg_length = total_content_length / len(sections)
            # Score: 100 at 500+ chars, linear below
            score = min(100, (avg_length / 500) * 100)

        return QualityMetric(
            name="Content Depth",
            dimension=QualityDimension.CONTENT,
            score=score,
            weight=1.3,
            description="Average content depth per section",
            threshold=60.0,
            metadata={
                "total_content_length": total_content_length,
                "average_content_length": total_content_length / max(1, len(sections)),
                "shallow_sections": shallow_sections,
            },
        )

    def _check_coherence(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check content coherence.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Coherence metric
        """
        sections = report.get_all_sections()
        coherence_issues = 0

        for section in sections:
            content_items = section.get_content()

            # Check for very short content items (likely incomplete)
            for item in content_items:
                text = self._extract_text(item)
                if text and len(text.strip()) < 20:
                    coherence_issues += 1

        # Calculate coherence score
        # Assume each section should have coherent content
        if not sections:
            score = 100.0
        else:
            # Penalize for coherence issues
            penalty = (coherence_issues / len(sections)) * 20
            score = max(0, 100 - penalty)

        return QualityMetric(
            name="Content Coherence",
            dimension=QualityDimension.CONTENT,
            score=score,
            weight=1.2,
            description="Content flows logically and coherently",
            threshold=70.0,
            metadata={
                "coherence_issues": coherence_issues,
            },
        )

    def _check_information_density(
        self, report: DomainReport, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Check information density.

        Args:
            report: Report
            dimension_score: Dimension score

        Returns:
            Information density metric
        """
        sections = report.get_all_sections()
        total_words = 0
        total_sentences = 0

        for section in sections:
            content_text = self._get_section_text(section)

            # Count words
            words = content_text.split()
            total_words += len(words)

            # Count sentences (approximate)
            sentences = content_text.split('.')
            total_sentences += len([s for s in sentences if s.strip()])

        # Calculate density
        if total_sentences == 0:
            avg_words_per_sentence = 0
            score = 0.0
        else:
            avg_words_per_sentence = total_words / total_sentences

            # Ideal: 15-20 words per sentence
            # Score based on proximity to ideal
            if 15 <= avg_words_per_sentence <= 20:
                score = 100.0
            elif avg_words_per_sentence < 15:
                # Too sparse
                score = (avg_words_per_sentence / 15) * 100
            else:
                # Too dense
                score = max(0, 100 - (avg_words_per_sentence - 20) * 2)

        return QualityMetric(
            name="Information Density",
            dimension=QualityDimension.CONTENT,
            score=score,
            weight=1.0,
            description="Appropriate information density",
            threshold=60.0,
            metadata={
                "total_words": total_words,
                "total_sentences": total_sentences,
                "avg_words_per_sentence": avg_words_per_sentence,
            },
        )

    def _get_section_content_length(self, section: ReportSection) -> int:
        """Get total content length for section.

        Args:
            section: Report section

        Returns:
            Total character count
        """
        content_text = self._get_section_text(section)
        return len(content_text)

    def _get_section_text(self, section: ReportSection) -> str:
        """Get all text content from section.

        Args:
            section: Report section

        Returns:
            Combined text
        """
        texts = []
        for item in section.get_content():
            text = self._extract_text(item)
            if text:
                texts.append(text)
        return " ".join(texts)

    def _extract_text(self, item: any) -> str:
        """Extract text from content item.

        Args:
            item: Content item

        Returns:
            Extracted text
        """
        if isinstance(item, dict):
            return item.get("text", "")
        return str(item)
