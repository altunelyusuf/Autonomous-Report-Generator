"""Base exporter interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from src.domain.export.models import ExportOptions, ExportResult
from src.domain.models.report import DomainReport


class IExporter(ABC):
    """Interface for report exporters.

    Defines the contract for exporting reports to various formats.
    """

    @abstractmethod
    async def export(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> ExportResult:
        """Export report to file.

        Args:
            report: Report to export
            output_path: Output file path
            options: Export options

        Returns:
            Export result

        Raises:
            ExportException: If export fails
        """
        pass

    @abstractmethod
    def supports_format(self, format_name: str) -> bool:
        """Check if exporter supports a format.

        Args:
            format_name: Format name

        Returns:
            True if format is supported
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """Get list of supported formats.

        Returns:
            List of format names
        """
        pass

    @abstractmethod
    def get_default_extension(self) -> str:
        """Get default file extension.

        Returns:
            File extension (e.g., '.md', '.html')
        """
        pass

    @abstractmethod
    def validate_options(self, options: ExportOptions) -> bool:
        """Validate export options.

        Args:
            options: Export options

        Returns:
            True if options are valid
        """
        pass
