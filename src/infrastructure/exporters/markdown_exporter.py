"""Markdown exporter implementation."""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List

from src.domain.export.exceptions import ExportException, FileWriteException
from src.domain.export.exporter import IExporter
from src.domain.export.models import (
    ExportFormat,
    ExportOptions,
    ExportResult,
    ExportStatus,
    TableOfContents,
)
from src.domain.models.report import DomainReport, ReportSection

logger = logging.getLogger(__name__)


class MarkdownExporter(IExporter):
    """Export reports to Markdown format.

    Features:
    - GitHub Flavored Markdown (GFM)
    - Table of contents
    - Metadata header
    - Section hierarchy
    - Code blocks with syntax highlighting
    - Tables
    - Links and anchors
    """

    def __init__(self):
        """Initialize Markdown exporter."""
        self.supported_formats = ["markdown", "md"]

    async def export(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> ExportResult:
        """Export report to Markdown.

        Args:
            report: Report to export
            output_path: Output file path
            options: Export options

        Returns:
            Export result
        """
        logger.info(f"Exporting report to Markdown: {output_path}")

        start_time = time.time()
        result = ExportResult(
            format=ExportFormat.MARKDOWN,
            status=ExportStatus.IN_PROGRESS,
        )

        try:
            # Validate options
            if not self.validate_options(options):
                raise ExportException("Invalid export options")

            # Ensure output path has correct extension
            if not output_path.suffix:
                output_path = output_path.with_suffix(".md")

            # Generate Markdown content
            markdown_content = self._generate_markdown(report, options)

            # Write to file
            self._write_file(output_path, markdown_content)

            # Calculate file size
            file_size = output_path.stat().st_size
            duration = time.time() - start_time

            # Mark as completed
            result.mark_completed(output_path, file_size, duration)

            logger.info(
                f"Markdown export completed: {file_size} bytes, {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Markdown export failed: {e}")
            result.mark_failed(str(e))
            return result

    def _generate_markdown(
        self,
        report: DomainReport,
        options: ExportOptions,
    ) -> str:
        """Generate Markdown content.

        Args:
            report: Report to convert
            options: Export options

        Returns:
            Markdown content
        """
        lines = []

        # Title
        lines.append(f"# {report.report_title}\n")

        # Metadata
        if options.include_metadata:
            lines.append(self._generate_metadata(report))

        # Table of Contents
        if options.include_toc:
            toc = self._generate_toc(report, options)
            lines.append(toc.to_markdown())
            lines.append("\n---\n")

        # Sections
        sections = report.get_all_sections()
        for section in sections:
            section_md = self._generate_section(section, options)
            lines.append(section_md)
            lines.append("\n")

        # Statistics
        if options.include_statistics:
            lines.append(self._generate_statistics(report))

        return "\n".join(lines)

    def _generate_metadata(self, report: DomainReport) -> str:
        """Generate metadata section.

        Args:
            report: Report

        Returns:
            Markdown metadata
        """
        metadata_lines = [
            "## Metadata\n",
            f"- **Report ID**: {report.report_id}",
            f"- **Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **Quality Score**: {report.quality_score:.2f}/100",
            f"- **Completeness**: {report.completeness_score:.2f}%",
            f"- **Total Sections**: {report.get_section_count()}",
            "\n",
        ]

        return "\n".join(metadata_lines)

    def _generate_toc(
        self,
        report: DomainReport,
        options: ExportOptions,
    ) -> TableOfContents:
        """Generate table of contents.

        Args:
            report: Report
            options: Export options

        Returns:
            Table of contents
        """
        toc = TableOfContents(
            max_depth=3,
            include_page_numbers=False,  # Markdown doesn't have pages
        )

        sections = report.get_all_sections()
        for section in sections:
            anchor = self._create_anchor(section.section_title)
            toc.add_entry(
                title=f"{section.section_number} {section.section_title}",
                level=section.hierarchy_level + 1,
                anchor=anchor,
            )

        return toc

    def _generate_section(
        self,
        section: ReportSection,
        options: ExportOptions,
    ) -> str:
        """Generate Markdown for a section.

        Args:
            section: Report section
            options: Export options

        Returns:
            Markdown section
        """
        lines = []

        # Section heading
        heading_level = section.hierarchy_level + 2  # H2 and below
        heading_prefix = "#" * heading_level

        title = f"{section.section_number} {section.section_title}"
        anchor = self._create_anchor(section.section_title)

        lines.append(f'{heading_prefix} {title} {{#{anchor}}}\n')

        # Section content
        content_items = section.get_content()
        for item in content_items:
            if isinstance(item, dict):
                content_md = self._format_content_item(item, options)
                lines.append(content_md)
            else:
                lines.append(str(item))

        return "\n".join(lines)

    def _format_content_item(
        self,
        item: dict,
        options: ExportOptions,
    ) -> str:
        """Format a content item.

        Args:
            item: Content item
            options: Export options

        Returns:
            Formatted content
        """
        content_type = item.get("type", "text")
        text = item.get("text", "")

        if content_type == "code":
            language = item.get("language", "")
            return f"```{language}\n{text}\n```\n"

        elif content_type == "table":
            return self._format_table(item.get("data", []))

        elif content_type == "quote":
            # Blockquote
            lines = text.split("\n")
            return "\n".join(f"> {line}" for line in lines) + "\n"

        else:
            # Regular text
            return text + "\n"

    def _format_table(self, data: List[List[str]]) -> str:
        """Format table in Markdown.

        Args:
            data: Table data (rows of columns)

        Returns:
            Markdown table
        """
        if not data or len(data) < 2:
            return ""

        lines = []

        # Header row
        header = data[0]
        lines.append("| " + " | ".join(header) + " |")

        # Separator
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")

        # Data rows
        for row in data[1:]:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines) + "\n"

    def _generate_statistics(self, report: DomainReport) -> str:
        """Generate statistics section.

        Args:
            report: Report

        Returns:
            Markdown statistics
        """
        stats_lines = [
            "\n---\n",
            "## Report Statistics\n",
            f"- **Total Sections**: {report.get_section_count()}",
            f"- **Quality Score**: {report.quality_score:.2f}/100",
            f"- **Completeness Score**: {report.completeness_score:.2f}%",
        ]

        # Add bibliography stats if available
        if "bibliography" in report.metadata:
            bib_stats = report.metadata["bibliography"]
            stats_lines.extend([
                f"- **Total Citations**: {bib_stats.get('total_citations', 0)}",
                f"- **Used Citations**: {bib_stats.get('used_citations', 0)}",
            ])

        return "\n".join(stats_lines)

    def _create_anchor(self, title: str) -> str:
        """Create anchor ID from title.

        Args:
            title: Section title

        Returns:
            Anchor ID (lowercase, hyphenated)
        """
        # Convert to lowercase, replace spaces with hyphens
        anchor = title.lower()
        anchor = anchor.replace(" ", "-")

        # Remove special characters
        anchor = "".join(c for c in anchor if c.isalnum() or c == "-")

        return anchor

    def _write_file(self, output_path: Path, content: str) -> None:
        """Write content to file.

        Args:
            output_path: Output file path
            content: Content to write

        Raises:
            FileWriteException: If write fails
        """
        try:
            # Create parent directories
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            raise FileWriteException(f"Failed to write file: {e}")

    def supports_format(self, format_name: str) -> bool:
        """Check if format is supported."""
        return format_name.lower() in self.supported_formats

    def get_supported_formats(self) -> list[str]:
        """Get supported formats."""
        return self.supported_formats.copy()

    def get_default_extension(self) -> str:
        """Get default file extension."""
        return ".md"

    def validate_options(self, options: ExportOptions) -> bool:
        """Validate export options."""
        # Markdown has minimal requirements
        return True
