"""Domain models for ontology processing."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class OntologyFormat(Enum):
    """Supported ontology formats."""

    OWL = "owl"
    RDF = "rdf"
    TTL = "ttl"
    N3 = "n3"
    JSONLD = "jsonld"


@dataclass
class OntologyMetadata:
    """Ontology metadata (Dublin Core + OWL)."""

    title: str
    description: Optional[str] = None
    creator: List[str] = field(default_factory=list)
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    version_info: Optional[str] = None
    version_iri: Optional[str] = None
    license: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    namespaces: Dict[str, str] = field(default_factory=dict)
    language: Optional[str] = None
    subject: Optional[str] = None
    publisher: Optional[str] = None
    rights: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "creator": self.creator,
            "created": self.created.isoformat() if self.created else None,
            "modified": self.modified.isoformat() if self.modified else None,
            "version_info": self.version_info,
            "version_iri": self.version_iri,
            "license": self.license,
            "imports": self.imports,
            "namespaces": self.namespaces,
            "language": self.language,
            "subject": self.subject,
            "publisher": self.publisher,
            "rights": self.rights,
        }


@dataclass
class ClassRestriction:
    """OWL class restriction."""

    restriction_type: str  # e.g., 'someValuesFrom', 'allValuesFrom', 'hasValue'
    on_property: str
    value: Any
    cardinality: Optional[int] = None
    min_cardinality: Optional[int] = None
    max_cardinality: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "restriction_type": self.restriction_type,
            "on_property": self.on_property,
            "value": str(self.value),
            "cardinality": self.cardinality,
            "min_cardinality": self.min_cardinality,
            "max_cardinality": self.max_cardinality,
        }


@dataclass
class OntologyClass:
    """Single ontology class."""

    uri: str
    label: str
    comment: Optional[str] = None
    subclass_of: List[str] = field(default_factory=list)
    equivalent_to: List[str] = field(default_factory=list)
    disjoint_with: List[str] = field(default_factory=list)
    annotations: Dict[str, List[str]] = field(default_factory=dict)
    restrictions: List[ClassRestriction] = field(default_factory=list)
    deprecated: bool = False

    # Hierarchy information (populated by ClassHierarchyBuilder)
    depth: int = 0
    children: List["OntologyClass"] = field(default_factory=list)
    parents: List["OntologyClass"] = field(default_factory=list)

    def add_child(self, child: "OntologyClass") -> None:
        """Add a child class."""
        if child not in self.children:
            self.children.append(child)

    def add_parent(self, parent: "OntologyClass") -> None:
        """Add a parent class."""
        if parent not in self.parents:
            self.parents.append(parent)

    def is_root(self) -> bool:
        """Check if this is a root class."""
        return len(self.parents) == 0

    def is_leaf(self) -> bool:
        """Check if this is a leaf class."""
        return len(self.children) == 0

    def get_ancestor_count(self) -> int:
        """Get total number of ancestors."""
        count = len(self.parents)
        for parent in self.parents:
            count += parent.get_ancestor_count()
        return count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uri": self.uri,
            "label": self.label,
            "comment": self.comment,
            "subclass_of": self.subclass_of,
            "equivalent_to": self.equivalent_to,
            "disjoint_with": self.disjoint_with,
            "annotations": self.annotations,
            "restrictions": [r.to_dict() for r in self.restrictions],
            "deprecated": self.deprecated,
            "depth": self.depth,
            "is_root": self.is_root(),
            "is_leaf": self.is_leaf(),
        }


@dataclass
class OntologyProperty:
    """Ontology property (object or data property)."""

    uri: str
    label: str
    property_type: str  # 'ObjectProperty', 'DatatypeProperty', 'AnnotationProperty'
    comment: Optional[str] = None
    domain: List[str] = field(default_factory=list)
    range: List[str] = field(default_factory=list)
    super_property: List[str] = field(default_factory=list)
    sub_property: List[str] = field(default_factory=list)
    inverse_of: Optional[str] = None
    is_functional: bool = False
    is_inverse_functional: bool = False
    is_transitive: bool = False
    is_symmetric: bool = False
    is_asymmetric: bool = False
    is_reflexive: bool = False
    is_irreflexive: bool = False
    annotations: Dict[str, List[str]] = field(default_factory=dict)
    deprecated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uri": self.uri,
            "label": self.label,
            "property_type": self.property_type,
            "comment": self.comment,
            "domain": self.domain,
            "range": self.range,
            "super_property": self.super_property,
            "sub_property": self.sub_property,
            "inverse_of": self.inverse_of,
            "is_functional": self.is_functional,
            "is_inverse_functional": self.is_inverse_functional,
            "is_transitive": self.is_transitive,
            "is_symmetric": self.is_symmetric,
            "is_asymmetric": self.is_asymmetric,
            "is_reflexive": self.is_reflexive,
            "is_irreflexive": self.is_irreflexive,
            "annotations": self.annotations,
            "deprecated": self.deprecated,
        }


@dataclass
class Individual:
    """Ontology individual/instance."""

    uri: str
    label: str
    types: List[str] = field(default_factory=list)
    same_as: List[str] = field(default_factory=list)
    different_from: List[str] = field(default_factory=list)
    properties: Dict[str, List[Any]] = field(default_factory=dict)
    annotations: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uri": self.uri,
            "label": self.label,
            "types": self.types,
            "same_as": self.same_as,
            "different_from": self.different_from,
            "properties": {k: [str(v) for v in vals] for k, vals in self.properties.items()},
            "annotations": self.annotations,
        }


@dataclass
class ClassHierarchy:
    """Class hierarchy tree structure."""

    roots: List[OntologyClass] = field(default_factory=list)
    max_depth: int = 0
    total_classes: int = 0

    def add_root(self, root: OntologyClass) -> None:
        """Add a root class."""
        if root not in self.roots:
            self.roots.append(root)

    def calculate_statistics(self) -> None:
        """Calculate hierarchy statistics."""
        self.max_depth = max((self._get_max_depth(root) for root in self.roots), default=0)
        self.total_classes = sum(
            (self._count_classes(root) for root in self.roots), start=0
        )

    def _get_max_depth(self, node: OntologyClass) -> int:
        """Get maximum depth from a node."""
        if not node.children:
            return node.depth
        return max(self._get_max_depth(child) for child in node.children)

    def _count_classes(self, node: OntologyClass) -> int:
        """Count classes in subtree."""
        count = 1
        for child in node.children:
            count += self._count_classes(child)
        return count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_depth": self.max_depth,
            "total_classes": self.total_classes,
            "root_classes": [root.to_dict() for root in self.roots],
        }


@dataclass
class OntologyStatistics:
    """Ontology statistics."""

    class_count: int = 0
    property_count: int = 0
    object_property_count: int = 0
    datatype_property_count: int = 0
    annotation_property_count: int = 0
    individual_count: int = 0
    axiom_count: int = 0
    max_hierarchy_depth: int = 0
    avg_children_per_class: float = 0.0
    avg_properties_per_class: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "class_count": self.class_count,
            "property_count": self.property_count,
            "object_property_count": self.object_property_count,
            "datatype_property_count": self.datatype_property_count,
            "annotation_property_count": self.annotation_property_count,
            "individual_count": self.individual_count,
            "axiom_count": self.axiom_count,
            "max_hierarchy_depth": self.max_hierarchy_depth,
            "avg_children_per_class": round(self.avg_children_per_class, 2),
            "avg_properties_per_class": round(self.avg_properties_per_class, 2),
        }


@dataclass
class OntologyStructure:
    """Complete ontology structure."""

    uri: str
    format: OntologyFormat
    metadata: OntologyMetadata
    classes: List[OntologyClass] = field(default_factory=list)
    properties: List[OntologyProperty] = field(default_factory=list)
    individuals: List[Individual] = field(default_factory=list)
    hierarchy: ClassHierarchy = field(default_factory=ClassHierarchy)
    statistics: OntologyStatistics = field(default_factory=OntologyStatistics)
    parsed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uri": self.uri,
            "format": self.format.value,
            "metadata": self.metadata.to_dict(),
            "classes": [cls.to_dict() for cls in self.classes],
            "properties": [prop.to_dict() for prop in self.properties],
            "individuals": [ind.to_dict() for ind in self.individuals],
            "hierarchy": self.hierarchy.to_dict(),
            "statistics": self.statistics.to_dict(),
            "parsed_at": self.parsed_at.isoformat(),
        }


@dataclass
class ValidationResult:
    """Validation result."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    score: Optional[float] = None

    def add_error(self, error: str) -> None:
        """Add an error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning."""
        self.warnings.append(warning)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "score": self.score,
        }
