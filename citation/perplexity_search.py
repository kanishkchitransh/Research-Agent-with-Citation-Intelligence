"""Perplexity Search API integration for finding academic papers.

This module uses Perplexity's search API to find papers across the web.
Perplexity is excellent for academic content as it provides citations and sources.
"""

import json
import os
from typing import List, Optional

import requests
from loguru import logger


class PerplexitySearchResult:
    """A search result from Perplexity."""

    def __init__(self, title: str, link: str, snippet: str):
        self.title = title
        self.link = link
        self.snippet = snippet

    def __repr__(self) -> str:
        return f"PerplexitySearchResult(title='{self.title[:50]}...', link='{self.link}')"


class PaperPerplexitySearch:
    """
    Search for academic papers using Perplexity Search API.

    Perplexity is excellent for academic content as it:
    - Searches multiple academic databases
    - Provides high-quality sources
    - Returns citations automatically
    - Has good understanding of research papers
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Perplexity Search.

        Args:
            api_key: Perplexity API key (or set PERPLEXITY_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.api_url = "https://api.perplexity.ai/chat/completions"

        if not self.api_key:
            logger.warning(
                "Perplexity API key not provided. Set PERPLEXITY_API_KEY or pass api_key parameter."
            )
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Perplexity Search initialized")

    def search_paper(
        self, query: str, num_results: int = 10
    ) -> List[PerplexitySearchResult]:
        """
        Search for a paper using Perplexity Search API.

        Args:
            query: Search query (paper title, author, etc.)
            num_results: Number of results to return (informational, Perplexity decides)

        Returns:
            List of PerplexitySearchResult objects
        """
        if not self.enabled:
            logger.warning("Perplexity Search not initialized")
            return []

        try:
            # Build search prompt
            prompt = f"""Find academic papers related to: {query}

IMPORTANT: Prioritize links from these sources (in order):
1. ArXiv.org (arxiv.org/abs/ or arxiv.org/pdf/)
2. Google Scholar PDF links
3. ResearchGate
4. Open access repositories
5. IEEE Xplore or ACM (as last resort)

Please provide:
1. The paper title
2. Direct link to the paper
3. A brief description

Format each result as:
TITLE: [title]
URL: [url]
DESCRIPTION: [description]

Provide up to {num_results} results."""

            # Call Perplexity API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "sonar",  # Perplexity Sonar with web search
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a research assistant helping to find academic papers. Always provide direct URLs to papers.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 1000,
            }

            response = requests.post(
                self.api_url, json=payload, headers=headers, timeout=30
            )
            response.raise_for_status()

            data = response.json()

            # Parse response
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]

                # Parse structured results
                results = self._parse_results(content)

                logger.info(f"Found {len(results)} results via Perplexity for: {query[:50]}")
                return results
            else:
                logger.warning("No results from Perplexity API")
                return []

        except Exception as e:
            logger.error(f"Error searching Perplexity: {e}")
            return []

    def search_paper_by_citation(
        self, citation_marker: str, context: Optional[str] = None
    ) -> List[PerplexitySearchResult]:
        """
        Search for a paper using citation marker and context.

        Args:
            citation_marker: Citation string (e.g., "(Smith et al., 2020)")
            context: Optional context around citation

        Returns:
            List of PerplexitySearchResult objects
        """
        # Build search query
        clean_marker = citation_marker.strip("()[],")

        if context:
            # Extract keywords from context
            keywords = self._extract_keywords(context)
            query = f"{clean_marker} {' '.join(keywords[:2])} academic paper"
        else:
            query = f"{clean_marker} academic paper research"

        return self.search_paper(query)

    def _parse_results(self, content: str) -> List[PerplexitySearchResult]:
        """Parse Perplexity response into structured results."""
        results = []

        # Split by results (each starts with TITLE:)
        sections = content.split("TITLE:")

        for section in sections[1:]:  # Skip first empty section
            try:
                lines = section.strip().split("\n")

                title = ""
                url = ""
                description = ""

                for line in lines:
                    if line.startswith("URL:"):
                        url = line.replace("URL:", "").strip()
                    elif line.startswith("DESCRIPTION:"):
                        description = line.replace("DESCRIPTION:", "").strip()
                    elif not line.startswith(("URL:", "DESCRIPTION:")):
                        # Part of title
                        title += line.strip() + " "

                title = title.strip()

                if title and url:
                    results.append(
                        PerplexitySearchResult(
                            title=title, link=url, snippet=description
                        )
                    )

            except Exception as e:
                logger.warning(f"Error parsing result section: {e}")
                continue

        # If structured parsing fails, try to extract URLs directly
        if not results:
            results = self._extract_urls_fallback(content)

        return results

    def _extract_urls_fallback(self, content: str) -> List[PerplexitySearchResult]:
        """Fallback: Extract any URLs that look like paper sources."""
        import re

        results = []

        # Find URLs that look like academic sources
        url_patterns = [
            r"https?://arxiv\.org/[^\s]+",
            r"https?://(?:www\.)?ieee[^\s]+",
            r"https?://dl\.acm\.org[^\s]+",
            r"https?://scholar\.google[^\s]+",
            r"https?://[^\s]+\.pdf",
        ]

        for pattern in url_patterns:
            urls = re.findall(pattern, content)
            for url in urls:
                # Clean URL (remove trailing punctuation)
                url = url.rstrip(".,;:)")

                results.append(
                    PerplexitySearchResult(
                        title="Academic Paper", link=url, snippet=content[:200]
                    )
                )

        return results[:5]  # Limit to 5 results

    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 3) -> List[str]:
        """Extract meaningful keywords from text."""
        import re

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

        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        keywords = [w for w in words if w not in stopwords]

        return list(dict.fromkeys(keywords))[:max_keywords]
