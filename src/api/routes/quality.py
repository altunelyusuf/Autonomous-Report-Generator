"""Quality assessment endpoints."""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from src.api.models import (
    QualityAssessmentRequest,
    QualityAssessmentResponse,
    QualityDimensionResponse,
    QualityIssueResponse,
)
from src.domain.quality.assessor import create_default_quality_assessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quality", tags=["quality"])


@router.post(
    "/assess",
    response_model=QualityAssessmentResponse,
    summary="Assess report quality",
    description="Perform comprehensive quality assessment on a report",
)
async def assess_quality(request: QualityAssessmentRequest) -> QualityAssessmentResponse:
    """Assess report quality.

    Args:
        request: Quality assessment request

    Returns:
        Quality assessment results
    """
    logger.info(f"Assessing quality for report: {request.report_id}")

    try:
        # Import here to avoid circular dependency
        from src.api.routes.reports import _reports_storage

        # Get report
        if request.report_id not in _reports_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report not found: {request.report_id}",
            )

        report_data = _reports_storage[request.report_id]
        report = report_data.get("report")

        if not report:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Report has not been generated yet",
            )

        # Create quality assessor
        assessor = create_default_quality_assessor()

        # Perform assessment
        assessment = await assessor.assess(report)

        # Convert dimension scores
        dimensions = {}
        for dim, dim_score in assessment.dimension_scores.items():
            dimensions[dim.value] = QualityDimensionResponse(
                dimension=dim.value,
                score=dim_score.score,
                level=dim_score.level.value,
                passed=dim_score.passed,
                issues=len(dim_score.issues),
                threshold=dim_score.threshold,
            )

        # Store assessment
        report_data["assessment"] = assessment
        report_data["quality_score"] = assessment.overall_score

        return QualityAssessmentResponse(
            assessment_id=assessment.assessment_id,
            report_id=assessment.report_id,
            overall_score=assessment.overall_score,
            overall_level=assessment.overall_level.value,
            passed=assessment.passed,
            threshold=assessment.threshold,
            dimensions=dimensions,
            total_issues=assessment.total_issues,
            critical_issues=assessment.critical_issues,
            recommendations=assessment.recommendations,
            assessed_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quality assessment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quality assessment failed: {str(e)}",
        )


@router.get(
    "/{report_id}",
    response_model=QualityAssessmentResponse,
    summary="Get quality assessment",
    description="Retrieve quality assessment for a report",
)
async def get_quality_assessment(report_id: UUID) -> QualityAssessmentResponse:
    """Get quality assessment for a report.

    Args:
        report_id: Report ID

    Returns:
        Quality assessment results

    Raises:
        HTTPException: If report or assessment not found
    """
    logger.info(f"Retrieving quality assessment for report: {report_id}")

    try:
        # Import here to avoid circular dependency
        from src.api.routes.reports import _reports_storage

        # Get report
        if report_id not in _reports_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report not found: {report_id}",
            )

        report_data = _reports_storage[report_id]
        assessment = report_data.get("assessment")

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quality assessment not found for this report",
            )

        # Convert dimension scores
        dimensions = {}
        for dim, dim_score in assessment.dimension_scores.items():
            dimensions[dim.value] = QualityDimensionResponse(
                dimension=dim.value,
                score=dim_score.score,
                level=dim_score.level.value,
                passed=dim_score.passed,
                issues=len(dim_score.issues),
                threshold=dim_score.threshold,
            )

        return QualityAssessmentResponse(
            assessment_id=assessment.assessment_id,
            report_id=assessment.report_id,
            overall_score=assessment.overall_score,
            overall_level=assessment.overall_level.value,
            passed=assessment.passed,
            threshold=assessment.threshold,
            dimensions=dimensions,
            total_issues=assessment.total_issues,
            critical_issues=assessment.critical_issues,
            recommendations=assessment.recommendations,
            assessed_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve quality assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quality assessment: {str(e)}",
        )


@router.get(
    "/{report_id}/issues",
    response_model=list[QualityIssueResponse],
    summary="Get quality issues",
    description="Retrieve all quality issues for a report",
)
async def get_quality_issues(
    report_id: UUID,
    severity: str | None = None,
) -> list[QualityIssueResponse]:
    """Get quality issues for a report.

    Args:
        report_id: Report ID
        severity: Filter by severity (critical, high, medium, low, info)

    Returns:
        List of quality issues

    Raises:
        HTTPException: If report or assessment not found
    """
    logger.info(f"Retrieving quality issues for report: {report_id}")

    try:
        # Import here to avoid circular dependency
        from src.api.routes.reports import _reports_storage

        # Get report
        if report_id not in _reports_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report not found: {report_id}",
            )

        report_data = _reports_storage[report_id]
        assessment = report_data.get("assessment")

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quality assessment not found for this report",
            )

        # Get all issues
        all_issues = assessment.get_all_issues()

        # Filter by severity if specified
        if severity:
            all_issues = [
                issue for issue in all_issues
                if issue.severity.value.lower() == severity.lower()
            ]

        # Convert to response models
        issues = [
            QualityIssueResponse(
                severity=issue.severity.value,
                dimension=issue.dimension.value,
                title=issue.title,
                description=issue.description,
                location=issue.location,
                recommendation=issue.recommendation,
                auto_fixable=issue.auto_fixable,
            )
            for issue in all_issues
        ]

        return issues

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve quality issues: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quality issues: {str(e)}",
        )
