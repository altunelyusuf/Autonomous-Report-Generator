"""Metadata extractor for ontologies."""

import logging
from datetime import datetime
from typing import List, Optional

import rdflib
from rdflib import Graph, Namespace
from rdflib.namespace import DC, DCTERMS, OWL, RDF, RDFS

from src.domain.ontology.models import OntologyMetadata

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract metadata from ontologies.

    Supports:
    - Dublin Core (DC, DCTERMS)
    - OWL metadata
    - RDFS labels and comments
    - Custom annotations
    """

    def __init__(self):
        """Initialize metadata extractor."""
        self.dc = DC
        self.dcterms = DCTERMS
        self.owl = OWL
        self.rdfs = RDFS

    def extract_metadata(self, graph: Graph, ontology_uri: Optional[str] = None) -> OntologyMetadata:
        """Extract complete metadata from ontology graph.

        Args:
            graph: RDF graph
            ontology_uri: Optional ontology URI (will be detected if not provided)

        Returns:
            OntologyMetadata object
        """
        logger.info("Extracting ontology metadata")

        # Find ontology URI if not provided
        if not ontology_uri:
            ontology_uri = self._find_ontology_uri(graph)

        ontology_ref = rdflib.URIRef(ontology_uri) if ontology_uri else None

        # Extract all metadata fields
        title = self._extract_title(graph, ontology_ref)
        description = self._extract_description(graph, ontology_ref)
        creators = self._extract_creators(graph, ontology_ref)
        created = self._extract_created_date(graph, ontology_ref)
        modified = self._extract_modified_date(graph, ontology_ref)
        version_info = self._extract_version_info(graph, ontology_ref)
        version_iri = self._extract_version_iri(graph, ontology_ref)
        license_info = self._extract_license(graph, ontology_ref)
        imports = self._extract_imports(graph, ontology_ref)
        namespaces = self._extract_namespaces(graph)
        language = self._extract_language(graph, ontology_ref)
        subject = self._extract_subject(graph, ontology_ref)
        publisher = self._extract_publisher(graph, ontology_ref)
        rights = self._extract_rights(graph, ontology_ref)

        metadata = OntologyMetadata(
            title=title,
            description=description,
            creator=creators,
            created=created,
            modified=modified,
            version_info=version_info,
            version_iri=version_iri,
            license=license_info,
            imports=imports,
            namespaces=namespaces,
            language=language,
            subject=subject,
            publisher=publisher,
            rights=rights,
        )

        logger.info(f"Extracted metadata - Title: {title}, Creators: {len(creators)}")
        return metadata

    def _find_ontology_uri(self, graph: Graph) -> Optional[str]:
        """Find the ontology URI.

        Args:
            graph: RDF graph

        Returns:
            Ontology URI or None
        """
        # Try to find owl:Ontology declaration
        for ontology in graph.subjects(predicate=RDF.type, object=OWL.Ontology):
            return str(ontology)

        # If no explicit declaration, try to infer from imports
        for _, _, obj in graph.triples((None, OWL.imports, None)):
            # The importing ontology is likely the main one
            for s in graph.subjects(predicate=OWL.imports, object=obj):
                return str(s)

        return None

    def _extract_title(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> str:
        """Extract ontology title.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Ontology title
        """
        if ontology_ref:
            # Try DC title
            for title in graph.objects(subject=ontology_ref, predicate=self.dc.title):
                return str(title)

            # Try DCTERMS title
            for title in graph.objects(subject=ontology_ref, predicate=self.dcterms.title):
                return str(title)

            # Try RDFS label
            for label in graph.objects(subject=ontology_ref, predicate=RDFS.label):
                return str(label)

        # Default to "Untitled Ontology"
        return "Untitled Ontology"

    def _extract_description(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[str]:
        """Extract ontology description.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Description or None
        """
        if ontology_ref:
            # Try DC description
            for desc in graph.objects(subject=ontology_ref, predicate=self.dc.description):
                return str(desc)

            # Try DCTERMS description
            for desc in graph.objects(subject=ontology_ref, predicate=self.dcterms.description):
                return str(desc)

            # Try RDFS comment
            for comment in graph.objects(subject=ontology_ref, predicate=RDFS.comment):
                return str(comment)

        return None

    def _extract_creators(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> List[str]:
        """Extract ontology creators.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            List of creator names
        """
        creators = []

        if ontology_ref:
            # Try DC creator
            for creator in graph.objects(subject=ontology_ref, predicate=self.dc.creator):
                creators.append(str(creator))

            # Try DCTERMS creator
            for creator in graph.objects(subject=ontology_ref, predicate=self.dcterms.creator):
                if str(creator) not in creators:
                    creators.append(str(creator))

        return creators

    def _extract_created_date(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[datetime]:
        """Extract creation date.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Creation datetime or None
        """
        if ontology_ref:
            # Try DCTERMS created
            for created in graph.objects(subject=ontology_ref, predicate=self.dcterms.created):
                return self._parse_date(str(created))

            # Try DC date
            for date in graph.objects(subject=ontology_ref, predicate=self.dc.date):
                return self._parse_date(str(date))

        return None

    def _extract_modified_date(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[datetime]:
        """Extract modification date.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Modification datetime or None
        """
        if ontology_ref:
            # Try DCTERMS modified
            for modified in graph.objects(subject=ontology_ref, predicate=self.dcterms.modified):
                return self._parse_date(str(modified))

        return None

    def _extract_version_info(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[str]:
        """Extract version info.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Version info string or None
        """
        if ontology_ref:
            for version in graph.objects(subject=ontology_ref, predicate=OWL.versionInfo):
                return str(version)

        return None

    def _extract_version_iri(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[str]:
        """Extract version IRI.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Version IRI or None
        """
        if ontology_ref:
            for version_iri in graph.objects(subject=ontology_ref, predicate=OWL.versionIRI):
                return str(version_iri)

        return None

    def _extract_license(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[str]:
        """Extract license information.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            License string or None
        """
        if ontology_ref:
            # Try DCTERMS license
            for license_info in graph.objects(subject=ontology_ref, predicate=self.dcterms.license):
                return str(license_info)

            # Try DC rights
            for rights in graph.objects(subject=ontology_ref, predicate=self.dc.rights):
                return str(rights)

        return None

    def _extract_imports(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> List[str]:
        """Extract imported ontologies.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            List of imported ontology URIs
        """
        imports = []

        if ontology_ref:
            for imported in graph.objects(subject=ontology_ref, predicate=OWL.imports):
                imports.append(str(imported))

        return imports

    def _extract_namespaces(self, graph: Graph) -> dict:
        """Extract namespace prefixes.

        Args:
            graph: RDF graph

        Returns:
            Dictionary of prefix -> namespace mappings
        """
        namespaces = {}

        for prefix, namespace in graph.namespaces():
            if prefix:
                namespaces[prefix] = str(namespace)

        return namespaces

    def _extract_language(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[str]:
        """Extract language.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Language code or None
        """
        if ontology_ref:
            for lang in graph.objects(subject=ontology_ref, predicate=self.dc.language):
                return str(lang)

        return None

    def _extract_subject(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[str]:
        """Extract subject/topic.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Subject string or None
        """
        if ontology_ref:
            for subject in graph.objects(subject=ontology_ref, predicate=self.dc.subject):
                return str(subject)

        return None

    def _extract_publisher(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[str]:
        """Extract publisher.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Publisher string or None
        """
        if ontology_ref:
            for publisher in graph.objects(subject=ontology_ref, predicate=self.dc.publisher):
                return str(publisher)

        return None

    def _extract_rights(self, graph: Graph, ontology_ref: Optional[rdflib.URIRef]) -> Optional[str]:
        """Extract rights information.

        Args:
            graph: RDF graph
            ontology_ref: Ontology URI reference

        Returns:
            Rights string or None
        """
        if ontology_ref:
            for rights in graph.objects(subject=ontology_ref, predicate=self.dcterms.rights):
                return str(rights)

        return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime.

        Args:
            date_str: Date string

        Returns:
            Datetime object or None
        """
        # Try common date formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Unable to parse date: {date_str}")
        return None
