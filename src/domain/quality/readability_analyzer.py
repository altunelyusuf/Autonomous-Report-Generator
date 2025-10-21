"""Readability analyzer."""

import logging
import re
from typing import List

from src.domain.models.report import DomainReport, ReportSection
from src.domain.quality.models import (
    DimensionScore,
    IssueSeverity,
    QualityDimension,
    QualityIssue,
    QualityMetric,
    ReadabilityMetrics,
)

logger = logging.getLogger(__name__)


class ReadabilityAnalyzer:
    """Analyze readability of report content.

    Calculates various readability metrics:
    - Flesch Reading Ease
    - Flesch-Kincaid Grade Level
    - Average sentence length
    - Average word length
    """

    def __init__(
        self,
        target_reading_level: float = 12.0,
        max_sentence_length: int = 25,
    ):
        """Initialize readability analyzer.

        Args:
            target_reading_level: Target grade level (12 = high school)
            max_sentence_length: Maximum words per sentence
        """
        self.target_reading_level = target_reading_level
        self.max_sentence_length = max_sentence_length

    def check(self, report: DomainReport) -> DimensionScore:
        """Check readability.

        Args:
            report: Report to check

        Returns:
            Readability dimension score
        """
        logger.info(f"Analyzing readability for report {report.report_id}")

        dimension_score = DimensionScore(
            dimension=QualityDimension.READABILITY,
            threshold=65.0,
        )

        # Extract all text
        text = self._extract_report_text(report)

        # Calculate readability metrics
        metrics = self._calculate_readability_metrics(text)

        # Create metrics and check thresholds
        reading_ease_metric = self._create_reading_ease_metric(metrics, dimension_score)
        dimension_score.add_metric(reading_ease_metric)

        grade_level_metric = self._create_grade_level_metric(metrics, dimension_score)
        dimension_score.add_metric(grade_level_metric)

        sentence_length_metric = self._create_sentence_length_metric(metrics, dimension_score)
        dimension_score.add_metric(sentence_length_metric)

        # Calculate overall dimension score
        dimension_score.calculate_score()

        logger.info(
            f"Readability score: {dimension_score.score:.2f} "
            f"({dimension_score.level.value})"
        )

        return dimension_score

    def _extract_report_text(self, report: DomainReport) -> str:
        """Extract all text from report.

        Args:
            report: Report

        Returns:
            Combined text
        """
        texts = []
        for section in report.get_all_sections():
            section_text = self._extract_section_text(section)
            if section_text:
                texts.append(section_text)
        return " ".join(texts)

    def _extract_section_text(self, section: ReportSection) -> str:
        """Extract text from section.

        Args:
            section: Report section

        Returns:
            Section text
        """
        texts = []
        for item in section.get_content():
            if isinstance(item, dict):
                text = item.get("text", "")
            else:
                text = str(item)

            if text:
                texts.append(text)

        return " ".join(texts)

    def _calculate_readability_metrics(self, text: str) -> ReadabilityMetrics:
        """Calculate readability metrics.

        Args:
            text: Text to analyze

        Returns:
            Readability metrics
        """
        metrics = ReadabilityMetrics()

        if not text or len(text.strip()) == 0:
            return metrics

        # Count sentences, words, syllables
        sentences = self._count_sentences(text)
        words = self._count_words(text)
        syllables = self._count_syllables(text)
        characters = len(text.replace(" ", ""))

        if sentences == 0 or words == 0:
            return metrics

        # Calculate basic metrics
        metrics.average_sentence_length = words / sentences
        metrics.average_word_length = characters / words

        # Calculate Flesch Reading Ease
        # Formula: 206.835 - 1.015(total words/total sentences) - 84.6(total syllables/total words)
        if syllables > 0:
            metrics.flesch_reading_ease = (
                206.835
                - 1.015 * (words / sentences)
                - 84.6 * (syllables / words)
            )
            # Clamp to 0-100
            metrics.flesch_reading_ease = max(0, min(100, metrics.flesch_reading_ease))

        # Calculate Flesch-Kincaid Grade Level
        # Formula: 0.39(total words/total sentences) + 11.8(total syllables/total words) - 15.59
        if syllables > 0:
            metrics.flesch_kincaid_grade = (
                0.39 * (words / sentences)
                + 11.8 * (syllables / words)
                - 15.59
            )
            metrics.flesch_kincaid_grade = max(0, metrics.flesch_kincaid_grade)

        # Calculate Gunning Fog Index
        # Formula: 0.4[(words/sentences) + 100(complex words/words)]
        complex_words = self._count_complex_words(text)
        if words > 0:
            metrics.gunning_fog = 0.4 * (
                (words / sentences) + 100 * (complex_words / words)
            )

        # Estimate reading time (average 200 words per minute)
        metrics.reading_time_minutes = words / 200

        return metrics

    def _count_sentences(self, text: str) -> int:
        """Count sentences in text.

        Args:
            text: Text to analyze

        Returns:
            Sentence count
        """
        # Split on sentence-ending punctuation
        sentences = re.split(r'[.!?]+', text)
        return len([s for s in sentences if s.strip()])

    def _count_words(self, text: str) -> int:
        """Count words in text.

        Args:
            text: Text to analyze

        Returns:
            Word count
        """
        words = re.findall(r'\b\w+\b', text)
        return len(words)

    def _count_syllables(self, text: str) -> int:
        """Count syllables in text.

        Args:
            text: Text to analyze

        Returns:
            Syllable count (approximate)
        """
        words = re.findall(r'\b\w+\b', text.lower())
        syllable_count = 0

        for word in words:
            syllable_count += self._count_word_syllables(word)

        return syllable_count

    def _count_word_syllables(self, word: str) -> int:
        """Count syllables in a word (approximate).

        Args:
            word: Word to analyze

        Returns:
            Syllable count
        """
        word = word.lower()

        # Count vowel groups
        vowels = "aeiouy"
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel

        # Adjust for silent e
        if word.endswith('e'):
            syllable_count -= 1

        # Every word has at least one syllable
        if syllable_count == 0:
            syllable_count = 1

        return syllable_count

    def _count_complex_words(self, text: str) -> int:
        """Count complex words (3+ syllables).

        Args:
            text: Text to analyze

        Returns:
            Complex word count
        """
        words = re.findall(r'\b\w+\b', text.lower())
        complex_count = 0

        for word in words:
            if self._count_word_syllables(word) >= 3:
                complex_count += 1

        return complex_count

    def _create_reading_ease_metric(
        self, metrics: ReadabilityMetrics, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Create reading ease metric.

        Args:
            metrics: Readability metrics
            dimension_score: Dimension score

        Returns:
            Reading ease metric
        """
        score = metrics.flesch_reading_ease

        # Check if reading is too difficult
        if score < 30:
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.HIGH,
                    dimension=QualityDimension.READABILITY,
                    title="Very Difficult Reading",
                    description=f"Flesch Reading Ease score is {score:.1f} (very difficult)",
                    location="Report Content",
                    recommendation="Simplify sentence structure and use shorter words",
                    auto_fixable=False,
                )
            )
        elif score < 50:
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.MEDIUM,
                    dimension=QualityDimension.READABILITY,
                    title="Difficult Reading",
                    description=f"Flesch Reading Ease score is {score:.1f} (difficult)",
                    location="Report Content",
                    recommendation="Consider simplifying complex sentences",
                    auto_fixable=False,
                )
            )

        return QualityMetric(
            name="Reading Ease",
            dimension=QualityDimension.READABILITY,
            score=score,
            weight=1.5,
            description="Flesch Reading Ease score",
            threshold=50.0,
            metadata={
                "flesch_reading_ease": metrics.flesch_reading_ease,
            },
        )

    def _create_grade_level_metric(
        self, metrics: ReadabilityMetrics, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Create grade level metric.

        Args:
            metrics: Readability metrics
            dimension_score: Dimension score

        Returns:
            Grade level metric
        """
        grade_level = metrics.flesch_kincaid_grade

        # Check if grade level is appropriate
        if grade_level > self.target_reading_level + 2:
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.MEDIUM,
                    dimension=QualityDimension.READABILITY,
                    title="High Grade Level",
                    description=f"Reading level is grade {grade_level:.1f}, target is {self.target_reading_level}",
                    location="Report Content",
                    recommendation="Simplify content for broader accessibility",
                    auto_fixable=False,
                )
            )

        # Score: 100 at target level, decrease for deviation
        deviation = abs(grade_level - self.target_reading_level)
        score = max(0, 100 - (deviation * 5))

        return QualityMetric(
            name="Grade Level",
            dimension=QualityDimension.READABILITY,
            score=score,
            weight=1.3,
            description="Flesch-Kincaid Grade Level",
            threshold=60.0,
            metadata={
                "flesch_kincaid_grade": metrics.flesch_kincaid_grade,
                "target_grade_level": self.target_reading_level,
                "reading_level": metrics.get_reading_level(),
            },
        )

    def _create_sentence_length_metric(
        self, metrics: ReadabilityMetrics, dimension_score: DimensionScore
    ) -> QualityMetric:
        """Create sentence length metric.

        Args:
            metrics: Readability metrics
            dimension_score: Dimension score

        Returns:
            Sentence length metric
        """
        avg_length = metrics.average_sentence_length

        # Check for overly long sentences
        if avg_length > self.max_sentence_length:
            dimension_score.add_issue(
                QualityIssue(
                    severity=IssueSeverity.LOW,
                    dimension=QualityDimension.READABILITY,
                    title="Long Sentences",
                    description=f"Average sentence length is {avg_length:.1f} words (recommended: {self.max_sentence_length})",
                    location="Report Content",
                    recommendation="Break long sentences into shorter ones",
                    auto_fixable=False,
                )
            )

        # Score: 100 at ideal (15-20), decrease for deviation
        if 15 <= avg_length <= 20:
            score = 100.0
        elif avg_length < 15:
            score = (avg_length / 15) * 100
        else:
            excess = avg_length - 20
            score = max(0, 100 - (excess * 3))

        return QualityMetric(
            name="Sentence Length",
            dimension=QualityDimension.READABILITY,
            score=score,
            weight=1.2,
            description="Average sentence length",
            threshold=60.0,
            metadata={
                "average_sentence_length": metrics.average_sentence_length,
                "max_recommended": self.max_sentence_length,
            },
        )
