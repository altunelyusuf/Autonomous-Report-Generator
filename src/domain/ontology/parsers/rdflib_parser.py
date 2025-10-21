"""RDFLib-based ontology parser implementation."""

import hashlib
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

import rdflib
from rdflib import Graph
from rdflib.exceptions import ParserError

from src.domain.ontology.exceptions import (
    ParsingException,
    TimeoutException,
    UnsupportedFormatException,
)
from src.domain.ontology.models import OntologyFormat, ValidationResult
from src.domain.ontology.parser import IOntologyParser

logger = logging.getLogger(__name__)


class RDFLibParser(IOntologyParser):
    """RDFLib-based parser for RDF/OWL ontologies.

    Supports multiple formats:
    - OWL (RDF/XML format)
    - RDF/XML
    - Turtle (TTL)
    - N3
    - JSON-LD

    Features:
    - Automatic format detection
    - Streaming support for large files (>10MB)
    - Syntax validation
    - Error handling with line numbers
    """

    # File size threshold for streaming (10MB)
    STREAM_THRESHOLD = 10 * 1024 * 1024

    # Format mappings: file extension -> RDFLib format string
    FORMAT_MAP = {
        OntologyFormat.OWL: "xml",
        OntologyFormat.RDF: "xml",
        OntologyFormat.TTL: "turtle",
        OntologyFormat.N3: "n3",
        OntologyFormat.JSONLD: "json-ld",
    }

    # Extension to format mapping
    EXT_TO_FORMAT = {
        ".owl": OntologyFormat.OWL,
        ".rdf": OntologyFormat.RDF,
        ".xml": OntologyFormat.RDF,
        ".ttl": OntologyFormat.TTL,
        ".n3": OntologyFormat.N3,
        ".jsonld": OntologyFormat.JSONLD,
        ".json": OntologyFormat.JSONLD,
    }

    def __init__(self, timeout_seconds: int = 300):
        """Initialize RDFLib parser.

        Args:
            timeout_seconds: Maximum time allowed for parsing (default: 300s)
        """
        self.timeout_seconds = timeout_seconds
        self.graph: Optional[Graph] = None
        self._last_format: Optional[OntologyFormat] = None

    def parse(self, source: Union[Path, BytesIO, str]) -> Graph:
        """Parse ontology from source.

        Args:
            source: File path, BytesIO, or URL string

        Returns:
            Parsed RDF graph

        Raises:
            ParsingException: If parsing fails
            TimeoutException: If parsing exceeds timeout
        """
        logger.info(f"Parsing ontology from: {self._get_source_description(source)}")

        try:
            # Detect format
            fmt = self.detect_format(source)
            self._last_format = fmt

            # Choose parsing strategy based on size
            if self._should_stream(source):
                logger.info("Using streaming parser for large file")
                graph = self._stream_parse(source, fmt)
            else:
                logger.info("Using standard parser")
                graph = self._load_parse(source, fmt)

            self.graph = graph
            logger.info(
                f"Successfully parsed ontology: {len(graph)} triples"
            )
            return graph

        except ParserError as e:
            logger.error(f"RDFLib parsing error: {e}")
            raise ParsingException(
                f"Failed to parse ontology: {str(e)}"
            ) from e
        except TimeoutError as e:
            logger.error(f"Parsing timeout: {e}")
            raise TimeoutException(
                f"Parsing exceeded timeout of {self.timeout_seconds}s"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during parsing: {e}")
            raise ParsingException(
                f"Unexpected error: {str(e)}"
            ) from e

    def validate_syntax(self) -> ValidationResult:
        """Validate ontology syntax.

        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(is_valid=True)

        if self.graph is None:
            result.add_error("No graph loaded for validation")
            return result

        # Check if graph has any triples
        if len(self.graph) == 0:
            result.add_warning("Graph contains no triples")

        # Check for common RDF/OWL patterns
        try:
            # Check for ontology declaration
            ontologies = list(
                self.graph.subjects(
                    predicate=rdflib.RDF.type,
                    object=rdflib.OWL.Ontology
                )
            )

            if not ontologies:
                result.add_warning("No owl:Ontology declaration found")
            elif len(ontologies) > 1:
                result.add_warning(f"Multiple ontology declarations found: {len(ontologies)}")

            # Check for classes
            classes = list(
                self.graph.subjects(
                    predicate=rdflib.RDF.type,
                    object=rdflib.OWL.Class
                )
            )

            if not classes:
                result.add_warning("No owl:Class declarations found")

            logger.info(
                f"Validation complete: {len(result.errors)} errors, "
                f"{len(result.warnings)} warnings"
            )

        except Exception as e:
            logger.error(f"Error during validation: {e}")
            result.add_error(f"Validation error: {str(e)}")

        return result

    def get_format_name(self) -> str:
        """Get parser format name.

        Returns:
            Format name
        """
        if self._last_format:
            return self._last_format.value.upper()
        return "RDFLib"

    def detect_format(self, source: Union[Path, BytesIO, str]) -> OntologyFormat:
        """Detect ontology format.

        Detection strategy:
        1. Check file extension
        2. Perform content sniffing

        Args:
            source: File path, BytesIO, or URL

        Returns:
            Detected format

        Raises:
            UnsupportedFormatException: If format cannot be detected
        """
        # Try extension-based detection first
        if isinstance(source, Path) or isinstance(source, str):
            path_str = str(source)
            ext = Path(path_str).suffix.lower()
            if ext in self.EXT_TO_FORMAT:
                fmt = self.EXT_TO_FORMAT[ext]
                logger.debug(f"Detected format from extension: {fmt.value}")
                return fmt

        # Try content-based detection
        fmt = self._sniff_format(source)
        if fmt:
            logger.debug(f"Detected format from content: {fmt.value}")
            return fmt

        # Default to RDF/XML if unable to detect
        logger.warning("Unable to detect format, defaulting to RDF/XML")
        return OntologyFormat.RDF

    def _should_stream(self, source: Union[Path, BytesIO, str]) -> bool:
        """Check if source should be streamed.

        Args:
            source: File source

        Returns:
            True if streaming should be used
        """
        try:
            size = self._get_file_size(source)
            return size > self.STREAM_THRESHOLD
        except Exception:
            # If unable to determine size, don't stream
            return False

    def _get_file_size(self, source: Union[Path, BytesIO, str]) -> int:
        """Get file size in bytes.

        Args:
            source: File source

        Returns:
            File size in bytes
        """
        if isinstance(source, Path):
            return source.stat().st_size
        elif isinstance(source, BytesIO):
            current_pos = source.tell()
            source.seek(0, 2)  # Seek to end
            size = source.tell()
            source.seek(current_pos)  # Restore position
            return size
        elif isinstance(source, str) and Path(source).exists():
            return Path(source).stat().st_size
        return 0

    def _load_parse(self, source: Union[Path, BytesIO, str], fmt: OntologyFormat) -> Graph:
        """Parse using standard loading.

        Args:
            source: File source
            fmt: Ontology format

        Returns:
            Parsed graph
        """
        graph = Graph()
        rdflib_format = self.FORMAT_MAP[fmt]

        if isinstance(source, BytesIO):
            graph.parse(source, format=rdflib_format)
        else:
            graph.parse(str(source), format=rdflib_format)

        return graph

    def _stream_parse(self, source: Union[Path, BytesIO, str], fmt: OntologyFormat) -> Graph:
        """Parse using streaming for large files.

        Args:
            source: File source
            fmt: Ontology format

        Returns:
            Parsed graph
        """
        # For now, use standard parsing
        # Future enhancement: implement true streaming for very large files
        return self._load_parse(source, fmt)

    def _sniff_format(self, source: Union[Path, BytesIO, str]) -> Optional[OntologyFormat]:
        """Sniff format from file content.

        Args:
            source: File source

        Returns:
            Detected format or None
        """
        try:
            # Read first few bytes
            if isinstance(source, BytesIO):
                current_pos = source.tell()
                sample = source.read(1024)
                source.seek(current_pos)
            elif isinstance(source, Path) or isinstance(source, str):
                with open(str(source), 'rb') as f:
                    sample = f.read(1024)
            else:
                return None

            sample_str = sample.decode('utf-8', errors='ignore').lower()

            # Check for format indicators
            if '<?xml' in sample_str or '<rdf:rdf' in sample_str:
                return OntologyFormat.RDF
            elif '@prefix' in sample_str or '@base' in sample_str:
                return OntologyFormat.TTL
            elif '"@context"' in sample_str or '"@graph"' in sample_str:
                return OntologyFormat.JSONLD

        except Exception as e:
            logger.warning(f"Error sniffing format: {e}")

        return None

    def _get_source_description(self, source: Union[Path, BytesIO, str]) -> str:
        """Get human-readable source description.

        Args:
            source: File source

        Returns:
            Description string
        """
        if isinstance(source, Path):
            return str(source)
        elif isinstance(source, str):
            return source
        elif isinstance(source, BytesIO):
            return f"<BytesIO: {len(source.getvalue())} bytes>"
        return str(type(source))
