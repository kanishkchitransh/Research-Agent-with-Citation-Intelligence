"""
Author Profile Fetcher using Perplexity API and Semantic Scholar API.

Fetches comprehensive author information from multiple sources:
- Perplexity API: Career overview, recent work, expertise
- Semantic Scholar API: Publication metrics, h-index, citations (FREE)
"""

import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from loguru import logger


@dataclass
class AuthorProfile:
    """Comprehensive author profile."""

    name: str
    normalized_name: str  # For caching: "firstname_lastname"
    institution: Optional[str] = None
    email: Optional[str] = None
    years_active: Optional[str] = None  # e.g., "2015-present"
    expertise_areas: List[str] = None  # Research areas

    # From Perplexity
    career_overview: Optional[str] = None
    recent_work: Optional[str] = None
    breakthrough_papers: List[str] = None
    current_focus: Optional[str] = None

    # From Semantic Scholar
    publication_count: int = 0
    citation_count: int = 0
    h_index: int = 0
    semantic_scholar_id: Optional[str] = None
    top_papers: List[Dict] = None  # List of {title, year, citations}

    # Collaborators
    collaborators: List[str] = None

    # Metadata
    fetched_at: str = None
    sources_used: List[str] = None

    def __post_init__(self):
        if self.expertise_areas is None:
            self.expertise_areas = []
        if self.breakthrough_papers is None:
            self.breakthrough_papers = []
        if self.top_papers is None:
            self.top_papers = []
        if self.collaborators is None:
            self.collaborators = []
        if self.sources_used is None:
            self.sources_used = []


