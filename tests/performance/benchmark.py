"""Performance benchmarking utilities."""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List
from uuid import uuid4

from src.domain.models.ontology import Concept, DomainOntology, Relationship
from src.domain.structure.extractor import StructureExtractor
from src.domain.quality.assessor import create_default_quality_assessor
from src.domain.export.models import ExportFormat, ExportOptions
from src.infrastructure.exporters.manager import ExportManager
from src.orchestration.orchestrator import (
    ReportGenerationConfig,
    create_default_orchestrator,
)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    duration: float
    iterations: int
    avg_duration: float
    min_duration: float
    max_duration: float
    success_rate: float
    metadata: dict


class Benchmark:
    """Performance benchmark runner."""

    def __init__(self, warmup_iterations: int = 2):
        """Initialize benchmark.

        Args:
            warmup_iterations: Number of warmup runs before measuring
        """
        self.warmup_iterations = warmup_iterations
        self.results: List[BenchmarkResult] = []

    async def run_async(
        self,
        name: str,
        func: Callable,
        iterations: int = 10,
        **kwargs,
    ) -> BenchmarkResult:
        """Run async benchmark.

        Args:
            name: Benchmark name
            func: Async function to benchmark
            iterations: Number of iterations
            **kwargs: Arguments to pass to function

        Returns:
            Benchmark result
        """
        print(f"\nRunning benchmark: {name}")

        # Warmup
        print(f"  Warmup ({self.warmup_iterations} iterations)...")
        for _ in range(self.warmup_iterations):
            try:
                await func(**kwargs)
            except Exception as e:
                print(f"  Warmup error: {e}")

        # Measure
        print(f"  Measuring ({iterations} iterations)...")
        durations = []
        successes = 0

        start_time = time.time()

        for i in range(iterations):
            iteration_start = time.time()
            try:
                await func(**kwargs)
                iteration_duration = time.time() - iteration_start
                durations.append(iteration_duration)
                successes += 1
            except Exception as e:
                print(f"  Iteration {i+1} error: {e}")
                durations.append(0.0)

        total_duration = time.time() - start_time

        # Calculate statistics
        if durations:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(d for d in durations if d > 0) if any(d > 0 for d in durations) else 0
            max_duration = max(durations)
        else:
            avg_duration = 0
            min_duration = 0
            max_duration = 0

        success_rate = successes / iterations if iterations > 0 else 0

        result = BenchmarkResult(
            name=name,
            duration=total_duration,
            iterations=iterations,
            avg_duration=avg_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            success_rate=success_rate,
            metadata=kwargs,
        )

        self.results.append(result)

        print(f"  ✓ Completed: {avg_duration:.3f}s avg, {success_rate:.1%} success")

        return result

    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        for result in self.results:
            print(f"\n{result.name}")
            print(f"  Iterations:    {result.iterations}")
            print(f"  Success Rate:  {result.success_rate:.1%}")
            print(f"  Avg Duration:  {result.avg_duration:.3f}s")
            print(f"  Min Duration:  {result.min_duration:.3f}s")
            print(f"  Max Duration:  {result.max_duration:.3f}s")
            print(f"  Total Time:    {result.duration:.3f}s")


async def benchmark_ontology_parsing(size: int = 50):
    """Benchmark ontology creation and parsing.

    Args:
        size: Number of concepts to create
    """
    ontology = DomainOntology(
        ontology_id=str(uuid4()),
        name=f"Benchmark Ontology ({size} concepts)",
        description="Performance test",
    )

    # Create concepts
    concepts = []
    for i in range(size):
        concept = Concept(
            concept_id=str(uuid4()),
            name=f"Concept_{i}",
            description=f"Description for concept {i}",
            category="test",
        )
        ontology.add_concept(concept)
        concepts.append(concept)

    # Add relationships
    for i in range(size - 1):
        ontology.add_relationship(
            Relationship(
                relationship_id=str(uuid4()),
                source_concept_id=concepts[i].concept_id,
                target_concept_id=concepts[i + 1].concept_id,
                relationship_type="related_to",
            )
        )

    return ontology


async def benchmark_structure_extraction(size: int = 50):
    """Benchmark structure extraction.

    Args:
        size: Number of concepts
    """
    ontology = await benchmark_ontology_parsing(size)

    extractor = StructureExtractor()
    report = extractor.extract_structure(ontology, max_depth=3)

    return report


