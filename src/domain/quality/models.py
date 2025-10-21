"""Domain models for quality assessment."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4


class QualityDimension(str, Enum):
    """Quality assessment dimensions."""

    CONTENT = "content"
    STRUCTURE = "structure"
    CITATIONS = "citations"
    READABILITY = "readability"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"


class QualityLevel(str, Enum):
    """Quality level classifications."""

    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 75-89
    FAIR = "fair"  # 60-74
    POOR = "poor"  # 40-59
    INADEQUATE = "inadequate"  # 0-39


class IssueSeverity(str, Enum):
    """Issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class QualityMetric:
    """Individual quality metric.

    Attributes:
        metric_id: Unique metric identifier
        name: Metric name
        dimension: Quality dimension
        score: Score value (0-100)
        weight: Metric weight for aggregation
        description: Metric description
        threshold: Minimum acceptable score
        metadata: Additional metadata
    """

    metric_id: UUID = field(default_factory=uuid4)
    name: str = ""
    dimension: QualityDimension = QualityDimension.CONTENT
    score: float = 0.0
    weight: float = 1.0
    description: str = ""
    threshold: float = 60.0
    metadata: Dict[str, any] = field(default_factory=dict)

    def is_passing(self) -> bool:
        """Check if metric passes threshold.

        Returns:
            True if score >= threshold
        """
        return self.score >= self.threshold

    def get_level(self) -> QualityLevel:
        """Get quality level based on score.

        Returns:
            Quality level
        """
        if self.score >= 90:
            return QualityLevel.EXCELLENT
        elif self.score >= 75:
            return QualityLevel.GOOD
        elif self.score >= 60:
            return QualityLevel.FAIR
        elif self.score >= 40:
            return QualityLevel.POOR
        else:
            return QualityLevel.INADEQUATE


@dataclass
class QualityIssue:
    """Quality issue or problem found.

    Attributes:
        issue_id: Unique issue identifier
        severity: Issue severity
        dimension: Quality dimension
        title: Issue title
        description: Detailed description
        location: Location in report (section, line, etc.)
        recommendation: Suggested fix
        auto_fixable: Whether issue can be auto-fixed
        metadata: Additional metadata
    """

    issue_id: UUID = field(default_factory=uuid4)
    severity: IssueSeverity = IssueSeverity.MEDIUM
    dimension: QualityDimension = QualityDimension.CONTENT
    title: str = ""
    description: str = ""
    location: Optional[str] = None
    recommendation: Optional[str] = None
    auto_fixable: bool = False
    metadata: Dict[str, any] = field(default_factory=dict)

    def get_severity_score(self) -> int:
        """Get numeric severity score.

        Returns:
            Severity score (1-5)
        """
        severity_scores = {
            IssueSeverity.CRITICAL: 5,
            IssueSeverity.HIGH: 4,
            IssueSeverity.MEDIUM: 3,
            IssueSeverity.LOW: 2,
            IssueSeverity.INFO: 1,
        }
        return severity_scores.get(self.severity, 3)


@dataclass
class DimensionScore:
    """Quality score for a dimension.

    Attributes:
        dimension: Quality dimension
        score: Overall dimension score (0-100)
        level: Quality level
        metrics: Individual metrics
        issues: Issues found in this dimension
        passed: Whether dimension passed threshold
        threshold: Minimum acceptable score
    """

    dimension: QualityDimension
    score: float = 0.0
    level: QualityLevel = QualityLevel.INADEQUATE
    metrics: List[QualityMetric] = field(default_factory=list)
    issues: List[QualityIssue] = field(default_factory=list)
    passed: bool = False
    threshold: float = 60.0

    def calculate_score(self) -> float:
        """Calculate dimension score from metrics.

        Returns:
            Weighted average score
        """
        if not self.metrics:
            return 0.0

        total_weight = sum(m.weight for m in self.metrics)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(m.score * m.weight for m in self.metrics)
        self.score = weighted_sum / total_weight

        # Update level
        if self.score >= 90:
            self.level = QualityLevel.EXCELLENT
        elif self.score >= 75:
            self.level = QualityLevel.GOOD
        elif self.score >= 60:
            self.level = QualityLevel.FAIR
        elif self.score >= 40:
            self.level = QualityLevel.POOR
        else:
            self.level = QualityLevel.INADEQUATE

        # Update passed status
        self.passed = self.score >= self.threshold

        return self.score

    def add_metric(self, metric: QualityMetric) -> None:
        """Add a metric.

        Args:
            metric: Quality metric
        """
        self.metrics.append(metric)

    def add_issue(self, issue: QualityIssue) -> None:
        """Add an issue.

        Args:
            issue: Quality issue
        """
        self.issues.append(issue)

    def get_critical_issues(self) -> List[QualityIssue]:
        """Get critical issues.

        Returns:
            List of critical issues
        """
        return [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]

    def get_issue_count_by_severity(self) -> Dict[IssueSeverity, int]:
        """Get issue counts by severity.

        Returns:
            Dictionary of severity to count
        """
        counts = {severity: 0 for severity in IssueSeverity}
        for issue in self.issues:
            counts[issue.severity] += 1
        return counts


