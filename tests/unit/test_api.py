"""Tests for API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models import (
    ExportFormat,
    ExportRequest,
    QualityAssessmentRequest,
    ReportGenerationRequest,
    ReportStatus,
)
from src.domain.models.ontology import Concept, DomainOntology
from src.domain.models.report import DomainReport, ReportSection
from src.domain.quality.models import QualityAssessment, QualityDimension


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_report():
    """Create mock report."""
    report = DomainReport(
        report_id=uuid4(),
        report_title="Test Report",
        created_at=datetime.utcnow(),
    )

    section = ReportSection(
        section_id=uuid4(),
        section_number="1",
        section_title="Introduction",
        hierarchy_level=0,
    )
    section.add_content_item({"type": "text", "text": "Test content"})
    report.add_section(section)

    return report


@pytest.fixture
def mock_assessment():
    """Create mock quality assessment."""
    assessment = QualityAssessment(
        report_id=uuid4(),
        threshold=75.0,
    )
    assessment.overall_score = 85.0
    assessment.calculate_overall_score()
    return assessment


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert "components" in data
        assert data["components"]["api"] == "healthy"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert data["docs"] == "/docs"


class TestReportEndpoints:
    """Tests for report endpoints."""

    @patch("src.api.routes.reports.create_default_orchestrator")
    def test_create_report_success(self, mock_orchestrator_factory, client, mock_report, mock_assessment):
        """Test successful report creation."""
        # Setup mock
        mock_orchestrator = MagicMock()
        mock_orchestrator.generate_report = AsyncMock(
            return_value=(mock_report, mock_assessment)
        )
        mock_orchestrator_factory.return_value = mock_orchestrator

        # Make request
        request_data = {
            "query": "Test query",
            "max_depth": 3,
            "research_enabled": True,
            "llm_provider": "openai",
            "citation_style": "apa",
        }

        response = client.post("/reports/", json=request_data)

        assert response.status_code == 202
        data = response.json()

        assert "report_id" in data
        assert data["query"] == "Test query"
        assert data["status"] in [s.value for s in ReportStatus]

    def test_create_report_invalid_citation_style(self, client):
        """Test report creation with invalid citation style."""
        request_data = {
            "query": "Test query",
            "citation_style": "invalid",
        }

        response = client.post("/reports/", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_create_report_invalid_provider(self, client):
        """Test report creation with invalid LLM provider."""
        request_data = {
            "query": "Test query",
            "llm_provider": "invalid",
        }

        response = client.post("/reports/", json=request_data)

        assert response.status_code == 422  # Validation error

    @patch("src.api.routes.reports._reports_storage")
    def test_get_report_success(self, mock_storage, client, mock_report, mock_assessment):
        """Test successful report retrieval."""
        # Setup mock storage
        report_id = uuid4()
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(
            return_value={
                "report_id": report_id,
                "status": ReportStatus.COMPLETED,
                "title": "Test Report",
                "query": "Test query",
                "section_count": 1,
                "quality_score": 85.0,
                "completeness_score": 90.0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "error_message": None,
                "report": mock_report,
                "assessment": mock_assessment,
            }
        )

        response = client.get(f"/reports/{report_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["report_id"] == str(report_id)
        assert data["title"] == "Test Report"
        assert "sections" in data

    def test_get_report_not_found(self, client):
        """Test report retrieval for non-existent report."""
        non_existent_id = uuid4()
        response = client.get(f"/reports/{non_existent_id}")

        assert response.status_code == 404

    @patch("src.api.routes.reports._reports_storage")
    def test_list_reports(self, mock_storage, client):
        """Test listing reports."""
        # Setup mock storage
        mock_storage.values = MagicMock(return_value=[])

        response = client.get("/reports/")

        assert response.status_code == 200
        data = response.json()

        assert "reports" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data

    @patch("src.api.routes.reports._reports_storage")
    def test_list_reports_with_filters(self, mock_storage, client):
        """Test listing reports with filters."""
        # Setup mock storage
        mock_storage.values = MagicMock(return_value=[])

        response = client.get(
            "/reports/?skip=0&limit=5&status=completed&min_quality=80.0"
        )

        assert response.status_code == 200

    @patch("src.api.routes.reports._reports_storage")
    def test_delete_report_success(self, mock_storage, client):
        """Test successful report deletion."""
        # Setup mock storage
        report_id = uuid4()
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__delitem__ = MagicMock()

        response = client.delete(f"/reports/{report_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["deleted"] is True
        assert UUID(data["report_id"]) == report_id

    def test_delete_report_not_found(self, client):
        """Test report deletion for non-existent report."""
        non_existent_id = uuid4()
        response = client.delete(f"/reports/{non_existent_id}")

        assert response.status_code == 404


class TestQualityEndpoints:
    """Tests for quality assessment endpoints."""

    @patch("src.api.routes.quality._reports_storage")
    @patch("src.api.routes.quality.create_default_quality_assessor")
    def test_assess_quality_success(
        self, mock_assessor_factory, mock_storage, client, mock_report, mock_assessment
    ):
        """Test successful quality assessment."""
        # Setup mocks
        report_id = uuid4()
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(
            return_value={
                "report_id": report_id,
                "status": ReportStatus.COMPLETED,
                "report": mock_report,
            }
        )

        mock_assessor = MagicMock()
        mock_assessor.assess = AsyncMock(return_value=mock_assessment)
        mock_assessor_factory.return_value = mock_assessor

        # Make request
        request_data = {
            "report_id": str(report_id),
            "threshold": 75.0,
        }

        response = client.post("/quality/assess", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "assessment_id" in data
        assert "overall_score" in data
        assert "dimensions" in data

    @patch("src.api.routes.quality._reports_storage")
    def test_assess_quality_report_not_found(self, mock_storage, client):
        """Test quality assessment for non-existent report."""
        mock_storage.__contains__ = MagicMock(return_value=False)

        request_data = {
            "report_id": str(uuid4()),
            "threshold": 75.0,
        }

        response = client.post("/quality/assess", json=request_data)

        assert response.status_code == 404

    @patch("src.api.routes.quality._reports_storage")
    def test_get_quality_assessment_success(
        self, mock_storage, client, mock_assessment
    ):
        """Test successful quality assessment retrieval."""
        # Setup mock
        report_id = uuid4()
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(
            return_value={
                "report_id": report_id,
                "assessment": mock_assessment,
            }
        )

        response = client.get(f"/quality/{report_id}")

        assert response.status_code == 200
        data = response.json()

        assert "assessment_id" in data
        assert "overall_score" in data

    @patch("src.api.routes.quality._reports_storage")
    def test_get_quality_issues_success(self, mock_storage, client, mock_assessment):
        """Test successful quality issues retrieval."""
        # Setup mock
        report_id = uuid4()
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(
            return_value={
                "report_id": report_id,
                "assessment": mock_assessment,
            }
        )

        response = client.get(f"/quality/{report_id}/issues")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)


class TestExportEndpoints:
    """Tests for export endpoints."""

    @patch("src.api.routes.export._reports_storage")
    @patch("src.api.routes.export._export_manager")
    def test_export_report_success(
        self, mock_manager, mock_storage, client, mock_report
    ):
        """Test successful report export."""
        # Setup mocks
        report_id = uuid4()
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(
            return_value={
                "report_id": report_id,
                "status": ReportStatus.COMPLETED,
                "report": mock_report,
            }
        )

        from src.domain.export.models import ExportResult, ExportStatus
        from pathlib import Path

        mock_result = ExportResult(
            format=src.domain.export.models.ExportFormat.MARKDOWN,
            status=ExportStatus.COMPLETED,
        )
        mock_result.output_path = Path("/tmp/test.md")
        mock_result.file_size = 1000
        mock_result.duration = 0.5

        mock_manager.export = AsyncMock(return_value=mock_result)

        # Make request
        request_data = {
            "report_id": str(report_id),
            "format": "markdown",
            "include_toc": True,
        }

        response = client.post("/export/", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "export_id" in data
        assert data["format"] == "markdown"
        assert data["status"] == "completed"

    @patch("src.api.routes.export._reports_storage")
    def test_export_report_not_found(self, mock_storage, client):
        """Test export for non-existent report."""
        mock_storage.__contains__ = MagicMock(return_value=False)

        request_data = {
            "report_id": str(uuid4()),
            "format": "markdown",
        }

        response = client.post("/export/", json=request_data)

        assert response.status_code == 404

    @patch("src.api.routes.export._exports_storage")
    def test_get_export_status_success(self, mock_storage, client):
        """Test successful export status retrieval."""
        # Setup mock
        export_id = uuid4()
        mock_storage.__contains__ = MagicMock(return_value=True)
        mock_storage.__getitem__ = MagicMock(
            return_value={
                "export_id": export_id,
                "report_id": uuid4(),
                "format": "markdown",
                "status": "completed",
                "file_path": "/tmp/test.md",
                "file_size": 1000,
                "download_url": f"/export/{export_id}/download",
                "duration": 0.5,
                "error_message": None,
                "exported_at": datetime.utcnow(),
            }
        )

        response = client.get(f"/export/{export_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["export_id"] == str(export_id)
        assert data["status"] == "completed"

    def test_get_export_status_not_found(self, client):
        """Test export status for non-existent export."""
        non_existent_id = uuid4()
        response = client.get(f"/export/{non_existent_id}")

        assert response.status_code == 404


class TestErrorHandling:
    """Tests for error handling."""

    def test_validation_error(self, client):
        """Test validation error handling."""
        # Missing required field
        request_data = {}

        response = client.post("/reports/", json=request_data)

        assert response.status_code == 422
        data = response.json()

        assert "error" in data
        assert data["error"] == "ValidationError"


class TestOrchestratorModule:
    """Tests for orchestrator module."""

    @pytest.mark.asyncio
    async def test_orchestrator_creation(self):
        """Test orchestrator creation."""
        from src.orchestration import create_default_orchestrator

        orchestrator = create_default_orchestrator()

        assert orchestrator is not None
        assert orchestrator.ontology_parser is not None
        assert orchestrator.structure_extractor is not None

    @pytest.mark.asyncio
    async def test_report_generation_config(self):
        """Test report generation config."""
        from src.orchestration import ReportGenerationConfig

        config = ReportGenerationConfig(
            query="Test query",
            max_depth=3,
            citation_style="apa",
        )

        assert config.query == "Test query"
        assert config.max_depth == 3
        assert config.citation_style == "apa"

    @pytest.mark.asyncio
    async def test_minimal_ontology_creation(self):
        """Test minimal ontology creation."""
        from src.orchestration.orchestrator import ReportOrchestrator

        orchestrator = ReportOrchestrator()
        ontology = orchestrator._create_minimal_ontology("Test query")

        assert ontology is not None
        assert len(ontology.concepts) == 1
        assert ontology.concepts[0].name == "Test query"


# Integration test fixtures would go here
# These would test the full flow but require actual implementations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
