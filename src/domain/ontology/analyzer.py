"""Ontology analyzer - main facade for ontology processing."""

import hashlib
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

from src.domain.ontology.builders.hierarchy_builder import ClassHierarchyBuilder
from src.domain.ontology.exceptions import ParsingException, ValidationException
from src.domain.ontology.extractors.class_extractor import ClassExtractor
from src.domain.ontology.extractors.metadata_extractor import MetadataExtractor
from src.domain.ontology.models import OntologyFormat, OntologyStatistics, OntologyStructure
from src.domain.ontology.parser import IOntologyParser
from src.domain.ontology.parsers.rdflib_parser import RDFLibParser

logger = logging.getLogger(__name__)


class OntologyAnalyzer:
    """Facade for ontology parsing and analysis operations.

    This class provides a simplified interface for analyzing ontologies,
    coordinating multiple components:
    - Parser: Parse ontology file
    - Metadata Extractor: Extract Dublin Core and OWL metadata
    - Class Extractor: Extract OWL classes
    - Hierarchy Builder: Build class hierarchy tree

    Features:
    - Automatic format detection
    - Comprehensive metadata extraction
    - Complete class hierarchy
    - Statistics calculation
    """

    def __init__(
        self,
        parser: Optional[IOntologyParser] = None,
        metadata_extractor: Optional[MetadataExtractor] = None,
        class_extractor: Optional[ClassExtractor] = None,
        hierarchy_builder: Optional[ClassHierarchyBuilder] = None,
    ):
        """Initialize ontology analyzer.

        Args:
            parser: Optional custom parser (defaults to RDFLibParser)
            metadata_extractor: Optional custom metadata extractor
            class_extractor: Optional custom class extractor
            hierarchy_builder: Optional custom hierarchy builder
        """
        self.parser = parser or RDFLibParser()
        self.metadata_extractor = metadata_extractor or MetadataExtractor()
        self.class_extractor = class_extractor or ClassExtractor()
        self.hierarchy_builder = hierarchy_builder or ClassHierarchyBuilder()

        logger.info("OntologyAnalyzer initialized")

    def analyze_ontology(
        self,
        source: Union[Path, BytesIO, str],
        format: Optional[OntologyFormat] = None,
    ) -> OntologyStructure:
        """Analyze ontology and extract complete structure.

        This is the main entry point for ontology analysis.

        Process:
        1. Parse ontology file to RDF graph
        2. Extract metadata (Dublin Core, OWL)
        3. Extract classes
        4. Build class hierarchy
        5. Calculate statistics

        Args:
            source: File path, BytesIO, or URI
            format: Optional explicit format (auto-detected if None)

        Returns:
            OntologyStructure with all extracted information

        Raises:
            ParsingException: If ontology cannot be parsed
            ValidationException: If ontology is invalid
        """
        logger.info(f"Starting ontology analysis: {self._get_source_description(source)}")

        try:
            # Step 1: Parse ontology
            logger.info("Step 1/5: Parsing ontology")
            graph = self.parser.parse(source)

            # Validate syntax
            validation = self.parser.validate_syntax()
            if not validation.is_valid:
                logger.error(f"Validation failed: {validation.errors}")
                raise ValidationException(f"Ontology validation failed: {validation.errors}")

            # Get ontology URI
            ontology_uri = self._extract_ontology_uri(graph)
            detected_format = self.parser.detect_format(source) if format is None else format

            # Step 2: Extract metadata
            logger.info("Step 2/5: Extracting metadata")
            metadata = self.metadata_extractor.extract_metadata(graph, ontology_uri)

            # Step 3: Extract classes
            logger.info("Step 3/5: Extracting classes")
            classes = self.class_extractor.extract_classes(graph)

            # Step 4: Build hierarchy
            logger.info("Step 4/5: Building class hierarchy")
            hierarchy = self.hierarchy_builder.build_hierarchy(classes)

            # Step 5: Calculate statistics
            logger.info("Step 5/5: Calculating statistics")
            statistics = self._calculate_statistics(graph, classes, hierarchy)

            # Create structure
            structure = OntologyStructure(
                uri=ontology_uri or "unknown",
                format=detected_format,
                metadata=metadata,
                classes=classes,
                properties=[],  # Will be implemented in future enhancement
                individuals=[],  # Will be implemented in future enhancement
                hierarchy=hierarchy,
                statistics=statistics,
            )

            logger.info(
                f"Analysis complete: {statistics.class_count} classes, "
                f"{hierarchy.max_depth} max depth"
            )

            return structure

        except (ParsingException, ValidationException):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during analysis: {e}")
            raise ParsingException(f"Analysis failed: {str(e)}") from e

    def _extract_ontology_uri(self, graph) -> Optional[str]:
        """Extract ontology URI from graph.

        Args:
            graph: RDF graph

        Returns:
            Ontology URI or None
        """
        from rdflib.namespace import OWL, RDF

        # Find owl:Ontology
        for ontology in graph.subjects(predicate=RDF.type, object=OWL.Ontology):
            return str(ontology)

        return None

    def _calculate_statistics(
        self, graph, classes, hierarchy
    ) -> OntologyStatistics:
        """Calculate ontology statistics.

        Args:
            graph: RDF graph
            classes: List of classes
            hierarchy: Class hierarchy

        Returns:
            OntologyStatistics object
        """
        from rdflib.namespace import OWL, RDF

        statistics = OntologyStatistics()

        # Class statistics
        statistics.class_count = len(classes)

        # Hierarchy statistics
        statistics.max_hierarchy_depth = hierarchy.max_depth

        # Calculate average children per class
        total_children = sum(len(cls.children) for cls in classes)
        if classes:
            statistics.avg_children_per_class = total_children / len(classes)

        # Count different property types
        object_props = set(graph.subjects(predicate=RDF.type, object=OWL.ObjectProperty))
        datatype_props = set(graph.subjects(predicate=RDF.type, object=OWL.DatatypeProperty))
        annotation_props = set(graph.subjects(predicate=RDF.type, object=OWL.AnnotationProperty))

        statistics.object_property_count = len(object_props)
        statistics.datatype_property_count = len(datatype_props)
        statistics.annotation_property_count = len(annotation_props)
        statistics.property_count = (
            statistics.object_property_count
            + statistics.datatype_property_count
            + statistics.annotation_property_count
        )

        # Count individuals
        individuals = set()
        for s in graph.subjects():
            # Check if it's an individual (has a type that is a class)
            for o in graph.objects(subject=s, predicate=RDF.type):
                if o in [cls.uri for cls in classes]:
                    individuals.add(s)

        statistics.individual_count = len(individuals)

        # Total axioms (approximate by triple count)
        statistics.axiom_count = len(graph)

        return statistics

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

    def get_uri_hash(self, uri: str) -> str:
        """Get MD5 hash of URI for caching.

        Args:
            uri: Ontology URI

        Returns:
            MD5 hash string
        """
        return hashlib.md5(uri.encode()).hexdigest()
