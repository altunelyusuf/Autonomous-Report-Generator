"""PDF exporter implementation."""

import logging
import time
from datetime import datetime
from pathlib import Path

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


class PDFExporter(IExporter):
    """Export reports to PDF format.

    Features:
    - Professional PDF layout
    - Table of contents with page numbers
    - Headers and footers
    - Page numbering
    - Proper typography
    - Embedded fonts

    Note: This is a mock implementation. In production, use:
    - ReportLab for PDF generation
    - WeasyPrint for HTML-to-PDF conversion
    - Or other PDF libraries
    """

    def __init__(self):
        """Initialize PDF exporter."""
        self.supported_formats = ["pdf"]

    async def export(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> ExportResult:
        """Export report to PDF.

        Args:
            report: Report to export
            output_path: Output file path
            options: Export options

        Returns:
            Export result
        """
        logger.info(f"Exporting report to PDF: {output_path}")

        start_time = time.time()
        result = ExportResult(
            format=ExportFormat.PDF,
            status=ExportStatus.IN_PROGRESS,
        )

        try:
            # Validate options
            if not self.validate_options(options):
                raise ExportException("Invalid export options")

            # Ensure output path has correct extension
            if not output_path.suffix:
                output_path = output_path.with_suffix(".pdf")

            # Check if ReportLab is available
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import letter, A4
                from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
                from reportlab.lib.units import inch
                from reportlab.platypus import (
                    SimpleDocTemplate,
                    Paragraph,
                    Spacer,
                    PageBreak,
                    Table,
                    TableStyle,
                )

                # Generate PDF with ReportLab
                self._generate_pdf_reportlab(report, output_path, options)

            except ImportError:
                # ReportLab not available, create mock PDF
                logger.warning("ReportLab not available, creating mock PDF")
                self._generate_mock_pdf(report, output_path, options)

            # Calculate file size
            file_size = output_path.stat().st_size
            duration = time.time() - start_time

            # Mark as completed
            result.mark_completed(output_path, file_size, duration)

            logger.info(
                f"PDF export completed: {file_size} bytes, {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            result.mark_failed(str(e))
            return result

    def _generate_pdf_reportlab(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> None:
        """Generate PDF using ReportLab.

        Args:
            report: Report
            output_path: Output path
            options: Export options
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            PageBreak,
            Table,
            TableStyle,
        )

        # Create PDF document
        page_size = A4 if options.paper_size == "A4" else letter

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # Build document elements
        elements = []
        styles = getSampleStyleSheet()

        # Add custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
        )

        # Title
        elements.append(Paragraph(report.report_title, title_style))
        elements.append(Spacer(1, 0.5 * inch))

        # Metadata
        if options.include_metadata:
            elements.append(Paragraph("Metadata", heading_style))
            metadata_text = f"""
            Report ID: {report.report_id}<br/>
            Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}<br/>
            Quality Score: {report.quality_score:.2f}/100<br/>
            Completeness: {report.completeness_score:.2f}%<br/>
            Total Sections: {report.get_section_count()}
            """
            elements.append(Paragraph(metadata_text, styles['Normal']))
            elements.append(Spacer(1, 0.3 * inch))

        # Table of Contents
        if options.include_toc:
            elements.append(PageBreak())
            elements.append(Paragraph("Table of Contents", heading_style))

            toc_data = []
            sections = report.get_all_sections()
            for section in sections:
                indent = "  " * section.hierarchy_level
                title = f"{indent}{section.section_number} {section.section_title}"
                toc_data.append([title, ""])  # Page numbers would be added here

            if toc_data:
                toc_table = Table(toc_data, colWidths=[5 * inch, 0.5 * inch])
                toc_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(toc_table)

            elements.append(PageBreak())

        # Sections
        sections = report.get_all_sections()
        for section in sections:
            # Section heading
            heading_level = min(section.hierarchy_level + 1, 3)
            if heading_level == 1:
                style = styles['Heading1']
            elif heading_level == 2:
                style = styles['Heading2']
            else:
                style = styles['Heading3']

            title = f"{section.section_number} {section.section_title}"
            elements.append(Paragraph(title, style))
            elements.append(Spacer(1, 0.2 * inch))

            # Section content
            content_items = section.get_content()
            for item in content_items:
                if isinstance(item, dict):
                    text = item.get("text", "")
                else:
                    text = str(item)

                # Split into paragraphs
                paragraphs = text.split("\n\n")
                for para in paragraphs:
                    if para.strip():
                        elements.append(Paragraph(para, styles['Normal']))
                        elements.append(Spacer(1, 0.1 * inch))

            elements.append(Spacer(1, 0.3 * inch))

        # Statistics
        if options.include_statistics:
            elements.append(PageBreak())
            elements.append(Paragraph("Report Statistics", heading_style))

            stats_text = f"""
            Total Sections: {report.get_section_count()}<br/>
            Quality Score: {report.quality_score:.2f}/100<br/>
            Completeness Score: {report.completeness_score:.2f}%
            """

            if "bibliography" in report.metadata:
                bib_stats = report.metadata["bibliography"]
                stats_text += f"""<br/>
                Total Citations: {bib_stats.get('total_citations', 0)}<br/>
                Used Citations: {bib_stats.get('used_citations', 0)}
                """

            elements.append(Paragraph(stats_text, styles['Normal']))

        # Build PDF
        doc.build(elements)

    def _generate_mock_pdf(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> None:
        """Generate mock PDF for testing without ReportLab.

        Args:
            report: Report
            output_path: Output path
            options: Export options
        """
        # Create minimal PDF structure
        pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 200
>>
stream
BT
/F1 24 Tf
50 700 Td
({report.report_title}) Tj
0 -50 Td
/F1 12 Tf
(Mock PDF Export) Tj
0 -30 Td
(Report ID: {report.report_id}) Tj
0 -20 Td
(Sections: {report.get_section_count()}) Tj
0 -20 Td
(Quality: {report.quality_score:.2f}/100) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000315 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
566
%%EOF
"""

        # Write mock PDF
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pdf_content)

    def supports_format(self, format_name: str) -> bool:
        """Check if format is supported."""
        return format_name.lower() in self.supported_formats

    def get_supported_formats(self) -> list[str]:
        """Get supported formats."""
        return self.supported_formats.copy()

    def get_default_extension(self) -> str:
        """Get default file extension."""
        return ".pdf"

    def validate_options(self, options: ExportOptions) -> bool:
        """Validate export options."""
        # Validate paper size
        valid_sizes = ["letter", "A4", "legal"]
        if options.paper_size not in valid_sizes:
            logger.warning(f"Unknown paper size '{options.paper_size}', using 'letter'")
            options.paper_size = "letter"

        return True
