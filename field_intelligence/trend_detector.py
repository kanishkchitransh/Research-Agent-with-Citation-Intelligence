"""
Trend Detector - Research Field Trends and Breakthroughs

This module detects and analyzes trends, breakthroughs, and research directions
in academic fields using Perplexity API.

Provides:
- Recent breakthrough identification
- Emerging trend detection
- Future research direction prediction
- Historical evolution analysis
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from loguru import logger

try:
    import requests
except ImportError:
    logger.warning("requests not installed, trend detection will not work")
    requests = None


@dataclass
class FieldTrends:
    """Trends and breakthroughs in a research field."""

    field_name: str
    recent_breakthroughs: List[str]  # Major breakthroughs in last 2-3 years
    emerging_trends: List[str]  # Current emerging trends
    research_directions: List[str]  # Predicted future directions
    key_challenges: List[str]  # Open problems and challenges
    timeline_summary: str  # Historical evolution summary
    hot_topics: List[str]  # Currently hot research topics
    impact_areas: Optional[List[str]] = None  # Real-world impact areas

    def to_dict(self) -> Dict:
        """Convert to dictionary for caching."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'FieldTrends':
        """Create from dictionary (for cache retrieval)."""
        return cls(**data)


class TrendDetector:
    """
    Detects trends and breakthroughs in research fields using Perplexity API.

    Uses Perplexity's sonar model with web search to:
    1. Identify recent breakthroughs (last 2-3 years)
    2. Detect emerging trends
    3. Predict future research directions
    4. Analyze field evolution
    """

    def __init__(self, perplexity_api_key: str):
        """
        Initialize trend detector.

        Args:
            perplexity_api_key: Perplexity API key for trend queries
        """
        self.api_key = perplexity_api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"

        if not self.api_key:
            logger.warning("No Perplexity API key provided - trend detection will be limited")

    def detect_trends(
        self,
        field_name: str,
        field_keywords: Optional[List[str]] = None
    ) -> FieldTrends:
        """
        Detect trends and breakthroughs in a research field.

        Args:
            field_name: Name of the research field
            field_keywords: Optional keywords for more specific queries

        Returns:
            FieldTrends with comprehensive trend analysis
        """
        try:
            # Construct query for trend detection
            query = self._construct_trends_query(field_name, field_keywords)

            logger.info(f"Detecting trends for field: {field_name}")

            # Query Perplexity API
            trends_info = self._query_perplexity(query)

            # Parse response into FieldTrends
            trends = self._parse_trends_response(trends_info, field_name)

            logger.info(f"✅ Trend detection complete for {field_name}")
            return trends

        except Exception as e:
            logger.error(f"Error detecting trends: {e}")
            # Return minimal trends on error
            return self._create_fallback_trends(field_name)

    def _construct_trends_query(
        self,
        field_name: str,
        keywords: Optional[List[str]]
    ) -> str:
        """Construct Perplexity query for trend detection."""

        query = f"""Analyze recent trends and breakthroughs in {field_name}

Provide a comprehensive analysis including:
1. Recent breakthroughs (last 2-3 years) - 3-5 major developments
2. Emerging trends - 3-5 current trends gaining traction
3. Future research directions - 3-5 predicted directions
4. Key challenges - 3-5 open problems researchers are tackling
5. Hot topics - 3-5 currently popular research topics
6. Timeline summary - Brief evolution of the field (2-3 sentences)
7. Real-world impact areas (if applicable)
"""

        if keywords:
            keywords_str = ", ".join(keywords[:5])
            query += f"\n\nFocus on aspects related to: {keywords_str}"

        query += "\n\nProvide factual, up-to-date information with specific examples where possible. Focus on developments from 2022 onwards."

        return query

    def _query_perplexity(self, query: str) -> str:
        """
        Query Perplexity API for trends information.

        Args:
            query: Trends detection query

        Returns:
            Response text from Perplexity
        """
        if not self.api_key or not requests:
            raise ValueError("Perplexity API key or requests module not available")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.1-sonar-small-128k-online",  # Fast, with web search
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert research analyst tracking the latest developments in academic fields. Provide up-to-date, factual information about recent breakthroughs and trends."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.3,  # Slightly higher for trend detection
            "max_tokens": 2000  # More tokens for comprehensive trends
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Perplexity API request failed: {e}")
            raise

    def _parse_trends_response(
        self,
        response_text: str,
        field_name: str
    ) -> FieldTrends:
        """
        Parse Perplexity response into FieldTrends.

        Uses pattern matching to extract structured trend information.
        """
        # Extract different categories of information
        breakthroughs = self._extract_list_items(response_text, ["breakthrough", "development", "advance"])
        trends = self._extract_list_items(response_text, ["trend", "emerging", "growing"])
        directions = self._extract_list_items(response_text, ["direction", "future", "predicted"])
        challenges = self._extract_list_items(response_text, ["challenge", "problem", "open"])
        hot_topics = self._extract_list_items(response_text, ["hot topic", "popular", "active"])
        impact_areas = self._extract_list_items(response_text, ["impact", "application", "real-world"])

        # Extract timeline summary
        timeline = self._extract_section(response_text, ["timeline", "evolution", "history"])

        return FieldTrends(
            field_name=field_name,
            recent_breakthroughs=breakthroughs[:5],
            emerging_trends=trends[:5],
            research_directions=directions[:5],
            key_challenges=challenges[:5],
            hot_topics=hot_topics[:5],
            timeline_summary=timeline,
            impact_areas=impact_areas[:5] if impact_areas else None
        )

    def _extract_list_items(self, text: str, keywords: List[str]) -> List[str]:
        """Extract list items based on keywords."""
        items = []
        lines = text.split('\n')

        in_section = False
        for line in lines:
            # Check if we're in relevant section
            if any(kw in line.lower() for kw in keywords):
                in_section = True
                continue

            # If in section, extract list items
            if in_section:
                # Stop at next major section
                if line.startswith('#') or (line and line[0].isupper() and ':' in line and len(line.split(':')[0]) < 40):
                    in_section = False
                    continue

                # Extract bullet points or numbered lists
                stripped = line.strip()
                if stripped.startswith(('-', '*', '•')):
                    item = stripped.lstrip('-*•').strip()
                    if item and len(item) > 10:  # Meaningful items only
                        items.append(item)
                elif stripped and stripped[0].isdigit() and '.' in stripped[:3]:
                    item = stripped.split('.', 1)[1].strip()
                    if item and len(item) > 10:
                        items.append(item)

        return items[:10]  # Limit to 10

    def _extract_section(self, text: str, keywords: List[str]) -> str:
        """Extract text from a specific section."""
        lines = text.split('\n')
        section_text = []
        in_section = False

        for line in lines:
            # Check if we're in relevant section
            if any(kw in line.lower() for kw in keywords):
                in_section = True
                continue

            # If in section, collect text
            if in_section:
                # Stop at next section
                if line.startswith('#'):
                    break
                if line.strip() and not line.strip().startswith(('-', '*', '•')):
                    section_text.append(line.strip())

        result = ' '.join(section_text)[:500] if section_text else "Not available"
        return result

    def _create_fallback_trends(self, field_name: str) -> FieldTrends:
        """Create minimal fallback trends on error."""
        return FieldTrends(
            field_name=field_name,
            recent_breakthroughs=["Unable to fetch recent breakthroughs"],
            emerging_trends=["Unable to fetch emerging trends"],
            research_directions=["Unable to fetch future directions"],
            key_challenges=["Unable to fetch key challenges"],
            hot_topics=["Unable to fetch hot topics"],
            timeline_summary="Unable to fetch timeline information"
        )
