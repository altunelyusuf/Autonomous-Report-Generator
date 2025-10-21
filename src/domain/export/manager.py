"""Export manager coordinating all exporters."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from src.domain.export.exceptions import ExportException, UnsupportedFormatException
from src.domain.export.exporter import IExporter
from src.domain.export.models import (
    ExportFormat,
    ExportMetrics,
    ExportOptions,
    ExportRequest,
    ExportResult,
)
from src.domain.models.report import DomainReport

logger = logging.getLogger(__name__)


class ExportManager:
    """Manage report export operations.

    Coordinates multiple exporters and handles export requests.

    Features:
    - Multi-format export support
    - Exporter registry
    - Export metrics tracking
    - Batch export
    - Format validation
    """

    def __init__(self):
        """Initialize export manager."""
        self.exporters: Dict[ExportFormat, IExporter] = {}
        self.metrics = ExportMetrics()

        logger.info("Export manager initialized")

    def register_exporter(
        self,
        format: ExportFormat,
        exporter: IExporter,
    ) -> None:
        """Register an exporter for a format.

        Args:
            format: Export format
            exporter: Exporter instance
        """
        self.exporters[format] = exporter
        logger.info(f"Registered exporter for format: {format.value}")

    def get_exporter(self, format: ExportFormat) -> Optional[IExporter]:
        """Get exporter for a format.

        Args:
            format: Export format

        Returns:
            Exporter if available
        """
        return self.exporters.get(format)

    def is_format_supported(self, format: ExportFormat) -> bool:
        """Check if format is supported.

        Args:
            format: Export format

        Returns:
            True if format is supported
        """
        return format in self.exporters

    def get_supported_formats(self) -> List[ExportFormat]:
        """Get list of supported formats.

        Returns:
            List of supported formats
        """
        return list(self.exporters.keys())

    async def export(
        self,
        report: DomainReport,
        format: ExportFormat,
        output_path: Path,
        options: Optional[ExportOptions] = None,
    ) -> ExportResult:
        """Export report to specified format.

        Args:
            report: Report to export
            format: Export format
            output_path: Output file path
            options: Export options

        Returns:
            Export result

        Raises:
            UnsupportedFormatException: If format not supported
            ExportException: If export fails
        """
        logger.info(f"Exporting report {report.report_id} to {format.value}")

        # Check if format is supported
        if not self.is_format_supported(format):
            raise UnsupportedFormatException(
                f"Format '{format.value}' is not supported. "
                f"Supported formats: {[f.value for f in self.get_supported_formats()]}"
            )

        # Get exporter
        exporter = self.get_exporter(format)
        if not exporter:
            raise ExportException(f"No exporter available for {format.value}")

        # Use default options if not provided
        if options is None:
            options = ExportOptions()

        # Export
        try:
            result = await exporter.export(report, output_path, options)

            # Record metrics
            self.metrics.record_export(
                success=result.is_successful(),
                format=format,
                duration=result.export_duration,
                file_size=result.file_size,
            )

            return result

        except Exception as e:
            logger.error(f"Export failed: {e}")

            # Record failure
            self.metrics.record_export(
                success=False,
                format=format,
                duration=0.0,
                file_size=0,
            )

            raise

    async def export_request(
        self,
        report: DomainReport,
        request: ExportRequest,
    ) -> ExportResult:
        """Process export request.

        Args:
            report: Report to export
            request: Export request

        Returns:
            Export result
        """
        if request.output_path is None:
            raise ExportException("Output path not specified in request")

        return await self.export(
            report=report,
            format=request.format,
            output_path=request.output_path,
            options=request.options,
        )

    async def export_multiple(
        self,
        report: DomainReport,
        formats: List[ExportFormat],
        output_dir: Path,
        base_filename: str = "report",
        options: Optional[ExportOptions] = None,
    ) -> Dict[ExportFormat, ExportResult]:
        """Export report to multiple formats.

        Args:
            report: Report to export
            formats: List of export formats
            output_dir: Output directory
            base_filename: Base filename (without extension)
            options: Export options

        Returns:
            Dictionary mapping format to result
        """
        logger.info(f"Exporting to {len(formats)} formats")

        results = {}

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export to each format
        for format in formats:
            try:
                # Get exporter to determine extension
                exporter = self.get_exporter(format)
                if not exporter:
                    logger.warning(f"No exporter for {format.value}, skipping")
                    continue

                # Build output path
                extension = exporter.get_default_extension()
                output_path = output_dir / f"{base_filename}{extension}"

                # Export
                result = await self.export(
                    report=report,
                    format=format,
                    output_path=output_path,
                    options=options,
                )

                results[format] = result

                if result.is_successful():
                    logger.info(f"Exported to {format.value}: {output_path}")
                else:
                    logger.error(
                        f"Failed to export to {format.value}: {result.error_message}"
                    )

            except Exception as e:
                logger.error(f"Error exporting to {format.value}: {e}")

        logger.info(
            f"Batch export completed: {len(results)}/{len(formats)} successful"
        )

        return results

    def get_metrics(self) -> ExportMetrics:
        """Get export metrics.

        Returns:
            Export metrics
        """
        return self.metrics

    def get_metrics_summary(self) -> Dict[str, any]:
        """Get metrics summary.

        Returns:
            Dictionary with metrics summary
        """
        return {
            "total_exports": self.metrics.total_exports,
            "successful_exports": self.metrics.successful_exports,
            "failed_exports": self.metrics.failed_exports,
            "success_rate": self.metrics.get_success_rate(),
            "average_duration": self.metrics.average_duration,
            "total_size_mb": self.metrics.get_total_size_mb(),
            "exports_by_format": self.metrics.exports_by_format,
        }

    def reset_metrics(self) -> None:
        """Reset export metrics."""
        self.metrics = ExportMetrics()
        logger.info("Export metrics reset")


def create_default_export_manager() -> ExportManager:
    """Create export manager with default exporters.

    Returns:
        Configured export manager
    """
    from src.infrastructure.exporters.html_exporter import HTMLExporter
    from src.infrastructure.exporters.markdown_exporter import MarkdownExporter
    from src.infrastructure.exporters.pdf_exporter import PDFExporter

    manager = ExportManager()

    # Register exporters
    manager.register_exporter(ExportFormat.MARKDOWN, MarkdownExporter())
    manager.register_exporter(ExportFormat.HTML, HTMLExporter())
    manager.register_exporter(ExportFormat.PDF, PDFExporter())

    logger.info("Created export manager with default exporters")

    return manager
