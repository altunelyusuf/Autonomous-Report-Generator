"""Abstract interface for research services."""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.research.models import ResearchContext, SearchResult


class IResearchService(ABC):
    """Abstract interface for knowledge source research services.

    This interface defines the contract that all research service
    implementations must follow. Different services (web search,
    academic APIs, Wikidata) implement this interface.

    All implementations should:
    - Be async for concurrent execution
    - Handle errors gracefully
    - Return standardized SearchResult objects
    - Track reliability metrics
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        context: Optional[ResearchContext] = None,
    ) -> List[SearchResult]:
        """Search knowledge source for query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            context: Optional research context for filtering/guidance

        Returns:
            List of search results

        Raises:
            ResearchException: If search fails
            ValidationException: If query is invalid
            TimeoutException: If search times out
        """
        pass

    @abstractmethod
    def get_reliability_score(self) -> float:
        """Get reliability score of this source.

        Returns:
            Reliability score (0.0 to 1.0)
        """
        pass

    @abstractmethod
    async def validate_access(self) -> bool:
        """Validate that source is accessible.

        Returns:
            True if source is accessible, False otherwise
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get human-readable source name.

        Returns:
            Source name (e.g., "Wikipedia", "Semantic Scholar")
        """
        pass

    @abstractmethod
    def get_source_type(self) -> str:
        """Get source type identifier.

        Returns:
            Source type (e.g., "web", "academic", "wikidata")
        """
        pass

    def supports_advanced_search(self) -> bool:
        """Check if source supports advanced search features.

        Returns:
            True if advanced search is supported
        """
        return False

    def get_rate_limit(self) -> Optional[int]:
        """Get rate limit for this source.

        Returns:
            Requests per minute limit, or None if no limit
        """
        return None

    def get_cost_per_query(self) -> float:
        """Get estimated cost per query.

        Returns:
            Cost in USD, or 0.0 if free
        """
        return 0.0
