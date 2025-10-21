"""Application settings and configuration management."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Report Generation System", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(..., alias="SECRET_KEY")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=40, alias="DB_MAX_OVERFLOW")
    db_echo: bool = Field(default=False, alias="DB_ECHO")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_cache_ttl: int = Field(default=86400, alias="REDIS_CACHE_TTL")

    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=True, alias="API_RELOAD")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"], alias="CORS_ORIGINS"
    )

    # Ontology Parser
    ontology_max_file_size_mb: int = Field(
        default=100, alias="ONTOLOGY_MAX_FILE_SIZE_MB"
    )
    ontology_timeout_seconds: int = Field(
        default=300, alias="ONTOLOGY_TIMEOUT_SECONDS"
    )
    ontology_cache_enabled: bool = Field(
        default=True, alias="ONTOLOGY_CACHE_ENABLED"
    )
    ontology_cache_ttl_hours: int = Field(
        default=24, alias="ONTOLOGY_CACHE_TTL_HOURS"
    )

    # OpenAI LLM
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", alias="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=4000, alias="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, alias="OPENAI_TEMPERATURE")
    openai_enabled: bool = Field(default=False, alias="OPENAI_ENABLED")

    # Anthropic LLM
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514", alias="ANTHROPIC_MODEL"
    )
    anthropic_max_tokens: int = Field(default=4000, alias="ANTHROPIC_MAX_TOKENS")
    anthropic_temperature: float = Field(default=0.7, alias="ANTHROPIC_TEMPERATURE")
    anthropic_enabled: bool = Field(default=False, alias="ANTHROPIC_ENABLED")

    # Local LLM
    local_llm_enabled: bool = Field(default=False, alias="LOCAL_LLM_ENABLED")
    local_llm_endpoint: str = Field(
        default="http://localhost:11434", alias="LOCAL_LLM_ENDPOINT"
    )
    local_llm_model: str = Field(default="llama2", alias="LOCAL_LLM_MODEL")

    # Research Services
    web_search_enabled: bool = Field(default=True, alias="WEB_SEARCH_ENABLED")
    web_search_api_key: Optional[str] = Field(default=None, alias="WEB_SEARCH_API_KEY")
    academic_api_enabled: bool = Field(default=True, alias="ACADEMIC_API_ENABLED")
    academic_api_key: Optional[str] = Field(default=None, alias="ACADEMIC_API_KEY")
    wikidata_enabled: bool = Field(default=True, alias="WIKIDATA_ENABLED")

    # Content Generation
    content_min_quality_score: float = Field(
        default=75.0, alias="CONTENT_MIN_QUALITY_SCORE"
    )
    content_min_readability: float = Field(
        default=60.0, alias="CONTENT_MIN_READABILITY"
    )
    content_temperature: float = Field(default=0.7, alias="CONTENT_TEMPERATURE")

    # Cost Limits
    llm_per_request_max_usd: float = Field(
        default=0.50, alias="LLM_PER_REQUEST_MAX_USD"
    )
    llm_daily_max_usd: float = Field(default=100.00, alias="LLM_DAILY_MAX_USD")

    # Quality Thresholds
    quality_min_completeness: float = Field(
        default=80.0, alias="QUALITY_MIN_COMPLETENESS"
    )
    quality_min_citation_coverage: float = Field(
        default=90.0, alias="QUALITY_MIN_CITATION_COVERAGE"
    )
    quality_min_accessibility: float = Field(
        default=85.0, alias="QUALITY_MIN_ACCESSIBILITY"
    )

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND"
    )

    # Monitoring
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v.upper()

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def any_llm_enabled(self) -> bool:
        """Check if any LLM provider is enabled."""
        return self.openai_enabled or self.anthropic_enabled or self.local_llm_enabled


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
