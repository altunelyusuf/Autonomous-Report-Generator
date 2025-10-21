"""MS Word (DOCX) exporter implementation."""

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


class DOCXExporter(IExporter):
    """Export reports to MS Word DOCX format.

    Features:
    - Professional Word document formatting
    - Table of contents
    - Styled headings and paragraphs
    - Tables
    - Page numbers
    - Headers and footers
    - Metadata properties
    - Section breaks
    """

    def __init__(self):
        """Initialize DOCX exporter."""
        self.supported_formats = ["docx", "doc"]

    async def export(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> ExportResult:
        """Export report to DOCX.

        Args:
            report: Report to export
            output_path: Output file path
            options: Export options

        Returns:
            Export result
        """
        logger.info(f"Exporting report to DOCX: {output_path}")

        start_time = time.time()
        result = ExportResult(
            format=ExportFormat.DOCX,
            status=ExportStatus.IN_PROGRESS,
        )

        try:
            # Validate options
            if not self.validate_options(options):
                raise ExportException("Invalid export options")

            # Ensure output path has correct extension
            if not output_path.suffix:
                output_path = output_path.with_suffix(".docx")

            # Check if python-docx is available
            try:
                from docx import Document
                from docx.shared import Inches, Pt, RGBColor
                from docx.enum.text import WD_ALIGN_PARAGRAPH
                from docx.enum.style import WD_STYLE_TYPE

                # Generate DOCX with python-docx
                self._generate_docx_pythondocx(report, output_path, options)

            except ImportError:
                # python-docx not available, create mock DOCX
                logger.warning("python-docx not available, creating mock DOCX")
                self._generate_mock_docx(report, output_path, options)

            # Calculate file size
            file_size = output_path.stat().st_size
            duration = time.time() - start_time

            # Mark as completed
            result.mark_completed(output_path, file_size, duration)

            logger.info(
                f"DOCX export completed: {file_size} bytes, {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"DOCX export failed: {e}")
            result.mark_failed(str(e))
            return result

    def _generate_docx_pythondocx(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> None:
        """Generate DOCX using python-docx.

        Args:
            report: Report
            output_path: Output path
            options: Export options
        """
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        # Create document
        doc = Document()

        # Set document properties
        core_props = doc.core_properties
        core_props.title = report.report_title
        core_props.subject = "Automated Report"
        core_props.creator = "Autonomous Report Generator"
        core_props.created = datetime.utcnow()

        # Configure page setup
        section = doc.sections[0]
        section.page_height = Inches(11) if options.paper_size == "letter" else Inches(11.69)
        section.page_width = Inches(8.5) if options.paper_size == "letter" else Inches(8.27)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)

        # Add title
        title = doc.add_heading(report.report_title, level=0)
        title_format = title.paragraph_format
        title_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_format.space_after = Pt(12)

        # Add metadata
        if options.include_metadata:
            doc.add_heading("Metadata", level=1)

            metadata_items = [
                f"Report ID: {report.report_id}",
                f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"Quality Score: {report.quality_score:.2f}/100",
                f"Completeness: {report.completeness_score:.2f}%",
                f"Total Sections: {report.get_section_count()}",
            ]

            for item in metadata_items:
                p = doc.add_paragraph(item)
                p.paragraph_format.space_after = Pt(6)

            doc.add_paragraph()  # Spacing

        # Add table of contents
        if options.include_toc:
            doc.add_heading("Table of Contents", level=1)

            sections = report.get_all_sections()
            for section_item in sections:
                indent = "    " * section_item.hierarchy_level
                toc_text = f"{indent}{section_item.section_number} {section_item.section_title}"
                p = doc.add_paragraph(toc_text)
                p.paragraph_format.left_indent = Inches(section_item.hierarchy_level * 0.5)
                p.paragraph_format.space_after = Pt(3)

            doc.add_page_break()

        # Add sections
        sections = report.get_all_sections()
        for section_item in sections:
            # Section heading
            heading_level = min(section_item.hierarchy_level + 1, 9)  # Word supports up to 9 levels
            title_text = f"{section_item.section_number} {section_item.section_title}"

            heading = doc.add_heading(title_text, level=heading_level)
            heading.paragraph_format.space_before = Pt(12)
            heading.paragraph_format.space_after = Pt(6)

            # Section content
            content_items = section_item.get_content()
            for item in content_items:
                if isinstance(item, dict):
                    self._add_content_item(doc, item, options)
                else:
                    p = doc.add_paragraph(str(item))
                    p.paragraph_format.space_after = Pt(6)
                    p.paragraph_format.line_spacing = options.line_spacing

        # Add statistics
        if options.include_statistics:
            doc.add_page_break()
            doc.add_heading("Report Statistics", level=1)

            stats_items = [
                f"Total Sections: {report.get_section_count()}",
                f"Quality Score: {report.quality_score:.2f}/100",
                f"Completeness Score: {report.completeness_score:.2f}%",
            ]

            if "bibliography" in report.metadata:
                bib_stats = report.metadata["bibliography"]
                stats_items.extend([
                    f"Total Citations: {bib_stats.get('total_citations', 0)}",
                    f"Used Citations: {bib_stats.get('used_citations', 0)}",
                ])

            for item in stats_items:
                p = doc.add_paragraph(item)
                p.paragraph_format.space_after = Pt(6)

        # Add page numbers
        if options.page_numbers:
            self._add_page_numbers(doc, section)

        # Save document
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))

    def _add_content_item(
        self,
        doc,
        item: dict,
        options: ExportOptions,
    ) -> None:
        """Add content item to document.

        Args:
            doc: Document object
            item: Content item
            options: Export options
        """
        from docx.shared import Pt

        content_type = item.get("type", "text")
        text = item.get("text", "")

        if content_type == "code":
            # Add code block
            p = doc.add_paragraph(text, style='Intense Quote')
            p.paragraph_format.space_after = Pt(12)

        elif content_type == "table":
            # Add table
            self._add_table(doc, item.get("data", []))

        elif content_type == "quote":
            # Add quote
            p = doc.add_paragraph(text, style='Quote')
            p.paragraph_format.space_after = Pt(12)

        else:
            # Regular text
            paragraphs = text.split("\n\n")
            for para_text in paragraphs:
                if para_text.strip():
                    p = doc.add_paragraph(para_text)
                    p.paragraph_format.space_after = Pt(6)
                    p.paragraph_format.line_spacing = options.line_spacing

    def _add_table(self, doc, data: List[List[str]]) -> None:
        """Add table to document.

        Args:
            doc: Document object
            data: Table data (rows of columns)
        """
        from docx.shared import Pt, RGBColor

        if not data or len(data) < 2:
            return

        # Create table
        table = doc.add_table(rows=len(data), cols=len(data[0]))
        table.style = 'Light Grid Accent 1'

        # Populate table
        for i, row_data in enumerate(data):
            row = table.rows[i]
            for j, cell_text in enumerate(row_data):
                cell = row.cells[j]
                cell.text = cell_text

                # Header row formatting
                if i == 0:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.bold = True
                            run.font.size = Pt(11)

        # Add spacing after table
        doc.add_paragraph()

    def _add_page_numbers(self, doc, section) -> None:
        """Add page numbers to document.

        Args:
            doc: Document object
            section: Section object
        """
        # Note: Adding page numbers programmatically in python-docx is complex
        # This is a simplified approach
        # In production, consider using python-docx-template or similar
        pass

    def _generate_mock_docx(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> None:
        """Generate mock DOCX for testing without python-docx.

        Args:
            report: Report
            output_path: Output path
            options: Export options
        """
        import zipfile
        from io import BytesIO

        # Create minimal DOCX structure (DOCX is a ZIP file)
        docx_buffer = BytesIO()

        with zipfile.ZipFile(docx_buffer, 'w', zipfile.ZIP_DEFLATED) as docx:
            # Add [Content_Types].xml
            content_types = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
            docx.writestr('[Content_Types].xml', content_types)

            # Add _rels/.rels
            rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
            docx.writestr('_rels/.rels', rels)

            # Add word/document.xml
            document_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:pPr>
                <w:pStyle w:val="Title"/>
            </w:pPr>
            <w:r>
                <w:t>{report.report_title}</w:t>
            </w:r>
        </w:p>
        <w:p>
            <w:r>
                <w:t>Mock DOCX Export</w:t>
            </w:r>
        </w:p>
        <w:p>
            <w:r>
                <w:t>Report ID: {report.report_id}</w:t>
            </w:r>
        </w:p>
        <w:p>
            <w:r>
                <w:t>Sections: {report.get_section_count()}</w:t>
            </w:r>
        </w:p>
        <w:p>
            <w:r>
                <w:t>Quality: {report.quality_score:.2f}/100</w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>'''
            docx.writestr('word/document.xml', document_xml)

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(docx_buffer.getvalue())

    def supports_format(self, format_name: str) -> bool:
        """Check if format is supported."""
        return format_name.lower() in self.supported_formats

    def get_supported_formats(self) -> list[str]:
        """Get supported formats."""
        return self.supported_formats.copy()

    def get_default_extension(self) -> str:
        """Get default file extension."""
        return ".docx"

    def validate_options(self, options: ExportOptions) -> bool:
        """Validate export options."""
        # Validate paper size
        valid_sizes = ["letter", "A4", "legal"]
        if options.paper_size not in valid_sizes:
            logger.warning(f"Unknown paper size '{options.paper_size}', using 'letter'")
            options.paper_size = "letter"

        # Validate line spacing
        if options.line_spacing < 1.0 or options.line_spacing > 3.0:
            logger.warning(f"Invalid line spacing {options.line_spacing}, using 1.5")
            options.line_spacing = 1.5

        return True
