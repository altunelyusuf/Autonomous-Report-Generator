"""Basic report generation example.

This example demonstrates the simplest workflow:
1. Create orchestrator
2. Configure report generation
3. Generate report
4. Export to multiple formats
"""

import asyncio
from pathlib import Path

from src.orchestration import create_default_orchestrator, ReportGenerationConfig
from src.domain.export.models import ExportFormat, ExportOptions
from src.infrastructure.exporters.manager import ExportManager


async def main():
    """Run basic report generation example."""
    print("=" * 80)
    print("BASIC REPORT GENERATION EXAMPLE")
    print("=" * 80)

    # Step 1: Create orchestrator
    print("\n1. Creating orchestrator...")
    orchestrator = create_default_orchestrator()
    print("   ✓ Orchestrator created")

    # Step 2: Configure report generation
    print("\n2. Configuring report generation...")
    config = ReportGenerationConfig(
        query="Machine Learning Fundamentals",
        max_depth=3,
        research_enabled=False,  # Disable for basic example
        citation_style="apa",
        include_bibliography=True,
        quality_threshold=60.0,  # Lower threshold for basic example
    )
    print(f"   ✓ Query: {config.query}")
    print(f"   ✓ Max depth: {config.max_depth}")
    print(f"   ✓ Citation style: {config.citation_style}")

    # Step 3: Generate report
    print("\n3. Generating report...")
    report, assessment = await orchestrator.generate_report(config)
    print(f"   ✓ Report generated: {report.report_title}")
    print(f"   ✓ Sections: {report.get_section_count()}")
    print(f"   ✓ Quality score: {assessment.overall_score:.2f}/100")
    print(f"   ✓ Quality level: {assessment.overall_level.value}")

    # Step 4: Show sections
    print("\n4. Report structure:")
    for section in report.get_all_sections():
        indent = "  " * section.hierarchy_level
        print(f"   {indent}{section.section_number} {section.section_title}")

    # Step 5: Export to multiple formats
    print("\n5. Exporting to multiple formats...")
    output_dir = Path("/tmp/report_examples")
    output_dir.mkdir(parents=True, exist_ok=True)

    manager = ExportManager()
    options = ExportOptions(
        include_toc=True,
        include_metadata=True,
        include_statistics=True,
    )

    formats = [
        (ExportFormat.MARKDOWN, "md"),
        (ExportFormat.HTML, "html"),
    ]

    for format_type, ext in formats:
        output_path = output_dir / f"basic_report.{ext}"
        result = await manager.export(report, format_type, output_path, options)

        if result.output_path:
            file_size_kb = result.file_size / 1024
            print(f"   ✓ {format_type.value.upper()}: {output_path} ({file_size_kb:.1f} KB)")
        else:
            print(f"   ✗ {format_type.value.upper()}: Export failed - {result.error_message}")

    # Step 6: Show quality details
    print("\n6. Quality assessment details:")
    for dimension, dim_score in assessment.dimension_scores.items():
        status = "✓" if dim_score.passed else "✗"
        print(
            f"   {status} {dimension.value.capitalize()}: "
            f"{dim_score.score:.2f}/100 ({dim_score.level.value})"
        )

    if assessment.recommendations:
        print("\n7. Recommendations:")
        for i, rec in enumerate(assessment.recommendations[:5], 1):
            print(f"   {i}. {rec}")

    print("\n" + "=" * 80)
    print("EXAMPLE COMPLETE")
    print("=" * 80)
    print(f"\nGenerated files in: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