class AuthorProfileFetcher:
    """
    Fetches author profiles from multiple sources.

    Uses:
    1. Perplexity API - Career overview and context
    2. Semantic Scholar API - Publication metrics (FREE)
    """

    def __init__(
        self,
        perplexity_api_key: Optional[str] = None,
        use_semantic_scholar: bool = True,
    ):
        """
        Initialize the author profile fetcher.

        Args:
            perplexity_api_key: Perplexity API key (optional, uses env var if not provided)
            use_semantic_scholar: Whether to use Semantic Scholar API (default: True)
        """
        self.perplexity_api_key = perplexity_api_key or os.getenv("PERPLEXITY_API_KEY")
        self.use_semantic_scholar = use_semantic_scholar

        # Semantic Scholar API (FREE, no key needed)
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"

        logger.info(
            f"AuthorProfileFetcher initialized "
            f"(Perplexity: {bool(self.perplexity_api_key)}, "
            f"Semantic Scholar: {use_semantic_scholar})"
        )

    def normalize_author_name(self, name: str) -> str:
        """
        Normalize author name for caching.

        Examples:
            "Ashish Vaswani" -> "ashish_vaswani"
            "Ming-Wei Chang" -> "mingwei_chang"
            "Kenton Lee" -> "kenton_lee"
        """
        # Remove special characters, convert to lowercase
        normalized = re.sub(r'[^a-zA-Z\s]', '', name.lower())
        # Replace spaces with underscores
        normalized = '_'.join(normalized.split())
        return normalized

    def fetch_profile(
        self,
        author_name: str,
        institution: Optional[str] = None,
        paper_context: Optional[str] = None,
    ) -> AuthorProfile:
        """
        Fetch comprehensive author profile.

        Args:
            author_name: Author's name
            institution: Author's institution (helps with disambiguation)
            paper_context: Context from the paper (helps with disambiguation)

        Returns:
            AuthorProfile object
        """
        logger.info(f"Fetching profile for author: {author_name}")

        normalized_name = self.normalize_author_name(author_name)

        profile = AuthorProfile(
            name=author_name,
            normalized_name=normalized_name,
            institution=institution,
            fetched_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Fetch from Perplexity (career overview, expertise)
        if self.perplexity_api_key:
            try:
                perplexity_data = self._fetch_from_perplexity(
                    author_name, institution, paper_context
                )
                profile.career_overview = perplexity_data.get("career_overview")
                profile.recent_work = perplexity_data.get("recent_work")
                profile.breakthrough_papers = perplexity_data.get("breakthrough_papers", [])
                profile.current_focus = perplexity_data.get("current_focus")
                profile.expertise_areas = perplexity_data.get("expertise_areas", [])
                profile.sources_used.append("perplexity")
                logger.info(f"✓ Fetched Perplexity data for {author_name}")
            except Exception as e:
                logger.warning(f"Failed to fetch from Perplexity: {e}")

        # Fetch from Semantic Scholar (publication metrics)
        if self.use_semantic_scholar:
            try:
                scholar_data = self._fetch_from_semantic_scholar(author_name)
                if scholar_data:
                    profile.semantic_scholar_id = scholar_data.get("authorId")
                    profile.publication_count = scholar_data.get("paperCount", 0)
                    profile.citation_count = scholar_data.get("citationCount", 0)
                    profile.h_index = scholar_data.get("hIndex", 0)
                    profile.top_papers = scholar_data.get("top_papers", [])
                    profile.sources_used.append("semantic_scholar")
                    logger.info(f"✓ Fetched Semantic Scholar data for {author_name}")
            except Exception as e:
                logger.warning(f"Failed to fetch from Semantic Scholar: {e}")

        return profile

    def _fetch_from_perplexity(
        self,
        author_name: str,
        institution: Optional[str],
        paper_context: Optional[str],
    ) -> Dict:
        """
        Fetch author information from Perplexity API.

        Returns dict with:
            - career_overview
            - recent_work
            - breakthrough_papers
            - current_focus
            - expertise_areas
        """
        # Build context-aware query
        query = f"{author_name} researcher profile"

        if institution:
            query += f" {institution}"

        if paper_context:
            # Extract key topics from paper context
            query += f" research in {paper_context[:100]}"

        query += " academic publications expertise career"

        # Call Perplexity API
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "sonar",  # Perplexity's search model
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at finding information about academic researchers. Provide structured information about the researcher's career, expertise, and contributions."
                },
                {
                    "role": "user",
                    "content": f"Find information about {author_name} as an academic researcher. Include: career overview, research areas, notable publications, current work, and institution affiliation. Be concise but comprehensive."
                }
            ],
        }

        try:
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Parse the response to extract structured information
            parsed_data = self._parse_perplexity_response(content)

            return parsed_data

        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return {}

    def _parse_perplexity_response(self, content: str) -> Dict:
        """
        Parse Perplexity response to extract structured data.

        Looks for patterns in the text response.
        """
        data = {
            "career_overview": content,  # Full response as overview
            "recent_work": None,
            "breakthrough_papers": [],
            "current_focus": None,
            "expertise_areas": [],
        }

        # Extract expertise areas (look for common patterns)
        expertise_keywords = [
            "machine learning", "natural language processing", "computer vision",
            "deep learning", "reinforcement learning", "transformers", "neural networks",
            "artificial intelligence", "data science", "robotics", "NLP", "CV",
            "linguistics", "computational", "algorithms", "optimization"
        ]

        content_lower = content.lower()
        found_expertise = []
        for keyword in expertise_keywords:
            if keyword in content_lower:
                found_expertise.append(keyword.title())

        data["expertise_areas"] = list(set(found_expertise))[:5]  # Top 5 unique areas

        # Try to extract current focus (usually mentioned near end)
        if "currently" in content_lower or "recent" in content_lower:
            # Extract sentences mentioning current work
            sentences = content.split('.')
            for sent in sentences:
                if "currently" in sent.lower() or "recent" in sent.lower():
                    data["current_focus"] = sent.strip()
                    break

        return data

    def _fetch_from_semantic_scholar(self, author_name: str) -> Optional[Dict]:
        """
        Fetch author information from Semantic Scholar API (FREE).

        Returns dict with:
            - authorId
            - paperCount
            - citationCount
            - hIndex
            - top_papers: [{title, year, citationCount}, ...]
        """
        try:
            # Search for author
            search_url = f"{self.semantic_scholar_base}/author/search"
            params = {"query": author_name, "limit": 1}

            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()

            search_result = response.json()

            if not search_result.get("data"):
                logger.warning(f"No Semantic Scholar results for {author_name}")
                return None

            author_id = search_result["data"][0]["authorId"]

            # Get detailed author info
            author_url = f"{self.semantic_scholar_base}/author/{author_id}"
            params = {
                "fields": "authorId,name,paperCount,citationCount,hIndex,papers.title,papers.year,papers.citationCount"
            }

            response = requests.get(author_url, params=params, timeout=10)
            response.raise_for_status()

            author_data = response.json()

            # Extract top papers
            papers = author_data.get("papers", [])
            top_papers = sorted(
                papers,
                key=lambda p: p.get("citationCount", 0),
                reverse=True
            )[:5]  # Top 5 most cited

            top_papers_formatted = [
                {
                    "title": p.get("title", "Unknown"),
                    "year": p.get("year", "N/A"),
                    "citations": p.get("citationCount", 0)
                }
                for p in top_papers
            ]

            return {
                "authorId": author_data.get("authorId"),
                "paperCount": author_data.get("paperCount", 0),
                "citationCount": author_data.get("citationCount", 0),
                "hIndex": author_data.get("hIndex", 0),
                "top_papers": top_papers_formatted,
            }

        except Exception as e:
            logger.error(f"Semantic Scholar API error: {e}")
            return None

    def fetch_multiple_authors(
        self,
        author_names: List[str],
        prioritize_first_last: bool = True,
    ) -> List[AuthorProfile]:
        """
        Fetch profiles for multiple authors.

        Args:
            author_names: List of author names
            prioritize_first_last: If True, fetch first and last authors immediately,
                                  queue others for background processing

        Returns:
            List of AuthorProfile objects
        """
        profiles = []

        if prioritize_first_last and len(author_names) > 2:
            # Fetch first and last authors immediately
            priority_authors = [author_names[0], author_names[-1]]
            supporting_authors = author_names[1:-1]

            logger.info(f"Priority fetch: {priority_authors}")
            for author in priority_authors:
                profile = self.fetch_profile(author)
                profiles.append(profile)

            # For MVP, fetch supporting authors too (in production, queue these)
            logger.info(f"Fetching supporting authors: {len(supporting_authors)}")
            for author in supporting_authors:
                profile = self.fetch_profile(author)
                profiles.append(profile)
        else:
            # Fetch all authors
            for author in author_names:
                profile = self.fetch_profile(author)
                profiles.append(profile)

        return profiles
