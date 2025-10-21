"""Section numbering system for reports."""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SectionNumberGenerator:
    """Generate hierarchical section numbers.

    Generates section numbers in formats like:
    - 1, 2, 3 (level 1)
    - 1.1, 1.2, 1.3 (level 2)
    - 1.1.1, 1.1.2 (level 3)
    - etc.

    Features:
    - Maintains state across multiple sections
    - Automatic level tracking
    - Reset capability
    - Multiple numbering styles
    """

    def __init__(self, style: str = "decimal"):
        """Initialize section number generator.

        Args:
            style: Numbering style ('decimal', 'roman', 'alphabetic')
                   Currently only 'decimal' is implemented
        """
        self.style = style
        self._counters: Dict[int, int] = {}  # level -> current count
        self._reset()

    def _reset(self) -> None:
        """Reset all counters."""
        self._counters = {i: 0 for i in range(1, 11)}  # Support up to 10 levels

    def reset(self) -> None:
        """Public reset method."""
        self._reset()
        logger.debug("Section numbering reset")

    def get_next_number(self, level: int) -> str:
        """Get next section number for given level.

        Args:
            level: Hierarchy level (1-based)

        Returns:
            Section number string (e.g., "1.2.3")

        Raises:
            ValueError: If level is invalid
        """
        if level < 1 or level > 10:
            raise ValueError(f"Invalid level: {level}. Must be between 1 and 10.")

        # Increment counter for this level
        self._counters[level] += 1

        # Reset counters for deeper levels
        for deeper_level in range(level + 1, 11):
            self._counters[deeper_level] = 0

        # Build number string
        number_parts = []
        for i in range(1, level + 1):
            number_parts.append(str(self._counters[i]))

        number = ".".join(number_parts)

        logger.debug(f"Generated section number: {number} (level {level})")
        return number

    def get_current_number(self, level: int) -> str:
        """Get current section number for given level without incrementing.

        Args:
            level: Hierarchy level

        Returns:
            Current section number string

        Raises:
            ValueError: If level is invalid
        """
        if level < 1 or level > 10:
            raise ValueError(f"Invalid level: {level}. Must be between 1 and 10.")

        # Build number string
        number_parts = []
        for i in range(1, level + 1):
            number_parts.append(str(self._counters[i]))

        return ".".join(number_parts)

    def peek_next_number(self, level: int) -> str:
        """Preview what the next number would be without incrementing.

        Args:
            level: Hierarchy level

        Returns:
            Preview of next section number

        Raises:
            ValueError: If level is invalid
        """
        if level < 1 or level > 10:
            raise ValueError(f"Invalid level: {level}. Must be between 1 and 10.")

        # Build number string with next count
        number_parts = []
        for i in range(1, level + 1):
            if i == level:
                number_parts.append(str(self._counters[i] + 1))
            else:
                number_parts.append(str(self._counters[i]))

        return ".".join(number_parts)

    def get_parent_number(self, section_number: str) -> str:
        """Get parent section number from a section number.

        Args:
            section_number: Section number (e.g., "1.2.3")

        Returns:
            Parent section number (e.g., "1.2")
            Returns empty string if no parent (top-level section)
        """
        parts = section_number.split(".")
        if len(parts) <= 1:
            return ""

        return ".".join(parts[:-1])

    def get_level_from_number(self, section_number: str) -> int:
        """Get hierarchy level from section number.

        Args:
            section_number: Section number (e.g., "1.2.3")

        Returns:
            Hierarchy level (e.g., 3)
        """
        return len(section_number.split("."))

    def format_section_header(self, section_number: str, title: str) -> str:
        """Format a complete section header.

        Args:
            section_number: Section number
            title: Section title

        Returns:
            Formatted header (e.g., "1.2.3 Introduction")
        """
        return f"{section_number} {title}"

    def is_subsection_of(self, child: str, parent: str) -> bool:
        """Check if one section is a subsection of another.

        Args:
            child: Potential child section number
            parent: Potential parent section number

        Returns:
            True if child is subsection of parent
        """
        if not child.startswith(parent + "."):
            return False

        # Check it's a direct relationship (not a grandchild)
        child_parts = child.split(".")
        parent_parts = parent.split(".")

        return len(child_parts) == len(parent_parts) + 1

    def is_descendant_of(self, descendant: str, ancestor: str) -> bool:
        """Check if one section is a descendant of another (any level).

        Args:
            descendant: Potential descendant section number
            ancestor: Potential ancestor section number

        Returns:
            True if descendant is under ancestor
        """
        return descendant.startswith(ancestor + ".")

    def compare_sections(self, section1: str, section2: str) -> int:
        """Compare two section numbers for ordering.

        Args:
            section1: First section number
            section2: Second section number

        Returns:
            -1 if section1 < section2
             0 if section1 == section2
             1 if section1 > section2
        """
        parts1 = [int(p) for p in section1.split(".")]
        parts2 = [int(p) for p in section2.split(".")]

        # Compare level by level
        for i in range(max(len(parts1), len(parts2))):
            val1 = parts1[i] if i < len(parts1) else 0
            val2 = parts2[i] if i < len(parts2) else 0

            if val1 < val2:
                return -1
            elif val1 > val2:
                return 1

        return 0

    def sort_section_numbers(self, section_numbers: List[str]) -> List[str]:
        """Sort section numbers in proper order.

        Args:
            section_numbers: List of section numbers

        Returns:
            Sorted list
        """
        from functools import cmp_to_key

        return sorted(section_numbers, key=cmp_to_key(self.compare_sections))


class AlternativeNumberingStyles:
    """Alternative numbering style generators.

    Provides different numbering formats for various document types.
    """

    @staticmethod
    def roman_numeral(number: int, lowercase: bool = False) -> str:
        """Convert number to Roman numeral.

        Args:
            number: Integer to convert
            lowercase: Use lowercase numerals

        Returns:
            Roman numeral string
        """
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]

        roman_num = ""
        i = 0
        while number > 0:
            for _ in range(number // val[i]):
                roman_num += syms[i]
                number -= val[i]
            i += 1

        return roman_num.lower() if lowercase else roman_num

    @staticmethod
    def alphabetic(number: int, lowercase: bool = True) -> str:
        """Convert number to alphabetic label.

        Args:
            number: Integer to convert (1-26)
            lowercase: Use lowercase letters

        Returns:
            Alphabetic label
        """
        if number < 1 or number > 26:
            raise ValueError("Number must be between 1 and 26 for alphabetic")

        char = chr(ord("a" if lowercase else "A") + number - 1)
        return char
