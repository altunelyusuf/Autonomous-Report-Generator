"""Abstract interface for ontology parsers."""

from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Union

import rdflib

from src.domain.ontology.models import OntologyFormat, ValidationResult


class IOntologyParser(ABC):
    """Abstract interface for ontology parsing implementations.

    This interface defines the contract that all ontology parsers must implement.
    Different parsers (RDFLib, OWLReady2, etc.) can implement this interface
    to provide consistent ontology parsing capabilities.
    """

    @abstractmethod
    def parse(self, source: Union[Path, BytesIO, str]) -> rdflib.Graph:
        """Parse ontology from various sources.

        Args:
            source: File path, bytes, URI, or stream

        Returns:
            RDF graph containing the parsed ontology

        Raises:
            ParsingException: If parsing fails
            TimeoutException: If parsing exceeds timeout
            UnsupportedFormatException: If format is not supported
        """
        pass

    @abstractmethod
    def validate_syntax(self) -> ValidationResult:
        """Validate ontology syntax.

        Returns:
            ValidationResult with validation status and any errors/warnings

        Raises:
            ValidationException: If validation cannot be performed
        """
        pass

    @abstractmethod
    def get_format_name(self) -> str:
        """Return parser format name.

        Returns:
            Name of the format this parser handles (e.g., 'RDF/XML', 'Turtle', 'OWL')
        """
        pass

    @abstractmethod
    def detect_format(self, source: Union[Path, BytesIO, str]) -> OntologyFormat:
        """Detect ontology format from source.

        Args:
            source: File path, bytes, URI, or stream

        Returns:
            Detected ontology format

        Raises:
            UnsupportedFormatException: If format cannot be detected or is unsupported
        """
        pass