@dataclass
class QualityAssessment:
    """Complete quality assessment result.

    Attributes:
        assessment_id: Unique assessment identifier
        report_id: ID of assessed report
        overall_score: Overall quality score (0-100)
        overall_level: Overall quality level
        dimension_scores: Scores by dimension
        total_issues: Total issues found
        critical_issues: Critical issues count
        passed: Whether assessment passed
        threshold: Overall threshold
        recommendations: List of recommendations
        assessed_at: Assessment timestamp
        metadata: Additional metadata
    """

    assessment_id: UUID = field(default_factory=uuid4)
    report_id: UUID = field(default_factory=uuid4)
    overall_score: float = 0.0
    overall_level: QualityLevel = QualityLevel.INADEQUATE
    dimension_scores: Dict[QualityDimension, DimensionScore] = field(default_factory=dict)
    total_issues: int = 0
    critical_issues: int = 0
    passed: bool = False
    threshold: float = 75.0
    recommendations: List[str] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, any] = field(default_factory=dict)

    def calculate_overall_score(self) -> float:
        """Calculate overall score from dimension scores.

        Returns:
            Overall weighted score
        """
        if not self.dimension_scores:
            return 0.0

        # Default weights for dimensions
        weights = {
            QualityDimension.CONTENT: 0.25,
            QualityDimension.STRUCTURE: 0.15,
            QualityDimension.CITATIONS: 0.15,
            QualityDimension.READABILITY: 0.15,
            QualityDimension.COMPLETENESS: 0.15,
            QualityDimension.CONSISTENCY: 0.10,
            QualityDimension.ACCURACY: 0.05,
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for dimension, dim_score in self.dimension_scores.items():
            weight = weights.get(dimension, 0.1)
            total_weight += weight
            weighted_sum += dim_score.score * weight

        if total_weight == 0:
            return 0.0

        self.overall_score = weighted_sum / total_weight

        # Update level
        if self.overall_score >= 90:
            self.overall_level = QualityLevel.EXCELLENT
        elif self.overall_score >= 75:
            self.overall_level = QualityLevel.GOOD
        elif self.overall_score >= 60:
            self.overall_level = QualityLevel.FAIR
        elif self.overall_score >= 40:
            self.overall_level = QualityLevel.POOR
        else:
            self.overall_level = QualityLevel.INADEQUATE

        # Update passed status
        self.passed = self.overall_score >= self.threshold

        # Count issues
        self.total_issues = sum(
            len(dim_score.issues) for dim_score in self.dimension_scores.values()
        )
        self.critical_issues = sum(
            len(dim_score.get_critical_issues())
            for dim_score in self.dimension_scores.values()
        )

        return self.overall_score

    def add_dimension_score(self, dimension_score: DimensionScore) -> None:
        """Add a dimension score.

        Args:
            dimension_score: Dimension score to add
        """
        self.dimension_scores[dimension_score.dimension] = dimension_score

    def get_all_issues(self) -> List[QualityIssue]:
        """Get all issues across dimensions.

        Returns:
            List of all issues
        """
        all_issues = []
        for dim_score in self.dimension_scores.values():
            all_issues.extend(dim_score.issues)
        return all_issues

    def get_issues_by_severity(self, severity: IssueSeverity) -> List[QualityIssue]:
        """Get issues by severity.

        Args:
            severity: Severity level

        Returns:
            List of issues with given severity
        """
        return [issue for issue in self.get_all_issues() if issue.severity == severity]

    def add_recommendation(self, recommendation: str) -> None:
        """Add a recommendation.

        Args:
            recommendation: Recommendation text
        """
        self.recommendations.append(recommendation)

    def to_summary(self) -> Dict[str, any]:
        """Convert to summary dictionary.

        Returns:
            Summary dictionary
        """
        return {
            "assessment_id": str(self.assessment_id),
            "report_id": str(self.report_id),
            "overall_score": round(self.overall_score, 2),
            "overall_level": self.overall_level.value,
            "passed": self.passed,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "dimensions": {
                dim.value: {
                    "score": round(score.score, 2),
                    "level": score.level.value,
                    "passed": score.passed,
                    "issues": len(score.issues),
                }
                for dim, score in self.dimension_scores.items()
            },
            "assessed_at": self.assessed_at.isoformat(),
        }


@dataclass
class ReadabilityMetrics:
    """Readability metrics for content.

    Attributes:
        flesch_reading_ease: Flesch Reading Ease score (0-100)
        flesch_kincaid_grade: Flesch-Kincaid Grade Level
        gunning_fog: Gunning Fog Index
        smog_index: SMOG Index
        coleman_liau_index: Coleman-Liau Index
        automated_readability_index: Automated Readability Index
        average_sentence_length: Average words per sentence
        average_word_length: Average characters per word
        difficult_words: Count of difficult words
        reading_time_minutes: Estimated reading time
    """

    flesch_reading_ease: float = 0.0
    flesch_kincaid_grade: float = 0.0
    gunning_fog: float = 0.0
    smog_index: float = 0.0
    coleman_liau_index: float = 0.0
    automated_readability_index: float = 0.0
    average_sentence_length: float = 0.0
    average_word_length: float = 0.0
    difficult_words: int = 0
    reading_time_minutes: float = 0.0

    def get_overall_readability_score(self) -> float:
        """Calculate overall readability score.

        Returns:
            Readability score (0-100)
        """
        # Use Flesch Reading Ease as primary metric
        # Normalize to 0-100 scale
        score = max(0, min(100, self.flesch_reading_ease))
        return score

    def get_reading_level(self) -> str:
        """Get reading level description.

        Returns:
            Reading level description
        """
        grade = self.flesch_kincaid_grade

        if grade <= 6:
            return "Elementary"
        elif grade <= 8:
            return "Middle School"
        elif grade <= 12:
            return "High School"
        elif grade <= 16:
            return "College"
        else:
            return "Graduate"
