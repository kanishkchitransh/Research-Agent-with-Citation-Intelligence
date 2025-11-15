"""Citation resolver using multiple sources.

This module resolves citation strings to actual papers using:
- Google Custom Search API (primary)
- Web scraping from multiple sources
- ArXiv API (fallback)
"""

import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import arxiv
from loguru import logger

from .google_search import PaperGoogleSearch
from .perplexity_search import PaperPerplexitySearch
from .web_scraper import PaperWebScraper


@dataclass
class ResolvedCitation:
    """Represents a resolved citation with paper metadata."""

    citation_marker: str
    title: str
    authors: List[str]
    abstract: str
    arxiv_id: str  # Optional, may be None for non-ArXiv papers
    published: str
    pdf_url: str
    match_score: float  # Confidence score (0-1)
    match_method: str  # How it was matched (google_search, web_scrape, arxiv_id, etc.)


class CitationResolver:
    """
    Resolves citations using multiple sources.

    Resolution Strategy (in order):
    1. ArXiv ID direct lookup (if present)
    2. ArXiv author-year search (fast for ArXiv papers)
    3. Google Custom Search + Web Scraping (works for any paper)
    4. ArXiv context search (fallback)
    """

    def __init__(
        self,
        max_results: int = 5,
        delay_between_requests: float = 1.0,
        google_api_key: Optional[str] = None,
        perplexity_api_key: Optional[str] = None,
    ):
        """
        Initialize the citation resolver.

        Args:
            max_results: Maximum results per search
            delay_between_requests: Delay between API calls (seconds)
            google_api_key: Google API key for Custom Search (optional)
            perplexity_api_key: Perplexity API key for search (optional, preferred)
        """
        self.max_results = max_results
        self.delay = delay_between_requests
        self._last_request_time = 0.0

        # Initialize search services and web scraper
        self.perplexity_search = PaperPerplexitySearch(api_key=perplexity_api_key)
        self.google_search = PaperGoogleSearch(api_key=google_api_key)
        self.web_scraper = PaperWebScraper()

        # Determine which search service is enabled
        search_status = "none"
        if perplexity_api_key:
            search_status = "perplexity"
        elif google_api_key:
            search_status = "google"

        logger.info(
            f"CitationResolver initialized (max_results={max_results}, "
            f"delay={delay_between_requests}s, search={search_status})"
        )

    def resolve(
        self, citation_text: str, context: Optional[str] = None
    ) -> Optional[ResolvedCitation]:
        """
        Resolve a citation using multiple sources.

        Args:
            citation_text: Citation marker or text (e.g., "[Smith et al.]", "(Smith, 2020)")
            context: Optional surrounding context to help matching

        Returns:
            ResolvedCitation if found, None otherwise
        """
        # Rate limiting
        self._rate_limit()

        # Try different resolution strategies in order
        resolved = None

        # Strategy 1: Try ArXiv ID if present (fastest)
        arxiv_id = self._extract_arxiv_id(citation_text)
        if arxiv_id:
            resolved = self._resolve_by_arxiv_id(arxiv_id, citation_text)
            if resolved:
                return resolved

        # Strategy 2: Try ArXiv author-year matching (fast for ArXiv papers)
        author, year = self._parse_author_year(citation_text)
        if author and year:
            resolved = self._resolve_by_author_year(
                author, year, citation_text, context
            )
            if resolved:
                return resolved

        # Strategy 3: Try Perplexity Search + Web Scraping (preferred, works for any paper)
        if self.perplexity_search.enabled:
            resolved = self._resolve_by_perplexity_search(citation_text, context)
            if resolved:
                return resolved

        # Strategy 3b: Try Google Search + Web Scraping (fallback)
        if self.google_search.service:
            resolved = self._resolve_by_google_search(citation_text, context)
            if resolved:
                return resolved

        # Strategy 4: Try ArXiv context search (final fallback)
        author_name = self._parse_author_name(citation_text)
        if author_name and context:
            resolved = self._resolve_by_context(author_name, context, citation_text)
            if resolved:
                return resolved

        logger.warning(f"Could not resolve citation: {citation_text}")
        return None

    def resolve_batch(
        self, citations: List[tuple[str, Optional[str]]]
    ) -> Dict[str, Optional[ResolvedCitation]]:
        """
        Resolve multiple citations in batch.

        Args:
            citations: List of (citation_text, context) tuples

        Returns:
            Dictionary mapping citation_text to ResolvedCitation
        """
        results = {}

        for citation_text, context in citations:
            try:
                resolved = self.resolve(citation_text, context)
                results[citation_text] = resolved
            except Exception as e:
                logger.error(f"Error resolving '{citation_text}': {e}")
                results[citation_text] = None

        logger.info(
            f"Batch resolution: {sum(1 for v in results.values() if v)} / {len(citations)} resolved"
        )

        return results

    def _resolve_by_arxiv_id(
        self, arxiv_id: str, citation_marker: str
    ) -> Optional[ResolvedCitation]:
        """Resolve by ArXiv ID."""
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(search.results(), None)

            if paper:
                logger.info(f"Resolved '{citation_marker}' by ArXiv ID: {arxiv_id}")
                return self._paper_to_resolved_citation(
                    paper, citation_marker, 1.0, "arxiv_id"
                )

        except Exception as e:
            logger.error(f"Error looking up ArXiv ID {arxiv_id}: {e}")

        return None

    def _resolve_by_author_year(
        self,
        author: str,
        year: str,
        citation_marker: str,
        context: Optional[str] = None,
    ) -> Optional[ResolvedCitation]:
        """Resolve by author name and year."""
        try:
            # Build search query
            query = f"au:{author} AND submittedDate:[{year}0101 TO {year}1231]"

            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )

            # Get results
            for paper in search.results():
                # Check if author matches
                if self._author_matches(author, paper.authors):
                    match_score = 0.8  # High confidence for author+year match
                    logger.info(
                        f"Resolved '{citation_marker}' by author-year: {author}, {year}"
                    )
                    return self._paper_to_resolved_citation(
                        paper, citation_marker, match_score, "author_year"
                    )

        except Exception as e:
            logger.error(f"Error searching by author-year: {e}")

        return None

    def _resolve_by_context(
        self, author_name: str, context: str, citation_marker: str
    ) -> Optional[ResolvedCitation]:
        """Resolve using context keywords."""
        try:
            # Extract potential keywords from context
            keywords = self._extract_keywords(context)

            # Search with author + keywords
            query = f"au:{author_name} AND ({' OR '.join(keywords[:3])})"

            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )

            paper = next(search.results(), None)
            if paper:
                match_score = 0.6  # Medium confidence for context match
                logger.info(f"Resolved '{citation_marker}' by context matching")
                return self._paper_to_resolved_citation(
                    paper, citation_marker, match_score, "context"
                )

        except Exception as e:
            logger.error(f"Error searching by context: {e}")

        return None

    def _resolve_by_perplexity_search(
        self, citation_marker: str, context: Optional[str] = None
    ) -> Optional[ResolvedCitation]:
        """Resolve using Perplexity Search + Web Scraping."""
        try:
            # Search Perplexity for the paper
            search_results = self.perplexity_search.search_paper_by_citation(
                citation_marker, context
            )

            if not search_results:
                return None

            # Try to scrape each result until we find valid paper content
            for result in search_results[:5]:  # Try top 5 results
                scraped_paper = self.web_scraper.scrape_paper(result.link)

                if scraped_paper and scraped_paper.abstract:
                    # Successfully scraped paper content
                    match_score = 0.80  # High confidence for Perplexity + scrape
                    logger.info(
                        f"Resolved '{citation_marker}' via Perplexity Search + Web Scraping"
                    )

                    return ResolvedCitation(
                        citation_marker=citation_marker,
                        title=scraped_paper.title,
                        authors=scraped_paper.authors,
                        abstract=scraped_paper.abstract,
                        arxiv_id=scraped_paper.source_url.split("/")[-1]
                        if "arxiv" in scraped_paper.source_url
                        else "",
                        published=scraped_paper.year or "Unknown",
                        pdf_url=scraped_paper.pdf_url or scraped_paper.source_url,
                        match_score=match_score,
                        match_method="perplexity_search_scrape",
                    )

        except Exception as e:
            logger.error(f"Error in Perplexity Search resolution: {e}")

        return None

    def _resolve_by_google_search(
        self, citation_marker: str, context: Optional[str] = None
    ) -> Optional[ResolvedCitation]:
        """Resolve using Google Custom Search + Web Scraping."""
        try:
            # Search Google for the paper
            search_results = self.google_search.search_paper_by_citation(
                citation_marker, context
            )

            if not search_results:
                return None

            # Try to scrape each result until we find valid paper content
            for result in search_results[:5]:  # Try top 5 results
                scraped_paper = self.web_scraper.scrape_paper(result.link)

                if scraped_paper and scraped_paper.abstract:
                    # Successfully scraped paper content
                    match_score = 0.75  # Good confidence for Google + scrape
                    logger.info(
                        f"Resolved '{citation_marker}' via Google Search + Web Scraping"
                    )

                    return ResolvedCitation(
                        citation_marker=citation_marker,
                        title=scraped_paper.title,
                        authors=scraped_paper.authors,
                        abstract=scraped_paper.abstract,
                        arxiv_id=scraped_paper.source_url.split("/")[-1]
                        if "arxiv" in scraped_paper.source_url
                        else "",
                        published=scraped_paper.year or "Unknown",
                        pdf_url=scraped_paper.pdf_url or scraped_paper.source_url,
                        match_score=match_score,
                        match_method="google_search_scrape",
                    )

        except Exception as e:
            logger.error(f"Error in Google Search resolution: {e}")

        return None

    def _paper_to_resolved_citation(
        self,
        paper: arxiv.Result,
        citation_marker: str,
        match_score: float,
        match_method: str,
    ) -> ResolvedCitation:
        """Convert arxiv.Result to ResolvedCitation."""
        return ResolvedCitation(
            citation_marker=citation_marker,
            title=paper.title,
            authors=[author.name for author in paper.authors],
            abstract=paper.summary,
            arxiv_id=paper.entry_id.split("/")[-1],
            published=paper.published.strftime("%Y-%m-%d"),
            pdf_url=paper.pdf_url,
            match_score=match_score,
            match_method=match_method,
        )

    def _rate_limit(self):
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self.delay:
            time.sleep(self.delay - time_since_last)

        self._last_request_time = time.time()

    @staticmethod
    def _extract_arxiv_id(text: str) -> Optional[str]:
        """Extract ArXiv ID from text."""
        # Match patterns like: arXiv:1234.5678, 1234.5678v1, etc.
        patterns = [
            r"arXiv:(\d{4}\.\d{4,5}(?:v\d+)?)",
            r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def _parse_author_year(citation: str) -> tuple[Optional[str], Optional[str]]:
        """Parse author name and year from citation."""
        # Match patterns like: (Smith, 2020), (Smith et al., 2020)
        match = re.search(
            r"\(([A-Z][a-z]+(?:\s+et al\.)?),\s+(\d{4})[a-z]?\)", citation
        )
        if match:
            author = match.group(1).replace(" et al.", "")
            year = match.group(2)
            return author, year

        return None, None

    @staticmethod
    def _parse_author_name(citation: str) -> Optional[str]:
        """Parse author name from named citation."""
        # Match patterns like: [Smith et al.], [Smith and Jones]
        match = re.search(r"\[([A-Z][a-z]+)", citation)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def _author_matches(search_author: str, paper_authors: List[arxiv.Result.Author]) -> bool:
        """Check if author name matches any paper author."""
        search_author_lower = search_author.lower()

        for author in paper_authors:
            # Check last name match
            author_parts = author.name.split()
            if author_parts and search_author_lower in author_parts[-1].lower():
                return True

        return False

    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
        """Extract potential keywords from text."""
        # Remove common words and extract meaningful terms
        stopwords = {"the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "or"}

        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        keywords = [w for w in words if w not in stopwords]

        # Return unique keywords
        return list(dict.fromkeys(keywords))[:max_keywords]
