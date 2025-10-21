"""API request and response models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ReportGenerationRequest(BaseModel):
    """Request to generate a report."""

    query: str = Field(..., min_length=1, max_length=1000, description="Research query")
    ontology_url: Optional[str] = Field(
        None, description="URL to ontology file (OWL/RDF)"
    )
    ontology_content: Optional[str] = Field(
        None, description="Direct ontology content"
    )
    max_depth: int = Field(3, ge=1, le=5, description="Maximum hierarchy depth")
    research_enabled: bool = Field(True, description="Enable research aggregation")
    max_sources: int = Field(10, ge=1, le=50, description="Maximum research sources")
    llm_provider: str = Field("openai", description="LLM provider (openai/anthropic)")
    llm_model: Optional[str] = Field(None, description="Specific LLM model")
    citation_style: str = Field(
        "apa", description="Citation style (apa/mla/chicago/ieee)"
    )
    include_bibliography: bool = Field(True, description="Include bibliography")
    quality_threshold: float = Field(
        75.0, ge=0.0, le=100.0, description="Minimum quality score"
    )

    @field_validator("citation_style")
    @classmethod
    def validate_citation_style(cls, v: str) -> str:
        """Validate citation style."""
        allowed = ["apa", "mla", "chicago", "ieee"]
        if v.lower() not in allowed:
            raise ValueError(f"Citation style must be one of: {', '.join(allowed)}")
        return v.lower()

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider."""
        allowed = ["openai", "anthropic"]
        if v.lower() not in allowed:
            raise ValueError(f"LLM provider must be one of: {', '.join(allowed)}")
        return v.lower()


class ReportStatus(str, Enum):
    """Report generation status."""

    PENDING = "pending"
    PARSING_ONTOLOGY = "parsing_ontology"
    EXTRACTING_STRUCTURE = "extracting_structure"
    RESEARCHING = "researching"
    GENERATING_CONTENT = "generating_content"
    ASSEMBLING = "assembling"
    ASSESSING_QUALITY = "assessing_quality"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportResponse(BaseModel):
    """Response containing report information."""

    report_id: UUID
    status: ReportStatus
    title: str
    query: str
    section_count: int
    quality_score: Optional[float] = None
    completeness_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class SectionSummary(BaseModel):
    """Summary of a report section."""

    section_id: UUID
    section_number: str
    title: str
    hierarchy_level: int
    content_items: int
    has_citations: bool


class DetailedReportResponse(BaseModel):
    """Detailed report response with sections."""

    report_id: UUID
    status: ReportStatus
    title: str
    query: str
    sections: List[SectionSummary]
    quality_score: float
    completeness_score: float
    total_citations: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


class QualityAssessmentRequest(BaseModel):
    """Request to assess report quality."""

    report_id: UUID
    threshold: float = Field(
        75.0, ge=0.0, le=100.0, description="Quality threshold"
    )
    dimensions: Optional[List[str]] = Field(
        None, description="Specific dimensions to assess"
    )


class QualityDimensionResponse(BaseModel):
    """Quality dimension assessment result."""

    dimension: str
    score: float
    level: str
    passed: bool
    issues: int
    threshold: float


class QualityIssueResponse(BaseModel):
    """Quality issue response."""

    severity: str
    dimension: str
    title: str
    description: str
    location: Optional[str] = None
    recommendation: Optional[str] = None
    auto_fixable: bool


class QualityAssessmentResponse(BaseModel):
    """Quality assessment response."""

    assessment_id: UUID
    report_id: UUID
    overall_score: float
    overall_level: str
    passed: bool
    threshold: float
    dimensions: Dict[str, QualityDimensionResponse]
    total_issues: int
    critical_issues: int
    recommendations: List[str]
    assessed_at: datetime


class ExportFormat(str, Enum):
    """Supported export formats."""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"


class ExportRequest(BaseModel):
    """Request to export report."""

    report_id: UUID
    format: ExportFormat
    include_toc: bool = Field(True, description="Include table of contents")
    include_metadata: bool = Field(True, description="Include metadata")
    include_statistics: bool = Field(True, description="Include statistics")
    include_bibliography: bool = Field(True, description="Include bibliography")
    theme: Optional[str] = Field("light", description="Theme for HTML/PDF (light/dark)")


class ExportResponse(BaseModel):
    """Export operation response."""

    export_id: UUID
    report_id: UUID
    format: str
    status: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    exported_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime
    components: Dict[str, str]


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime


class ListReportsRequest(BaseModel):
    """Request to list reports."""

    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(10, ge=1, le=100, description="Maximum records to return")
    status: Optional[ReportStatus] = Field(None, description="Filter by status")
    min_quality: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Minimum quality score"
    )


class ListReportsResponse(BaseModel):
    """Response with list of reports."""

    reports: List[ReportResponse]
    total: int
    skip: int
    limit: int


class DeleteReportResponse(BaseModel):
    """Response after deleting a report."""

    report_id: UUID
    deleted: bool
    message: str
