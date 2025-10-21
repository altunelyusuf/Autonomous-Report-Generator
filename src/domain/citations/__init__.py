"""Citation management module."""

from src.domain.citations.bibliography import BibliographyBuilder
from src.domain.citations.formatter import (
    APAFormatter,
    ChicagoFormatter,
    CitationFormatterFactory,
    ICitationFormatter,
    IEEEFormatter,
    MLAFormatter,
)
from src.domain.citations.models import (
    Author,
    Bibliography,
    Citation,
    CitationStyle,
    InlineCitation,
    SourceType,
)

__all__ = [
    # Models
    "Citation",
    "Author",
    "Bibliography",
    "InlineCitation",
    "CitationStyle",
    "SourceType",
    # Formatters
    "ICitationFormatter",
    "APAFormatter",
    "MLAFormatter",
    "ChicagoFormatter",
    "IEEEFormatter",
    "CitationFormatterFactory",
    # Builder
    "BibliographyBuilder",
]
