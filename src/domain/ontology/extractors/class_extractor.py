"""Class extractor for ontologies."""

import logging
from typing import Dict, List

import rdflib
from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS

from src.domain.ontology.models import ClassRestriction, OntologyClass

logger = logging.getLogger(__name__)


class ClassExtractor:
    """Extract OWL classes from ontology graphs."""

    def __init__(self):
        """Initialize class extractor."""
        self.owl = OWL
        self.rdf = RDF
        self.rdfs = RDFS

    def extract_classes(self, graph: Graph) -> List[OntologyClass]:
        """Extract all OWL classes from graph.

        Args:
            graph: RDF graph

        Returns:
            List of OntologyClass objects
        """
        logger.info("Extracting ontology classes")

        classes = []
        class_uris = self._find_class_uris(graph)

        logger.info(f"Found {len(class_uris)} classes")

        for class_uri in class_uris:
            ont_class = self._extract_class(graph, class_uri)
            classes.append(ont_class)

        logger.info(f"Extracted {len(classes)} classes")
        return classes

    def _find_class_uris(self, graph: Graph) -> List[str]:
        """Find all class URIs in the graph.

        Args:
            graph: RDF graph

        Returns:
            List of class URI strings
        """
        class_uris = set()

        # Find explicit owl:Class declarations
        for class_uri in graph.subjects(predicate=RDF.type, object=OWL.Class):
            class_uris.add(str(class_uri))

        # Find rdfs:Class declarations
        for class_uri in graph.subjects(predicate=RDF.type, object=RDFS.Class):
            class_uris.add(str(class_uri))

        # Find classes mentioned as subjects in subClassOf
        for class_uri in graph.subjects(predicate=RDFS.subClassOf):
            class_uris.add(str(class_uri))

        # Find classes mentioned as objects in subClassOf
        for class_uri in graph.objects(predicate=RDFS.subClassOf):
            if isinstance(class_uri, rdflib.URIRef):
                class_uris.add(str(class_uri))

        return list(class_uris)

    def _extract_class(self, graph: Graph, class_uri: str) -> OntologyClass:
        """Extract a single class.

        Args:
            graph: RDF graph
            class_uri: Class URI

        Returns:
            OntologyClass object
        """
        class_ref = rdflib.URIRef(class_uri)

        # Extract basic information
        label = self._extract_label(graph, class_ref)
        comment = self._extract_comment(graph, class_ref)

        # Extract relationships
        subclass_of = self._extract_subclass_of(graph, class_ref)
        equivalent_to = self._extract_equivalent_classes(graph, class_ref)
        disjoint_with = self._extract_disjoint_classes(graph, class_ref)

        # Extract annotations
        annotations = self._extract_annotations(graph, class_ref)

        # Extract restrictions
        restrictions = self._extract_restrictions(graph, class_ref)

        # Check if deprecated
        deprecated = self._is_deprecated(graph, class_ref)

        return OntologyClass(
            uri=class_uri,
            label=label,
            comment=comment,
            subclass_of=subclass_of,
            equivalent_to=equivalent_to,
            disjoint_with=disjoint_with,
            annotations=annotations,
            restrictions=restrictions,
            deprecated=deprecated,
        )

    def _extract_label(self, graph: Graph, class_ref: rdflib.URIRef) -> str:
        """Extract class label.

        Args:
            graph: RDF graph
            class_ref: Class URI reference

        Returns:
            Label string (or URI local name if no label found)
        """
        # Try RDFS label
        for label in graph.objects(subject=class_ref, predicate=RDFS.label):
            return str(label)

        # Fallback to local name from URI
        local_name = class_ref.split("#")[-1].split("/")[-1]
        return local_name

    def _extract_comment(self, graph: Graph, class_ref: rdflib.URIRef) -> str | None:
        """Extract class comment/description.

        Args:
            graph: RDF graph
            class_ref: Class URI reference

        Returns:
            Comment string or None
        """
        for comment in graph.objects(subject=class_ref, predicate=RDFS.comment):
            return str(comment)
        return None

    def _extract_subclass_of(self, graph: Graph, class_ref: rdflib.URIRef) -> List[str]:
        """Extract superclasses.

        Args:
            graph: RDF graph
            class_ref: Class URI reference

        Returns:
            List of superclass URIs
        """
        superclasses = []

        for superclass in graph.objects(subject=class_ref, predicate=RDFS.subClassOf):
            if isinstance(superclass, rdflib.URIRef):
                superclasses.append(str(superclass))
            # Skip blank nodes (restrictions) for now

        return superclasses

    def _extract_equivalent_classes(self, graph: Graph, class_ref: rdflib.URIRef) -> List[str]:
        """Extract equivalent classes.

        Args:
            graph: RDF graph
            class_ref: Class URI reference

        Returns:
            List of equivalent class URIs
        """
        equivalent = []

        for equiv_class in graph.objects(subject=class_ref, predicate=OWL.equivalentClass):
            if isinstance(equiv_class, rdflib.URIRef):
                equivalent.append(str(equiv_class))

        return equivalent

    def _extract_disjoint_classes(self, graph: Graph, class_ref: rdflib.URIRef) -> List[str]:
        """Extract disjoint classes.

        Args:
            graph: RDF graph
            class_ref: Class URI reference

        Returns:
            List of disjoint class URIs
        """
        disjoint = []

        for disj_class in graph.objects(subject=class_ref, predicate=OWL.disjointWith):
            if isinstance(disj_class, rdflib.URIRef):
                disjoint.append(str(disj_class))

        return disjoint

    def _extract_annotations(self, graph: Graph, class_ref: rdflib.URIRef) -> Dict[str, List[str]]:
        """Extract annotations.

        Args:
            graph: RDF graph
            class_ref: Class URI reference

        Returns:
            Dictionary of annotation property -> values
        """
        annotations: Dict[str, List[str]] = {}

        # Get all predicates for this class
        for pred, obj in graph.predicate_objects(subject=class_ref):
            # Skip standard RDF/RDFS/OWL predicates
            pred_str = str(pred)
            if any(pred_str.startswith(ns) for ns in [str(RDF), str(RDFS), str(OWL)]):
                continue

            # Add annotation
            if pred_str not in annotations:
                annotations[pred_str] = []
            annotations[pred_str].append(str(obj))

        return annotations

    def _extract_restrictions(self, graph: Graph, class_ref: rdflib.URIRef) -> List[ClassRestriction]:
        """Extract class restrictions.

        Args:
            graph: RDF graph
            class_ref: Class URI reference

        Returns:
            List of ClassRestriction objects
        """
        restrictions = []

        # Find blank node restrictions in subClassOf
        for restriction in graph.objects(subject=class_ref, predicate=RDFS.subClassOf):
            if isinstance(restriction, rdflib.BNode):
                rest = self._parse_restriction(graph, restriction)
                if rest:
                    restrictions.append(rest)

        return restrictions

    def _parse_restriction(self, graph: Graph, restriction_node: rdflib.BNode) -> ClassRestriction | None:
        """Parse a restriction blank node.

        Args:
            graph: RDF graph
            restriction_node: Blank node representing restriction

        Returns:
            ClassRestriction or None
        """
        # Check if it's actually a restriction
        is_restriction = False
        for _ in graph.triples((restriction_node, RDF.type, OWL.Restriction)):
            is_restriction = True
            break

        if not is_restriction:
            return None

        # Extract restriction details
        on_property = None
        restriction_type = None
        value = None
        cardinality = None

        # Get property
        for prop in graph.objects(subject=restriction_node, predicate=OWL.onProperty):
            on_property = str(prop)

        if not on_property:
            return None

        # Check restriction type
        for val in graph.objects(subject=restriction_node, predicate=OWL.someValuesFrom):
            restriction_type = "someValuesFrom"
            value = str(val)

        for val in graph.objects(subject=restriction_node, predicate=OWL.allValuesFrom):
            restriction_type = "allValuesFrom"
            value = str(val)

        for val in graph.objects(subject=restriction_node, predicate=OWL.hasValue):
            restriction_type = "hasValue"
            value = str(val)

        for card in graph.objects(subject=restriction_node, predicate=OWL.cardinality):
            cardinality = int(card)
            restriction_type = "cardinality"

        if restriction_type:
            return ClassRestriction(
                restriction_type=restriction_type,
                on_property=on_property,
                value=value,
                cardinality=cardinality,
            )

        return None

    def _is_deprecated(self, graph: Graph, class_ref: rdflib.URIRef) -> bool:
        """Check if class is deprecated.

        Args:
            graph: RDF graph
            class_ref: Class URI reference

        Returns:
            True if deprecated
        """
        for deprecated in graph.objects(subject=class_ref, predicate=OWL.deprecated):
            return str(deprecated).lower() in ("true", "1")

        return False