async def benchmark_quality_assessment(size: int = 20):
    """Benchmark quality assessment.

    Args:
        size: Number of sections
    """
    ontology = await benchmark_ontology_parsing(size)
    report = await benchmark_structure_extraction(size)

    # Add content
    for section in report.get_all_sections():
        section.add_content_item({
            "type": "text",
            "text": "This is test content for performance benchmarking. " * 20,
        })

    assessor = create_default_quality_assessor()
    assessment = await assessor.assess(report)

    return assessment


async def benchmark_export(format: ExportFormat, size: int = 20):
    """Benchmark export operation.

    Args:
        format: Export format
        size: Number of sections
    """
    ontology = await benchmark_ontology_parsing(size)
    report = await benchmark_structure_extraction(size)

    # Add content
    for section in report.get_all_sections():
        section.add_content_item({
            "type": "text",
            "text": "Export benchmark content. " * 50,
        })

    # Export
    manager = ExportManager()
    output_path = Path(f"/tmp/benchmark_{format.value}.tmp")

    result = await manager.export(
        report, format, output_path, ExportOptions()
    )

    # Cleanup
    if result.output_path and result.output_path.exists():
        result.output_path.unlink()

    return result


async def benchmark_full_workflow(size: int = 10):
    """Benchmark complete workflow.

    Args:
        size: Complexity parameter
    """
    orchestrator = create_default_orchestrator()

    config = ReportGenerationConfig(
        query=f"Benchmark Test {size}",
        max_depth=2,
        research_enabled=False,
        citation_style="apa",
    )

    report, assessment = await orchestrator.generate_report(config)

    return report, assessment


async def main():
    """Run all benchmarks."""
    print("=" * 80)
    print("PERFORMANCE BENCHMARKS")
    print("=" * 80)

    benchmark = Benchmark(warmup_iterations=2)

    # Ontology benchmarks
    await benchmark.run_async(
        "Ontology Creation (10 concepts)",
        benchmark_ontology_parsing,
        iterations=20,
        size=10,
    )

    await benchmark.run_async(
        "Ontology Creation (50 concepts)",
        benchmark_ontology_parsing,
        iterations=10,
        size=50,
    )

    await benchmark.run_async(
        "Ontology Creation (100 concepts)",
        benchmark_ontology_parsing,
        iterations=5,
        size=100,
    )

    # Structure extraction benchmarks
    await benchmark.run_async(
        "Structure Extraction (10 concepts)",
        benchmark_structure_extraction,
        iterations=15,
        size=10,
    )

    await benchmark.run_async(
        "Structure Extraction (50 concepts)",
        benchmark_structure_extraction,
        iterations=8,
        size=50,
    )

    # Quality assessment benchmarks
    await benchmark.run_async(
        "Quality Assessment (10 sections)",
        benchmark_quality_assessment,
        iterations=10,
        size=10,
    )

    await benchmark.run_async(
        "Quality Assessment (20 sections)",
        benchmark_quality_assessment,
        iterations=5,
        size=20,
    )

    # Export benchmarks
    await benchmark.run_async(
        "Export to Markdown",
        benchmark_export,
        iterations=10,
        format=ExportFormat.MARKDOWN,
        size=15,
    )

    await benchmark.run_async(
        "Export to HTML",
        benchmark_export,
        iterations=10,
        format=ExportFormat.HTML,
        size=15,
    )

    # Full workflow benchmark
    await benchmark.run_async(
        "Full Workflow (Simple)",
        benchmark_full_workflow,
        iterations=5,
        size=5,
    )

    await benchmark.run_async(
        "Full Workflow (Medium)",
        benchmark_full_workflow,
        iterations=3,
        size=10,
    )

    # Print summary
    benchmark.print_summary()

    # Performance recommendations
    print("\n" + "=" * 80)
    print("PERFORMANCE RECOMMENDATIONS")
    print("=" * 80)

    for result in benchmark.results:
        if result.avg_duration > 1.0:
            print(f"\n⚠ {result.name}")
            print(f"  Average duration is high: {result.avg_duration:.3f}s")
            print("  Consider optimization or caching")

        if result.success_rate < 1.0:
            print(f"\n⚠ {result.name}")
            print(f"  Success rate is low: {result.success_rate:.1%}")
            print("  Investigate failures")


if __name__ == "__main__":
    asyncio.run(main())
