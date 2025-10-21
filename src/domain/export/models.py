"""Domain models for report export."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4


class ExportFormat(str, Enum):
    """Export format types."""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    LATEX = "latex"
    JSON = "json"


class ExportStatus(str, Enum):
    """Export operation status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExportOptions:
    """Options for export operations.

    Attributes:
        include_toc: Include table of contents
        include_metadata: Include report metadata
        include_statistics: Include generation statistics
        page_numbers: Add page numbers (PDF/DOCX)
        syntax_highlighting: Enable code syntax highlighting
        theme: Visual theme (light/dark)
        font_family: Font family to use
        font_size: Base font size
        line_spacing: Line spacing
        margin_size: Page margins (PDF/DOCX)
        paper_size: Paper size (PDF/DOCX)
        custom_css: Custom CSS (HTML)
        custom_template: Custom template path
        metadata: Additional metadata
    """

    include_toc: bool = True
    include_metadata: bool = True
    include_statistics: bool = True
    page_numbers: bool = True
    syntax_highlighting: bool = True
    theme: str = "light"
    font_family: str = "Arial"
    font_size: int = 11
    line_spacing: float = 1.5
    margin_size: str = "1in"
    paper_size: str = "letter"
    custom_css: Optional[str] = None
    custom_template: Optional[Path] = None
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class ExportRequest:
    """Request for report export.

    Attributes:
        request_id: Unique request identifier
        report_id: ID of report to export
        format: Export format
        options: Export options
        output_path: Output file path
        created_at: Request creation timestamp
    """

    request_id: UUID = field(default_factory=uuid4)
    report_id: UUID = field(default_factory=uuid4)
    format: ExportFormat = ExportFormat.MARKDOWN
    options: ExportOptions = field(default_factory=ExportOptions)
    output_path: Optional[Path] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExportResult:
    """Result of export operation.

    Attributes:
        result_id: Unique result identifier
        request_id: Associated request ID
        status: Export status
        format: Export format used
        output_path: Path to exported file
        file_size: Size of exported file in bytes
        export_duration: Export duration in seconds
        error_message: Error message if failed
        warnings: List of warnings
        metadata: Additional metadata
        completed_at: Completion timestamp
    """

    result_id: UUID = field(default_factory=uuid4)
    request_id: UUID = field(default_factory=uuid4)
    status: ExportStatus = ExportStatus.PENDING
    format: ExportFormat = ExportFormat.MARKDOWN
    output_path: Optional[Path] = None
    file_size: int = 0
    export_duration: float = 0.0
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)
    completed_at: Optional[datetime] = None

    def add_warning(self, warning: str) -> None:
        """Add a warning message.

        Args:
            warning: Warning message
        """
        self.warnings.append(warning)

    def mark_completed(self, output_path: Path, file_size: int, duration: float) -> None:
        """Mark export as completed.

        Args:
            output_path: Path to exported file
            file_size: File size in bytes
            duration: Export duration in seconds
        """
        self.status = ExportStatus.COMPLETED
        self.output_path = output_path
        self.file_size = file_size
        self.export_duration = duration
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        """Mark export as failed.

        Args:
            error: Error message
        """
        self.status = ExportStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()

    def is_successful(self) -> bool:
        """Check if export was successful.

        Returns:
            True if export completed successfully
        """
        return self.status == ExportStatus.COMPLETED

    def get_file_size_mb(self) -> float:
        """Get file size in megabytes.

        Returns:
            File size in MB
        """
        return self.file_size / (1024 * 1024)


@dataclass
class ExportMetrics:
    """Metrics for export operations.

    Attributes:
        total_exports: Total export requests
        successful_exports: Successful exports
        failed_exports: Failed exports
        exports_by_format: Exports by format
        average_duration: Average export duration
        total_size: Total size of exports
    """

    total_exports: int = 0
    successful_exports: int = 0
    failed_exports: int = 0
    exports_by_format: Dict[str, int] = field(default_factory=dict)
    average_duration: float = 0.0
    total_size: int = 0

    def record_export(
        self,
        success: bool,
        format: ExportFormat,
        duration: float,
        file_size: int = 0,
    ) -> None:
        """Record an export operation.

        Args:
            success: Whether export succeeded
            format: Export format
            duration: Export duration in seconds
            file_size: File size in bytes
        """
        self.total_exports += 1

        if success:
            self.successful_exports += 1
            self.total_size += file_size

            # Update average duration
            n = self.successful_exports
            self.average_duration = (
                self.average_duration * (n - 1) + duration
            ) / n

            # Track format usage
            format_key = format.value
            self.exports_by_format[format_key] = (
                self.exports_by_format.get(format_key, 0) + 1
            )
        else:
            self.failed_exports += 1

    def get_success_rate(self) -> float:
        """Calculate success rate.

        Returns:
            Success rate (0.0 to 1.0)
        """
        if self.total_exports == 0:
            return 0.0
        return self.successful_exports / self.total_exports

    def get_total_size_mb(self) -> float:
        """Get total size in megabytes.

        Returns:
            Total size in MB
        """
        return self.total_size / (1024 * 1024)


@dataclass
class TableOfContents:
    """Table of contents for exported report.

    Attributes:
        entries: List of TOC entries
        max_depth: Maximum hierarchy depth to include
        include_page_numbers: Include page numbers
    """

    entries: List[Dict[str, any]] = field(default_factory=list)
    max_depth: int = 3
    include_page_numbers: bool = True

    def add_entry(
        self,
        title: str,
        level: int,
        page_number: Optional[int] = None,
        anchor: Optional[str] = None,
    ) -> None:
        """Add a TOC entry.

        Args:
            title: Section title
            level: Hierarchy level
            page_number: Page number (for PDF)
            anchor: HTML anchor (for HTML)
        """
        if level <= self.max_depth:
            self.entries.append({
                "title": title,
                "level": level,
                "page_number": page_number,
                "anchor": anchor,
            })

    def get_entry_count(self) -> int:
        """Get number of entries.

        Returns:
            Entry count
        """
        return len(self.entries)

    def to_markdown(self) -> str:
        """Generate Markdown TOC.

        Returns:
            Markdown formatted TOC
        """
        lines = ["## Table of Contents\n"]

        for entry in self.entries:
            indent = "  " * (entry["level"] - 1)
            title = entry["title"]

            if entry.get("anchor"):
                lines.append(f"{indent}- [{title}](#{entry['anchor']})")
            else:
                lines.append(f"{indent}- {title}")

        return "\n".join(lines)

    def to_html(self) -> str:
        """Generate HTML TOC.

        Returns:
            HTML formatted TOC
        """
        lines = ['<nav class="table-of-contents">', '<h2>Table of Contents</h2>', '<ul>']

        current_level = 0
        for entry in self.entries:
            level = entry["level"]

            # Open/close nested lists
            while current_level < level:
                lines.append("<ul>")
                current_level += 1
            while current_level > level:
                lines.append("</ul>")
                current_level -= 1

            title = entry["title"]
            anchor = entry.get("anchor", "")

            if anchor:
                lines.append(f'<li><a href="#{anchor}">{title}</a></li>')
            else:
                lines.append(f"<li>{title}</li>")

        # Close remaining lists
        while current_level > 0:
            lines.append("</ul>")
            current_level -= 1

        lines.append("</ul>")
        lines.append("</nav>")

        return "\n".join(lines)
