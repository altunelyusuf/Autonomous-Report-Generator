"""API client example.

This example demonstrates how to interact with the REST API:
1. Create a report
2. Check status
3. Get quality assessment
4. Export to formats
5. Download exported files
"""

import asyncio
import httpx
from typing import Dict, Any


class ReportAPIClient:
    """Simple client for Report Generator API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client.

        Args:
            base_url: API base URL
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def create_report(self, query: str, **kwargs) -> Dict[str, Any]:
        """Create a new report.

        Args:
            query: Research query
            **kwargs: Additional parameters

        Returns:
            Report response
        """
        payload = {"query": query, **kwargs}
        response = await self.client.post(f"{self.base_url}/reports/", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_report(self, report_id: str) -> Dict[str, Any]:
        """Get report details.

        Args:
            report_id: Report ID

        Returns:
            Report details
        """
        response = await self.client.get(f"{self.base_url}/reports/{report_id}")
        response.raise_for_status()
        return response.json()

    async def list_reports(
        self, skip: int = 0, limit: int = 10, **filters
    ) -> Dict[str, Any]:
        """List reports.

        Args:
            skip: Number to skip
            limit: Number to return
            **filters: Additional filters

        Returns:
            List of reports
        """
        params = {"skip": skip, "limit": limit, **filters}
        response = await self.client.get(f"{self.base_url}/reports/", params=params)
        response.raise_for_status()
        return response.json()

    async def assess_quality(
        self, report_id: str, threshold: float = 75.0
    ) -> Dict[str, Any]:
        """Assess report quality.

        Args:
            report_id: Report ID
            threshold: Quality threshold

        Returns:
            Quality assessment
        """
        payload = {"report_id": report_id, "threshold": threshold}
        response = await self.client.post(
            f"{self.base_url}/quality/assess", json=payload
        )
        response.raise_for_status()
        return response.json()

    async def get_quality_assessment(self, report_id: str) -> Dict[str, Any]:
        """Get quality assessment.

        Args:
            report_id: Report ID

        Returns:
            Quality assessment
        """
        response = await self.client.get(f"{self.base_url}/quality/{report_id}")
        response.raise_for_status()
        return response.json()

    async def export_report(
        self, report_id: str, format: str, **options
    ) -> Dict[str, Any]:
        """Export report.

        Args:
            report_id: Report ID
            format: Export format (markdown, html, pdf, docx, xlsx)
            **options: Export options

        Returns:
            Export response
        """
        payload = {"report_id": report_id, "format": format, **options}
        response = await self.client.post(f"{self.base_url}/export/", json=payload)
        response.raise_for_status()
        return response.json()

    async def download_export(self, export_id: str, output_path: str) -> None:
        """Download exported file.

        Args:
            export_id: Export ID
            output_path: Local file path
        """
        response = await self.client.get(
            f"{self.base_url}/export/{export_id}/download"
        )
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

    async def get_health(self) -> Dict[str, Any]:
        """Check API health.

        Returns:
            Health status
        """
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close client."""
        await self.client.aclose()


async def main():
    """Run API client example."""
    print("=" * 80)
    print("API CLIENT EXAMPLE")
    print("=" * 80)

    client = ReportAPIClient()

    try:
        # 1. Check health
        print("\n1. Checking API health...")
        health = await client.get_health()
        print(f"   ✓ Status: {health['status']}")
        print(f"   ✓ Version: {health['version']}")

        # 2. Create report
        print("\n2. Creating report...")
        report = await client.create_report(
            query="Artificial Intelligence Overview",
            max_depth=2,
            citation_style="apa",
        )
        report_id = report["report_id"]
        print(f"   ✓ Report ID: {report_id}")
        print(f"   ✓ Status: {report['status']}")

        # 3. Get report details
        print("\n3. Getting report details...")
        details = await client.get_report(report_id)
        print(f"   ✓ Title: {details['title']}")
        print(f"   ✓ Sections: {len(details.get('sections', []))}")
        print(f"   ✓ Quality Score: {details.get('quality_score', 0):.2f}/100")

        # 4. Get quality assessment
        if details.get("status") == "completed":
            print("\n4. Getting quality assessment...")
            assessment = await client.get_quality_assessment(report_id)
            print(f"   ✓ Overall Score: {assessment['overall_score']:.2f}/100")
            print(f"   ✓ Overall Level: {assessment['overall_level']}")
            print(f"   ✓ Total Issues: {assessment['total_issues']}")
            print(f"   ✓ Critical Issues: {assessment['critical_issues']}")

            print("\n   Dimension scores:")
            for dim, score_data in assessment.get("dimensions", {}).items():
                status = "✓" if score_data["passed"] else "✗"
                print(
                    f"     {status} {dim}: {score_data['score']:.2f}/100 "
                    f"({score_data['level']})"
                )

        # 5. Export to multiple formats
        print("\n5. Exporting to formats...")
        formats = ["markdown", "html"]

        for format in formats:
            export_result = await client.export_report(
                report_id, format, include_toc=True, include_metadata=True
            )
            export_id = export_result["export_id"]
            print(f"   ✓ {format.upper()}: Export ID {export_id}")

            if export_result.get("download_url"):
                print(f"     Download: {export_result['download_url']}")

        # 6. List all reports
        print("\n6. Listing reports...")
        reports_list = await client.list_reports(skip=0, limit=5)
        print(f"   ✓ Total reports: {reports_list['total']}")
        for r in reports_list["reports"][:3]:
            print(f"     - {r['title']} ({r['status']})")

    except httpx.HTTPError as e:
        print(f"\n✗ HTTP Error: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        await client.close()

    print("\n" + "=" * 80)
    print("EXAMPLE COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
