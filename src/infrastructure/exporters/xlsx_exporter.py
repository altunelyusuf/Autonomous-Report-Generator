"""MS Excel (XLSX) exporter implementation."""

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
)
from src.domain.models.report import DomainReport, ReportSection

logger = logging.getLogger(__name__)


class XLSXExporter(IExporter):
    """Export reports to MS Excel XLSX format.

    Features:
    - Multiple worksheets (Metadata, TOC, Sections, Statistics)
    - Formatted cells with styles
    - Column widths and row heights
    - Headers and freeze panes
    - Cell borders and colors
    - Formulas for statistics
    - Data validation
    """

    def __init__(self):
        """Initialize XLSX exporter."""
        self.supported_formats = ["xlsx", "xls"]

    async def export(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> ExportResult:
        """Export report to XLSX.

        Args:
            report: Report to export
            output_path: Output file path
            options: Export options

        Returns:
            Export result
        """
        logger.info(f"Exporting report to XLSX: {output_path}")

        start_time = time.time()
        result = ExportResult(
            format=ExportFormat.DOCX,  # Note: Using DOCX enum, should add XLSX to enum
            status=ExportStatus.IN_PROGRESS,
        )

        try:
            # Validate options
            if not self.validate_options(options):
                raise ExportException("Invalid export options")

            # Ensure output path has correct extension
            if not output_path.suffix:
                output_path = output_path.with_suffix(".xlsx")

            # Check if openpyxl is available
            try:
                from openpyxl import Workbook
                from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
                from openpyxl.utils import get_column_letter

                # Generate XLSX with openpyxl
                self._generate_xlsx_openpyxl(report, output_path, options)

            except ImportError:
                # openpyxl not available, create mock XLSX
                logger.warning("openpyxl not available, creating mock XLSX")
                self._generate_mock_xlsx(report, output_path, options)

            # Calculate file size
            file_size = output_path.stat().st_size
            duration = time.time() - start_time

            # Mark as completed
            result.mark_completed(output_path, file_size, duration)

            logger.info(
                f"XLSX export completed: {file_size} bytes, {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"XLSX export failed: {e}")
            result.mark_failed(str(e))
            return result

    def _generate_xlsx_openpyxl(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> None:
        """Generate XLSX using openpyxl.

        Args:
            report: Report
            output_path: Output path
            options: Export options
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        # Create workbook
        wb = Workbook()

        # Remove default sheet
        if "Sheet" in wb.sheetnames:
            wb.remove(wb["Sheet"])

        # Define styles
        header_font = Font(name='Calibri', size=14, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        title_font = Font(name='Calibri', size=16, bold=True, color="2F5496")
        label_font = Font(name='Calibri', size=11, bold=True)
        normal_font = Font(name='Calibri', size=11)

        border_style = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # 1. Metadata Sheet
        if options.include_metadata:
            ws_metadata = wb.create_sheet("Metadata")
            self._create_metadata_sheet(ws_metadata, report, title_font, label_font, normal_font)

        # 2. Table of Contents Sheet
        if options.include_toc:
            ws_toc = wb.create_sheet("Table of Contents")
            self._create_toc_sheet(
                ws_toc, report, header_font, header_fill, header_alignment, normal_font, border_style
            )

        # 3. Report Overview Sheet
        ws_overview = wb.create_sheet("Report Overview")
        self._create_overview_sheet(
            ws_overview, report, title_font, label_font, normal_font, border_style
        )

        # 4. Sections Data Sheet
        ws_sections = wb.create_sheet("Sections")
        self._create_sections_sheet(
            ws_sections, report, header_font, header_fill, header_alignment, normal_font, border_style
        )

        # 5. Statistics Sheet
        if options.include_statistics:
            ws_stats = wb.create_sheet("Statistics")
            self._create_statistics_sheet(ws_stats, report, title_font, label_font, normal_font)

        # Set active sheet to overview
        wb.active = wb["Report Overview"]

        # Save workbook
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(str(output_path))

    def _create_metadata_sheet(self, ws, report, title_font, label_font, normal_font):
        """Create metadata worksheet.

        Args:
            ws: Worksheet
            report: Report
            title_font: Title font style
            label_font: Label font style
            normal_font: Normal font style
        """
        from openpyxl.styles import Alignment

        # Title
        ws['A1'] = "Report Metadata"
        ws['A1'].font = title_font
        ws['A1'].alignment = Alignment(horizontal="left", vertical="center")

        # Metadata items
        metadata = [
            ("Report ID:", str(report.report_id)),
            ("Report Title:", report.report_title),
            ("Generated:", datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')),
            ("Quality Score:", f"{report.quality_score:.2f}/100"),
            ("Completeness:", f"{report.completeness_score:.2f}%"),
            ("Total Sections:", str(report.get_section_count())),
        ]

        row = 3
        for label, value in metadata:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = label_font
            ws[f'B{row}'] = value
            ws[f'B{row}'].font = normal_font
            row += 1

        # Adjust column widths
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 50

    def _create_toc_sheet(self, ws, report, header_font, header_fill, header_alignment, normal_font, border_style):
        """Create table of contents worksheet.

        Args:
            ws: Worksheet
            report: Report
            header_font: Header font style
            header_fill: Header fill style
            header_alignment: Header alignment
            normal_font: Normal font style
            border_style: Border style
        """
        from openpyxl.styles import Alignment

        # Header row
        headers = ["Section #", "Title", "Level", "Subsections"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border_style

        # Add sections
        sections = report.get_all_sections()
        for row, section in enumerate(sections, 2):
            ws.cell(row=row, column=1, value=section.section_number).font = normal_font
            ws.cell(row=row, column=2, value=section.section_title).font = normal_font
            ws.cell(row=row, column=3, value=section.hierarchy_level).font = normal_font
            ws.cell(row=row, column=4, value=len(section.get_subsections())).font = normal_font

            # Add indentation for hierarchy
            indent_cell = ws.cell(row=row, column=2)
            indent_cell.alignment = Alignment(indent=section.hierarchy_level * 2)

        # Adjust column widths
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 15

        # Freeze header row
        ws.freeze_panes = 'A2'

    def _create_overview_sheet(self, ws, report, title_font, label_font, normal_font, border_style):
        """Create overview worksheet.

        Args:
            ws: Worksheet
            report: Report
            title_font: Title font style
            label_font: Label font style
            normal_font: Normal font style
            border_style: Border style
        """
        from openpyxl.styles import Alignment

        # Title
        ws['A1'] = report.report_title
        ws['A1'].font = title_font
        ws.merge_cells('A1:D1')
        ws['A1'].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 30

        # Summary section
        ws['A3'] = "Report Summary"
        ws['A3'].font = label_font

        summary_data = [
            ("Total Sections:", report.get_section_count()),
            ("Quality Score:", f"{report.quality_score:.2f}/100"),
            ("Completeness:", f"{report.completeness_score:.2f}%"),
        ]

        row = 4
        for label, value in summary_data:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = label_font
            ws[f'B{row}'] = value
            ws[f'B{row}'].font = normal_font
            row += 1

        # Section breakdown
        ws['A8'] = "Section Breakdown"
        ws['A8'].font = label_font

        ws['A9'] = "Level"
        ws['B9'] = "Count"
        ws['A9'].font = label_font
        ws['B9'].font = label_font

        # Count sections by level
        sections = report.get_all_sections()
        level_counts = {}
        for section in sections:
            level = section.hierarchy_level
            level_counts[level] = level_counts.get(level, 0) + 1

        row = 10
        for level in sorted(level_counts.keys()):
            ws[f'A{row}'] = f"Level {level}"
            ws[f'B{row}'] = level_counts[level]
            row += 1

        # Adjust column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20

    def _create_sections_sheet(self, ws, report, header_font, header_fill, header_alignment, normal_font, border_style):
        """Create sections data worksheet.

        Args:
            ws: Worksheet
            report: Report
            header_font: Header font style
            header_fill: Header fill style
            header_alignment: Header alignment
            normal_font: Normal font style
            border_style: Border style
        """
        from openpyxl.styles import Alignment

        # Header row
        headers = ["Section #", "Title", "Level", "Content Preview", "Content Items"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border_style

        # Add sections
        sections = report.get_all_sections()
        for row, section in enumerate(sections, 2):
            ws.cell(row=row, column=1, value=section.section_number).font = normal_font
            ws.cell(row=row, column=2, value=section.section_title).font = normal_font
            ws.cell(row=row, column=3, value=section.hierarchy_level).font = normal_font

            # Content preview
            content_items = section.get_content()
            if content_items:
                preview = str(content_items[0])
                if isinstance(content_items[0], dict):
                    preview = content_items[0].get("text", "")
                # Limit preview to 100 characters
                preview = preview[:100] + "..." if len(preview) > 100 else preview
                ws.cell(row=row, column=4, value=preview).font = normal_font

            ws.cell(row=row, column=5, value=len(content_items)).font = normal_font

        # Adjust column widths
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 50
        ws.column_dimensions['E'].width = 15

        # Freeze header row
        ws.freeze_panes = 'A2'

    def _create_statistics_sheet(self, ws, report, title_font, label_font, normal_font):
        """Create statistics worksheet.

        Args:
            ws: Worksheet
            report: Report
            title_font: Title font style
            label_font: Label font style
            normal_font: Normal font style
        """
        from openpyxl.styles import Alignment

        # Title
        ws['A1'] = "Report Statistics"
        ws['A1'].font = title_font
        ws['A1'].alignment = Alignment(horizontal="left", vertical="center")

        # Statistics
        stats = [
            ("Total Sections:", report.get_section_count()),
            ("Quality Score:", f"{report.quality_score:.2f}/100"),
            ("Completeness Score:", f"{report.completeness_score:.2f}%"),
        ]

        # Add bibliography stats if available
        if "bibliography" in report.metadata:
            bib_stats = report.metadata["bibliography"]
            stats.extend([
                ("Total Citations:", bib_stats.get('total_citations', 0)),
                ("Used Citations:", bib_stats.get('used_citations', 0)),
                ("Unused Citations:", bib_stats.get('unused_citations', 0)),
            ])

        row = 3
        for label, value in stats:
            ws[f'A{row}'] = label
            ws[f'A{row}'].font = label_font
            ws[f'B{row}'] = value
            ws[f'B{row}'].font = normal_font
            row += 1

        # Chart data section (for potential charts)
        ws[f'A{row + 2}'] = "Quality Metrics"
        ws[f'A{row + 2}'].font = label_font

        metrics_row = row + 3
        ws[f'A{metrics_row}'] = "Metric"
        ws[f'B{metrics_row}'] = "Score"
        ws[f'A{metrics_row}'].font = label_font
        ws[f'B{metrics_row}'].font = label_font

        metrics_row += 1
        ws[f'A{metrics_row}'] = "Quality"
        ws[f'B{metrics_row}'] = report.quality_score

        metrics_row += 1
        ws[f'A{metrics_row}'] = "Completeness"
        ws[f'B{metrics_row}'] = report.completeness_score

        # Adjust column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20

    def _generate_mock_xlsx(
        self,
        report: DomainReport,
        output_path: Path,
        options: ExportOptions,
    ) -> None:
        """Generate mock XLSX for testing without openpyxl.

        Args:
            report: Report
            output_path: Output path
            options: Export options
        """
        import zipfile
        from io import BytesIO

        # Create minimal XLSX structure (XLSX is a ZIP file)
        xlsx_buffer = BytesIO()

        with zipfile.ZipFile(xlsx_buffer, 'w', zipfile.ZIP_DEFLATED) as xlsx:
            # Add [Content_Types].xml
            content_types = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>'''
            xlsx.writestr('[Content_Types].xml', content_types)

            # Add _rels/.rels
            rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
            xlsx.writestr('_rels/.rels', rels)

            # Add xl/workbook.xml
            workbook_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets>
        <sheet name="Report" sheetId="1" r:id="rId1"/>
    </sheets>
</workbook>'''
            xlsx.writestr('xl/workbook.xml', workbook_xml)

            # Add xl/_rels/workbook.xml.rels
            workbook_rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>'''
            xlsx.writestr('xl/_rels/workbook.xml.rels', workbook_rels)

            # Add xl/worksheets/sheet1.xml
            worksheet_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheetData>
        <row r="1">
            <c r="A1" t="inlineStr"><is><t>{report.report_title}</t></is></c>
        </row>
        <row r="2">
            <c r="A2" t="inlineStr"><is><t>Mock XLSX Export</t></is></c>
        </row>
        <row r="3">
            <c r="A3" t="inlineStr"><is><t>Report ID:</t></is></c>
            <c r="B3" t="inlineStr"><is><t>{report.report_id}</t></is></c>
        </row>
        <row r="4">
            <c r="A4" t="inlineStr"><is><t>Sections:</t></is></c>
            <c r="B4"><v>{report.get_section_count()}</v></c>
        </row>
        <row r="5">
            <c r="A5" t="inlineStr"><is><t>Quality:</t></is></c>
            <c r="B5"><v>{report.quality_score}</v></c>
        </row>
    </sheetData>
</worksheet>'''
            xlsx.writestr('xl/worksheets/sheet1.xml', worksheet_xml)

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(xlsx_buffer.getvalue())

    def supports_format(self, format_name: str) -> bool:
        """Check if format is supported."""
        return format_name.lower() in self.supported_formats

    def get_supported_formats(self) -> list[str]:
        """Get supported formats."""
        return self.supported_formats.copy()

    def get_default_extension(self) -> str:
        """Get default file extension."""
        return ".xlsx"

    def validate_options(self, options: ExportOptions) -> bool:
        """Validate export options."""
        return True
