# Quick Start Guide

Get started with the Autonomous Report Generator in 5 minutes.

## Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/Autonomous-Report-Generator.git
cd Autonomous-Report-Generator

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Your First Report

### Option 1: Using Python API

Create a file `my_first_report.py`:

```python
import asyncio
from src.orchestration import create_default_orchestrator, ReportGenerationConfig
from pathlib import Path

async def generate_report():
    # Create orchestrator
    orchestrator = create_default_orchestrator()

    # Configure
    config = ReportGenerationConfig(
        query="Python Programming",
        max_depth=2,
        citation_style="apa"
    )

    # Generate
    report, assessment = await orchestrator.generate_report(config)

    print(f"Report: {report.report_title}")
    print(f"Sections: {report.get_section_count()}")
    print(f"Quality: {assessment.overall_score:.2f}/100")

    return report

asyncio.run(generate_report())
```

Run it:
```bash
python my_first_report.py
```

### Option 2: Using REST API

```bash
# 1. Start the API server
python -m uvicorn src.api.main:app --reload

# 2. Open browser to http://localhost:8000/docs

# 3. Create a report via API
curl -X POST "http://localhost:8000/reports/" \
  -H "Content-Type: application/json" \
  -d '{"query": "Python Programming", "max_depth": 2}'
```

## Export Your Report

```python
from src.infrastructure.exporters.manager import ExportManager
from src.domain.export.models import ExportFormat, ExportOptions

async def export_report(report):
    manager = ExportManager()
    options = ExportOptions(include_toc=True)

    # Export to Markdown
    result = await manager.export(
        report,
        ExportFormat.MARKDOWN,
        Path("my_report.md"),
        options
    )

    print(f"Exported to: {result.output_path}")
```

## Check Quality

```python
from src.domain.quality.assessor import create_default_quality_assessor

async def check_quality(report):
    assessor = create_default_quality_assessor()
    assessment = await assessor.assess(report)

    print(f"Quality Score: {assessment.overall_score:.2f}/100")
    print(f"Issues Found: {assessment.total_issues}")

    for recommendation in assessment.recommendations:
        print(f"- {recommendation}")
```

## Next Steps

1. **Explore Examples**: Check `examples/` directory
2. **Read Documentation**: See `docs/` for detailed guides
3. **API Documentation**: Visit http://localhost:8000/docs
4. **Run Tests**: `pytest tests/`
5. **Benchmarks**: `python tests/performance/benchmark.py`

## Common Tasks

### Generate Report with Custom Ontology

```python
config = ReportGenerationConfig(
    query="My Topic",
    ontology_content=open("my_ontology.owl").read(),
    max_depth=3
)
```

### Use Different Citation Style

```python
config = ReportGenerationConfig(
    query="Research Topic",
    citation_style="mla"  # apa, mla, chicago, ieee
)
```

### Export to Multiple Formats

```python
formats = [
    ExportFormat.MARKDOWN,
    ExportFormat.HTML,
    ExportFormat.PDF,
    ExportFormat.DOCX,
]

for format_type in formats:
    await manager.export(report, format_type, f"report.{format_type.value}", options)
```

## Troubleshooting

### ModuleNotFoundError
```bash
# Ensure you're in the right directory
cd Autonomous-Report-Generator

# Activate virtual environment
source venv/bin/activate
```

### API Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Use different port
python -m uvicorn src.api.main:app --port 8001
```

### Tests Failing
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run specific test file
pytest tests/unit/test_quality.py -v
```

## Getting Help

- **Documentation**: `docs/`
- **Examples**: `examples/`
- **API Docs**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

Happy report generating!
