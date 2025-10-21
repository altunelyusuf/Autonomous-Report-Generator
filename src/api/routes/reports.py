"""Report generation and management endpoints."""

import logging
from datetime import datetime
from typing import Dict
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from src.api.exceptions import InvalidRequestException, ReportNotFoundException
from src.api.models import (
    DeleteReportResponse,
    DetailedReportResponse,
    ListReportsRequest,
    ListReportsResponse,
    ReportGenerationRequest,
    ReportResponse,
    ReportStatus,
    SectionSummary,
)
from src.orchestration.orchestrator import (
    ReportGenerationConfig,
    create_default_orchestrator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

# In-memory storage (replace with database in production)
_reports_storage: Dict[UUID, dict] = {}


@router.post(
    "/",
    response_model=ReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate new report",
    description="Submit a request to generate a new research report",
)
async def create_report(request: ReportGenerationRequest) -> ReportResponse:
    """Generate a new report.

    Args:
        request: Report generation request

    Returns:
        Report response with ID and status
    """
    logger.info(f"Received report generation request for query: {request.query}")

    try:
        # Create report ID
        report_id = uuid4()

        # Create initial report entry
        report_data = {
            "report_id": report_id,
            "status": ReportStatus.PENDING,
            "title": f"Research Report: {request.query}",
            "query": request.query,
            "section_count": 0,
            "quality_score": None,
            "completeness_score": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "error_message": None,
            "report": None,
            "assessment": None,
        }

        _reports_storage[report_id] = report_data

        # Start background generation (in production, use task queue)
        # For now, we'll mark it as pending and generate synchronously
        config = ReportGenerationConfig(
            query=request.query,
            ontology_content=request.ontology_content,
            ontology_source=request.ontology_url,
            max_depth=request.max_depth,
            research_enabled=request.research_enabled,
            max_sources=request.max_sources,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
            citation_style=request.citation_style,
            include_bibliography=request.include_bibliography,
            quality_threshold=request.quality_threshold,
        )

        # Generate report (this should be async/background in production)
        try:
            orchestrator = create_default_orchestrator()
            report, assessment = await orchestrator.generate_report(config)

            # Update storage
            report_data["status"] = ReportStatus.COMPLETED
            report_data["section_count"] = report.get_section_count()
            report_data["quality_score"] = assessment.overall_score
            report_data["completeness_score"] = report.completeness_score
            report_data["updated_at"] = datetime.utcnow()
            report_data["report"] = report
            report_data["assessment"] = assessment

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            report_data["status"] = ReportStatus.FAILED
            report_data["error_message"] = str(e)
            report_data["updated_at"] = datetime.utcnow()

        return ReportResponse(**{k: v for k, v in report_data.items() if k in ReportResponse.model_fields})

    except Exception as e:
        logger.error(f"Failed to create report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}",
        )


@router.get(
    "/{report_id}",
    response_model=DetailedReportResponse,
    summary="Get report details",
    description="Retrieve detailed information about a specific report",
)
async def get_report(report_id: UUID) -> DetailedReportResponse:
    """Get report details.

    Args:
        report_id: Report ID

    Returns:
        Detailed report information

    Raises:
        HTTPException: If report not found
    """
    logger.info(f"Retrieving report: {report_id}")

    if report_id not in _reports_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    report_data = _reports_storage[report_id]
    report = report_data.get("report")

    # Build section summaries
    sections = []
    if report:
        for section in report.get_all_sections():
            sections.append(
                SectionSummary(
                    section_id=section.section_id,
                    section_number=section.section_number,
                    title=section.section_title,
                    hierarchy_level=section.hierarchy_level,
                    content_items=len(section.get_content()),
                    has_citations=len(section.citations) > 0 if hasattr(section, "citations") else False,
                )
            )

    return DetailedReportResponse(
        report_id=report_data["report_id"],
        status=report_data["status"],
        title=report_data["title"],
        query=report_data["query"],
        sections=sections,
        quality_score=report_data.get("quality_score", 0.0) or 0.0,
        completeness_score=report_data.get("completeness_score", 0.0) or 0.0,
        total_citations=0,  # TODO: Calculate from report
        created_at=report_data["created_at"],
        updated_at=report_data["updated_at"],
        metadata={},
    )


@router.get(
    "/",
    response_model=ListReportsResponse,
    summary="List reports",
    description="List all reports with optional filtering",
)
async def list_reports(
    skip: int = 0,
    limit: int = 10,
    status: ReportStatus | None = None,
    min_quality: float | None = None,
) -> ListReportsResponse:
    """List reports with pagination.

    Args:
        skip: Number of reports to skip
        limit: Maximum number of reports to return
        status: Filter by status
        min_quality: Minimum quality score

    Returns:
        List of reports
    """
    logger.info(f"Listing reports (skip={skip}, limit={limit})")

    # Filter reports
    filtered_reports = []
    for report_data in _reports_storage.values():
        # Status filter
        if status and report_data["status"] != status:
            continue

        # Quality filter
        if min_quality and (
            report_data.get("quality_score") is None
            or report_data["quality_score"] < min_quality
        ):
            continue

        filtered_reports.append(report_data)

    # Sort by created_at descending
    filtered_reports.sort(key=lambda x: x["created_at"], reverse=True)

    # Paginate
    total = len(filtered_reports)
    paginated = filtered_reports[skip : skip + limit]

    # Convert to response models
    reports = [
        ReportResponse(**{k: v for k, v in r.items() if k in ReportResponse.model_fields})
        for r in paginated
    ]

    return ListReportsResponse(
        reports=reports,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/{report_id}",
    response_model=DeleteReportResponse,
    summary="Delete report",
    description="Delete a report and all associated data",
)
async def delete_report(report_id: UUID) -> DeleteReportResponse:
    """Delete a report.

    Args:
        report_id: Report ID

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If report not found
    """
    logger.info(f"Deleting report: {report_id}")

    if report_id not in _reports_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    del _reports_storage[report_id]

    return DeleteReportResponse(
        report_id=report_id,
        deleted=True,
        message="Report deleted successfully",
    )
