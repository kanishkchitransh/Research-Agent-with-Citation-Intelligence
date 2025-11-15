"""Google Custom Search API integration for finding academic papers.

This module uses Google Custom Search API to find papers across the web.
"""

import os
from typing import List, Optional

from googleapiclient.discovery import build
from loguru import logger


class GoogleSearchResult:
    """A single search result from Google."""

    def __init__(self, title: str, link: str, snippet: str):
        self.title = title
        self.link = link
        self.snippet = snippet

    def __repr__(self) -> str:
        return f"GoogleSearchResult(title='{self.title[:50]}...', link='{self.link}')"


class PaperGoogleSearch:
    """
    Search for academic papers using Google Custom Search API.

    Note: Requires Google Custom Search API key and Search Engine ID.
    Free tier: 100 queries/day
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
    ):
        """
        Initialize Google Custom Search.

        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            search_engine_id: Custom Search Engine ID (or set GOOGLE_CSE_ID env var)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = search_engine_id or os.getenv(
            "GOOGLE_CSE_ID", "017576662512468239146:omuauf_lfve"
        )

        if not self.api_key:
            logger.warning(
                "Google API key not provided. Set GOOGLE_API_KEY or pass api_key parameter."
            )
            self.service = None
        else:
            try:
                self.service = build("customsearch", "v1", developerKey=self.api_key)
                logger.info("Google Custom Search initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Google Custom Search: {e}")
                self.service = None

    def search_paper(
        self, query: str, num_results: int = 5
    ) -> List[GoogleSearchResult]:
        """
        Search for a paper using Google Custom Search.

        Args:
            query: Search query (paper title, author, etc.)
            num_results: Number of results to return (max 10)

        Returns:
            List of GoogleSearchResult objects
        """
        if not self.service:
            logger.warning("Google Custom Search not initialized")
            return []

        try:
            # Execute search
            result = (
                self.service.cse()
                .list(
                    q=query,
                    cx=self.search_engine_id,
                    num=min(num_results, 10),  # API max is 10
                )
                .execute()
            )

            # Parse results
            search_results = []
            if "items" in result:
                for item in result["items"]:
                    search_result = GoogleSearchResult(
                        title=item.get("title", ""),
                        link=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                    )
                    search_results.append(search_result)

            logger.info(f"Found {len(search_results)} results for query: {query[:50]}")
            return search_results

        except Exception as e:
            logger.error(f"Error searching Google: {e}")
            return []

    def search_paper_by_citation(
        self, citation_marker: str, context: Optional[str] = None
    ) -> List[GoogleSearchResult]:
        """
        Search for a paper using citation marker and context.

        Args:
            citation_marker: Citation string (e.g., "(Smith et al., 2020)")
            context: Optional context around citation

        Returns:
            List of GoogleSearchResult objects
        """
        # Build search query
        query_parts = []

        # Add citation marker (cleaned)
        clean_marker = citation_marker.strip("()[],")
        query_parts.append(clean_marker)

        # Add context keywords if available
        if context:
            # Extract meaningful keywords from context
            keywords = self._extract_keywords(context)
            if keywords:
                query_parts.extend(keywords[:2])  # Add top 2 keywords

        # Add academic source filters
        query = " ".join(query_parts)
        query += " (arxiv OR ieee OR acm OR scholar OR pdf OR paper)"

        return self.search_paper(query)

    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 3) -> List[str]:
        """Extract meaningful keywords from text."""
        import re

        # Remove common words
        stopwords = {
            "the",
            "a",
            "an",
            "in",
            "on",
            "at",
            "for",
            "to",
            "of",
            "and",
            "or",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "this",
            "that",
            "these",
            "those",
        }

        # Extract words (4+ characters)
        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        keywords = [w for w in words if w not in stopwords]

        # Return unique keywords
        return list(dict.fromkeys(keywords))[:max_keywords]
