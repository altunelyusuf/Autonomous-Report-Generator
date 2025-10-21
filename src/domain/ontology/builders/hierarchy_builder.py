"""Class hierarchy builder for ontologies."""

import logging
from typing import Dict, List, Set

from src.domain.ontology.exceptions import CircularInheritanceException
from src.domain.ontology.models import ClassHierarchy, OntologyClass

logger = logging.getLogger(__name__)


class ClassHierarchyBuilder:
    """Build class hierarchy tree from ontology classes.

    Features:
    - Builds parent-child relationships
    - Detects circular inheritance
    - Calculates hierarchy depth
    - Identifies root and leaf classes
    """

    def __init__(self):
        """Initialize hierarchy builder."""
        pass

    def build_hierarchy(self, classes: List[OntologyClass]) -> ClassHierarchy:
        """Build complete class hierarchy.

        Args:
            classes: List of ontology classes

        Returns:
            ClassHierarchy object

        Raises:
            CircularInheritanceException: If circular inheritance detected
        """
        logger.info(f"Building hierarchy for {len(classes)} classes")

        # Step 1: Create class index
        class_index = self._create_class_index(classes)

        # Step 2: Build parent-child relationships
        self._build_relationships(classes, class_index)

        # Step 3: Detect cycles
        self._detect_cycles(classes)

        # Step 4: Find root classes
        roots = self._find_roots(classes)

        logger.info(f"Found {len(roots)} root classes")

        # Step 5: Calculate depths
        for root in roots:
            self._calculate_depth(root, 0)

        # Step 6: Create hierarchy
        hierarchy = ClassHierarchy(roots=roots)
        hierarchy.calculate_statistics()

        logger.info(
            f"Hierarchy built: max_depth={hierarchy.max_depth}, "
            f"total_classes={hierarchy.total_classes}"
        )

        return hierarchy

    def _create_class_index(self, classes: List[OntologyClass]) -> Dict[str, OntologyClass]:
        """Create URI -> class mapping.

        Args:
            classes: List of classes

        Returns:
            Dictionary mapping URIs to classes
        """
        return {cls.uri: cls for cls in classes}

    def _build_relationships(
        self, classes: List[OntologyClass], class_index: Dict[str, OntologyClass]
    ) -> None:
        """Build parent-child relationships.

        Args:
            classes: List of classes
            class_index: URI to class mapping
        """
        for cls in classes:
            # Process each superclass
            for parent_uri in cls.subclass_of:
                if parent_uri in class_index:
                    parent = class_index[parent_uri]
                    # Add bidirectional relationship
                    parent.add_child(cls)
                    cls.add_parent(parent)
                else:
                    logger.warning(
                        f"Parent class {parent_uri} not found for {cls.uri}"
                    )

    def _detect_cycles(self, classes: List[OntologyClass]) -> None:
        """Detect circular inheritance using DFS.

        Args:
            classes: List of classes

        Raises:
            CircularInheritanceException: If cycle detected
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        for cls in classes:
            if cls.uri not in visited:
                if self._has_cycle_dfs(cls, visited, rec_stack):
                    raise CircularInheritanceException(cls.uri)

    def _has_cycle_dfs(
        self, cls: OntologyClass, visited: Set[str], rec_stack: Set[str]
    ) -> bool:
        """DFS-based cycle detection.

        Args:
            cls: Current class
            visited: Set of visited class URIs
            rec_stack: Recursion stack

        Returns:
            True if cycle detected
        """
        visited.add(cls.uri)
        rec_stack.add(cls.uri)

        # Visit all children
        for child in cls.children:
            if child.uri not in visited:
                if self._has_cycle_dfs(child, visited, rec_stack):
                    return True
            elif child.uri in rec_stack:
                # Back edge found - cycle detected
                return True

        rec_stack.remove(cls.uri)
        return False

    def _find_roots(self, classes: List[OntologyClass]) -> List[OntologyClass]:
        """Find root classes (classes with no parents).

        Args:
            classes: List of classes

        Returns:
            List of root classes
        """
        roots = [cls for cls in classes if cls.is_root()]

        # Sort roots by label for consistent ordering
        roots.sort(key=lambda cls: cls.label)

        return roots

    def _calculate_depth(self, cls: OntologyClass, depth: int) -> None:
        """Recursively calculate depth for class and descendants.

        Args:
            cls: Current class
            depth: Current depth
        """
        cls.depth = depth

        # Calculate depth for all children
        for child in cls.children:
            self._calculate_depth(child, depth + 1)

    def get_class_path(self, cls: OntologyClass) -> List[OntologyClass]:
        """Get path from root to class.

        Args:
            cls: Target class

        Returns:
            List of classes from root to target
        """
        path = [cls]
        current = cls

        while current.parents:
            # Take first parent (handle multiple inheritance)
            parent = current.parents[0]
            path.insert(0, parent)
            current = parent

        return path

    def get_descendants(self, cls: OntologyClass) -> List[OntologyClass]:
        """Get all descendants of a class.

        Args:
            cls: Parent class

        Returns:
            List of all descendant classes
        """
        descendants = []

        def collect_descendants(current: OntologyClass) -> None:
            for child in current.children:
                descendants.append(child)
                collect_descendants(child)

        collect_descendants(cls)
        return descendants

    def get_ancestors(self, cls: OntologyClass) -> List[OntologyClass]:
        """Get all ancestors of a class.

        Args:
            cls: Target class

        Returns:
            List of all ancestor classes
        """
        ancestors = []
        visited = set()

        def collect_ancestors(current: OntologyClass) -> None:
            for parent in current.parents:
                if parent.uri not in visited:
                    visited.add(parent.uri)
                    ancestors.append(parent)
                    collect_ancestors(parent)

        collect_ancestors(cls)
        return ancestors

    def find_common_ancestor(
        self, cls1: OntologyClass, cls2: OntologyClass
    ) -> OntologyClass | None:
        """Find lowest common ancestor of two classes.

        Args:
            cls1: First class
            cls2: Second class

        Returns:
            Common ancestor or None
        """
        ancestors1 = set(self.get_ancestors(cls1))
        ancestors2 = set(self.get_ancestors(cls2))

        common = ancestors1.intersection(ancestors2)

        if not common:
            return None

        # Return the one with maximum depth (lowest in tree)
        return max(common, key=lambda cls: cls.depth)
