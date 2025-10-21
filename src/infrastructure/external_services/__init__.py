"""External services integration."""

from src.infrastructure.external_services.academic_api import (
    AcademicAPIService,
    MockAcademicAPIService,
)
from src.infrastructure.external_services.web_search import (
    MockWebSearchService,
    WebSearchService,
)
from src.infrastructure.external_services.wikidata_client import (
    MockWikidataClient,
    WikidataClient,
)

__all__ = [
    "WebSearchService",
    "MockWebSearchService",
    "WikidataClient",
    "MockWikidataClient",
    "AcademicAPIService",
    "MockAcademicAPIService",
]
