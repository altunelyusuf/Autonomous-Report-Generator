"""HTML exporter implementation."""

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


class HTMLExporter(IExporter):
    """Export reports to HTML format.

    Features:
    - Responsive HTML5
    - CSS styling (light/dark themes)
    - Table of contents with navigation
    - Syntax highlighting
    - Print-friendly styles
    - Accessible markup
    """

    def __init__(self):
        """Initialize HTML exporter."""
        self.supported_formats = ["html", "htm"]

    async def export(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> ExportResult:
        """Export report to HTML.

        Args:
            report: Report to export
            output_path: Output file path
            options: Export options

        Returns:
            Export result
        """
        logger.info(f"Exporting report to HTML: {output_path}")

        start_time = time.time()
        result = ExportResult(
            format=ExportFormat.HTML,
            status=ExportStatus.IN_PROGRESS,
        )

        try:
            # Validate options
            if not self.validate_options(options):
                raise ExportException("Invalid export options")

            # Ensure output path has correct extension
            if not output_path.suffix:
                output_path = output_path.with_suffix(".html")

            # Generate HTML content
            html_content = self._generate_html(report, options)

            # Write to file
            self._write_file(output_path, html_content)

            # Calculate file size
            file_size = output_path.stat().st_size
            duration = time.time() - start_time

            # Mark as completed
            result.mark_completed(output_path, file_size, duration)

            logger.info(
                f"HTML export completed: {file_size} bytes, {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"HTML export failed: {e}")
            result.mark_failed(str(e))
            return result

    def _generate_html(
        self,
        report: DomainReport,
        options: ExportOptions,
    ) -> str:
        """Generate HTML content.

        Args:
            report: Report to convert
            options: Export options

        Returns:
            HTML content
        """
        parts = []

        # HTML header
        parts.append(self._generate_header(report, options))

        # Body start
        parts.append('<body>')

        # Container
        parts.append('<div class="container">')

        # Title
        parts.append(f'<h1 class="report-title">{self._escape_html(report.report_title)}</h1>')

        # Metadata
        if options.include_metadata:
            parts.append(self._generate_metadata(report))

        # Table of Contents
        if options.include_toc:
            toc = self._generate_toc(report, options)
            parts.append(toc.to_html())

        # Main content
        parts.append('<main class="report-content">')

        # Sections
        sections = report.get_all_sections()
        for section in sections:
            section_html = self._generate_section(section, options)
            parts.append(section_html)

        parts.append('</main>')

        # Statistics
        if options.include_statistics:
            parts.append(self._generate_statistics(report))

        # Footer
        parts.append(self._generate_footer())

        # Container end
        parts.append('</div>')

        # Body end
        parts.append('</body>')
        parts.append('</html>')

        return "\n".join(parts)

    def _generate_header(
        self,
        report: DomainReport,
        options: ExportOptions,
    ) -> str:
        """Generate HTML header.

        Args:
            report: Report
            options: Export options

        Returns:
            HTML header
        """
        css = options.custom_css or self._get_default_css(options.theme)

        header = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="generator" content="Autonomous Report Generator">
    <title>{self._escape_html(report.report_title)}</title>
    <style>
{css}
    </style>
</head>'''

        return header

    def _get_default_css(self, theme: str = "light") -> str:
        """Get default CSS styles.

        Args:
            theme: Theme name (light/dark)

        Returns:
            CSS content
        """
        if theme == "dark":
            bg_color = "#1e1e1e"
            text_color = "#e0e0e0"
            heading_color = "#ffffff"
            link_color = "#66b3ff"
            border_color = "#444444"
            toc_bg = "#2a2a2a"
        else:
            bg_color = "#ffffff"
            text_color = "#333333"
            heading_color = "#1a1a1a"
            link_color = "#0066cc"
            border_color = "#e0e0e0"
            toc_bg = "#f5f5f5"

        css = f'''
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: {text_color};
            background-color: {bg_color};
            padding: 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: {bg_color};
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .report-title {{
            color: {heading_color};
            font-size: 2.5em;
            margin-bottom: 20px;
            border-bottom: 3px solid {link_color};
            padding-bottom: 10px;
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: {heading_color};
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}

        h2 {{
            font-size: 1.8em;
            border-bottom: 2px solid {border_color};
            padding-bottom: 5px;
        }}

        h3 {{
            font-size: 1.4em;
        }}

        h4 {{
            font-size: 1.2em;
        }}

        p {{
            margin-bottom: 1em;
        }}

        a {{
            color: {link_color};
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        .metadata {{
            background: {toc_bg};
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid {link_color};
        }}

        .metadata h2 {{
            margin-top: 0;
        }}

        .metadata ul {{
            list-style: none;
            padding-left: 0;
        }}

        .metadata li {{
            margin: 5px 0;
        }}

        .table-of-contents {{
            background: {toc_bg};
            padding: 20px;
            margin: 30px 0;
            border-radius: 5px;
        }}

        .table-of-contents h2 {{
            margin-top: 0;
            border-bottom: none;
        }}

        .table-of-contents ul {{
            list-style: none;
            padding-left: 0;
        }}

        .table-of-contents li {{
            margin: 8px 0;
            padding-left: 20px;
        }}

        .table-of-contents ul ul {{
            margin-left: 20px;
            margin-top: 5px;
        }}

        .report-content {{
            margin: 30px 0;
        }}

        .section {{
            margin: 30px 0;
        }}

        code {{
            background: {toc_bg};
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}

        pre {{
            background: {toc_bg};
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 15px 0;
        }}

        pre code {{
            background: none;
            padding: 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid {border_color};
        }}

        th {{
            background: {toc_bg};
            font-weight: 600;
        }}

        blockquote {{
            border-left: 4px solid {link_color};
            padding-left: 20px;
            margin: 20px 0;
            font-style: italic;
            color: {text_color};
            opacity: 0.8;
        }}

        .statistics {{
            background: {toc_bg};
            padding: 20px;
            margin: 30px 0;
            border-radius: 5px;
        }}

        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid {border_color};
            text-align: center;
            font-size: 0.9em;
            color: {text_color};
            opacity: 0.7;
        }}

        @media print {{
            body {{
                background: white;
                color: black;
            }}

            .container {{
                box-shadow: none;
                padding: 0;
            }}

            .table-of-contents {{
                page-break-after: always;
            }}

            .section {{
                page-break-inside: avoid;
            }}
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
            }}

            .report-title {{
                font-size: 2em;
            }}

            h2 {{
                font-size: 1.5em;
            }}
        }}
        '''

        return css

    def _generate_metadata(self, report: DomainReport) -> str:
        """Generate metadata section.

        Args:
            report: Report

        Returns:
            HTML metadata
        """
        metadata_html = f'''
        <div class="metadata">
            <h2>Metadata</h2>
            <ul>
                <li><strong>Report ID:</strong> {report.report_id}</li>
                <li><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
                <li><strong>Quality Score:</strong> {report.quality_score:.2f}/100</li>
                <li><strong>Completeness:</strong> {report.completeness_score:.2f}%</li>
                <li><strong>Total Sections:</strong> {report.get_section_count()}</li>
            </ul>
        </div>
        '''

        return metadata_html

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
            include_page_numbers=False,
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
        """Generate HTML for a section.

        Args:
            section: Report section
            options: Export options

        Returns:
            HTML section
        """
        heading_level = min(section.hierarchy_level + 2, 6)  # H2-H6
        title = f"{section.section_number} {section.section_title}"
        anchor = self._create_anchor(section.section_title)

        section_parts = [
            f'<section class="section" id="{anchor}">',
            f'<h{heading_level}>{self._escape_html(title)}</h{heading_level}>',
        ]

        # Section content
        content_items = section.get_content()
        for item in content_items:
            if isinstance(item, dict):
                content_html = self._format_content_item(item, options)
                section_parts.append(content_html)
            else:
                section_parts.append(f'<p>{self._escape_html(str(item))}</p>')

        section_parts.append('</section>')

        return "\n".join(section_parts)

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
            Formatted HTML
        """
        content_type = item.get("type", "text")
        text = item.get("text", "")

        if content_type == "code":
            language = item.get("language", "")
            return f'<pre><code class="language-{language}">{self._escape_html(text)}</code></pre>'

        elif content_type == "table":
            return self._format_table(item.get("data", []))

        elif content_type == "quote":
            return f'<blockquote>{self._escape_html(text)}</blockquote>'

        else:
            # Regular text - preserve line breaks
            paragraphs = text.split("\n\n")
            html_parts = []
            for para in paragraphs:
                if para.strip():
                    html_parts.append(f'<p>{self._escape_html(para)}</p>')
            return "\n".join(html_parts)

    def _format_table(self, data: List[List[str]]) -> str:
        """Format table in HTML.

        Args:
            data: Table data (rows of columns)

        Returns:
            HTML table
        """
        if not data or len(data) < 2:
            return ""

        table_parts = ['<table>']

        # Header row
        table_parts.append('<thead><tr>')
        for cell in data[0]:
            table_parts.append(f'<th>{self._escape_html(cell)}</th>')
        table_parts.append('</tr></thead>')

        # Data rows
        table_parts.append('<tbody>')
        for row in data[1:]:
            table_parts.append('<tr>')
            for cell in row:
                table_parts.append(f'<td>{self._escape_html(cell)}</td>')
            table_parts.append('</tr>')
        table_parts.append('</tbody>')

        table_parts.append('</table>')

        return "\n".join(table_parts)

    def _generate_statistics(self, report: DomainReport) -> str:
        """Generate statistics section.

        Args:
            report: Report

        Returns:
            HTML statistics
        """
        stats_parts = [
            '<div class="statistics">',
            '<h2>Report Statistics</h2>',
            '<ul>',
            f'<li><strong>Total Sections:</strong> {report.get_section_count()}</li>',
            f'<li><strong>Quality Score:</strong> {report.quality_score:.2f}/100</li>',
            f'<li><strong>Completeness Score:</strong> {report.completeness_score:.2f}%</li>',
        ]

        # Add bibliography stats if available
        if "bibliography" in report.metadata:
            bib_stats = report.metadata["bibliography"]
            stats_parts.extend([
                f'<li><strong>Total Citations:</strong> {bib_stats.get("total_citations", 0)}</li>',
                f'<li><strong>Used Citations:</strong> {bib_stats.get("used_citations", 0)}</li>',
            ])

        stats_parts.extend([
            '</ul>',
            '</div>',
        ])

        return "\n".join(stats_parts)

    def _generate_footer(self) -> str:
        """Generate footer.

        Returns:
            HTML footer
        """
        return f'''
        <footer class="footer">
            <p>Generated by Autonomous Report Generator on {datetime.utcnow().strftime('%Y-%m-%d')}</p>
        </footer>
        '''

    def _create_anchor(self, title: str) -> str:
        """Create anchor ID from title.

        Args:
            title: Section title

        Returns:
            Anchor ID
        """
        anchor = title.lower()
        anchor = anchor.replace(" ", "-")
        anchor = "".join(c for c in anchor if c.isalnum() or c == "-")
        return anchor

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text

    def _write_file(self, output_path: Path, content: str) -> None:
        """Write content to file.

        Args:
            output_path: Output file path
            content: Content to write

        Raises:
            FileWriteException: If write fails
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

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
        return ".html"

    def validate_options(self, options: ExportOptions) -> bool:
        """Validate export options."""
        # Validate theme
        if options.theme not in ["light", "dark"]:
            logger.warning(f"Unknown theme '{options.theme}', using 'light'")
            options.theme = "light"

        return True
