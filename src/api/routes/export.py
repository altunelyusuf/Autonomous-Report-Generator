"""Export endpoints."""

import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from src.api.models import ExportRequest, ExportResponse
from src.domain.export.models import ExportFormat as DomainExportFormat
from src.domain.export.models import ExportOptions
from src.infrastructure.exporters.manager import ExportManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])

# Export manager instance
_export_manager = ExportManager()

# In-memory export storage
_exports_storage = {}


@router.post(
    "/",
    response_model=ExportResponse,
    summary="Export report",
    description="Export a report to the specified format",
)
async def export_report(request: ExportRequest) -> ExportResponse:
    """Export a report.

    Args:
        request: Export request

    Returns:
        Export response with file information
    """
    logger.info(
        f"Exporting report {request.report_id} to {request.format.value} format"
    )

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

        # Map API format to domain format
        format_mapping = {
            "markdown": DomainExportFormat.MARKDOWN,
            "html": DomainExportFormat.HTML,
            "pdf": DomainExportFormat.PDF,
            "docx": DomainExportFormat.DOCX,
            "xlsx": DomainExportFormat.XLSX,
        }

        domain_format = format_mapping.get(request.format.value)
        if not domain_format:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {request.format.value}",
            )

        # Create export options
        options = ExportOptions(
            include_toc=request.include_toc,
            include_metadata=request.include_metadata,
            include_statistics=request.include_statistics,
            include_bibliography=request.include_bibliography,
            theme=request.theme or "light",
        )

        # Create output path
        export_id = uuid4()
        output_dir = Path("/tmp/reports/exports")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get file extension
        extension_map = {
            DomainExportFormat.MARKDOWN: ".md",
            DomainExportFormat.HTML: ".html",
            DomainExportFormat.PDF: ".pdf",
            DomainExportFormat.DOCX: ".docx",
            DomainExportFormat.XLSX: ".xlsx",
        }

        extension = extension_map.get(domain_format, ".txt")
        output_path = output_dir / f"report_{report.report_id}{extension}"

        # Export report
        result = await _export_manager.export(
            report=report,
            format=domain_format,
            output_path=output_path,
            options=options,
        )

        # Store export information
        export_info = {
            "export_id": export_id,
            "report_id": request.report_id,
            "format": request.format.value,
            "status": result.status.value,
            "file_path": str(result.output_path) if result.output_path else None,
            "file_size": result.file_size,
            "download_url": f"/export/{export_id}/download" if result.output_path else None,
            "duration": result.duration,
            "error_message": result.error_message,
            "exported_at": datetime.utcnow() if result.output_path else None,
        }

        _exports_storage[export_id] = export_info

        return ExportResponse(**export_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.get(
    "/{export_id}",
    response_model=ExportResponse,
    summary="Get export status",
    description="Retrieve export operation status and information",
)
async def get_export_status(export_id: UUID) -> ExportResponse:
    """Get export status.

    Args:
        export_id: Export ID

    Returns:
        Export information

    Raises:
        HTTPException: If export not found
    """
    logger.info(f"Retrieving export status: {export_id}")

    if export_id not in _exports_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export not found: {export_id}",
        )

    export_info = _exports_storage[export_id]
    return ExportResponse(**export_info)


@router.get(
    "/{export_id}/download",
    summary="Download exported file",
    description="Download the exported report file",
)
async def download_export(export_id: UUID) -> FileResponse:
    """Download exported file.

    Args:
        export_id: Export ID

    Returns:
        File response

    Raises:
        HTTPException: If export not found or file not available
    """
    logger.info(f"Downloading export: {export_id}")

    if export_id not in _exports_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export not found: {export_id}",
        )

    export_info = _exports_storage[export_id]

    if not export_info["file_path"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export file not available",
        )

    file_path = Path(export_info["file_path"])

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found on disk",
        )

    # Determine media type
    media_types = {
        ".md": "text/markdown",
        ".html": "text/html",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    media_type = media_types.get(file_path.suffix, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )


@router.delete(
    "/{export_id}",
    summary="Delete export",
    description="Delete an export and its associated file",
)
async def delete_export(export_id: UUID) -> dict:
    """Delete an export.

    Args:
        export_id: Export ID

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If export not found
    """
    logger.info(f"Deleting export: {export_id}")

    if export_id not in _exports_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export not found: {export_id}",
        )

    export_info = _exports_storage[export_id]

    # Delete file if it exists
    if export_info["file_path"]:
        file_path = Path(export_info["file_path"])
        if file_path.exists():
            file_path.unlink()

    # Remove from storage
    del _exports_storage[export_id]

    return {
        "export_id": str(export_id),
        "deleted": True,
        "message": "Export deleted successfully",
    }
