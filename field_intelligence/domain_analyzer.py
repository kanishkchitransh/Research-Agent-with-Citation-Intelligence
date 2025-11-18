"""
Domain Analyzer - Research Field/Domain Analysis

This module analyzes research fields and domains using Perplexity API.
Provides comprehensive field profiles including:
- Field classification and taxonomy
- Current state of the art
- Key researchers and institutions
- Major conferences and venues
- Research scope and boundaries
"""

import json
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from loguru import logger

try:
    import requests
except ImportError:
    logger.warning("requests not installed, field intelligence will not work")
    requests = None


@dataclass
class FieldProfile:
    """Comprehensive field/domain profile."""

    field_name: str
    primary_domain: str  # e.g., "Computer Science", "Physics", "Biology"
    subdomains: List[str]  # e.g., ["Machine Learning", "NLP", "Computer Vision"]
    description: str  # Overview of the field
    key_concepts: List[str]  # Core concepts and terminology
    key_researchers: List[str]  # Leading researchers in the field
    major_venues: List[str]  # Top conferences/journals
    research_scope: str  # What the field covers
    current_state: str  # Current state of the art summary
    established_year: Optional[str] = None  # When the field emerged
    related_fields: Optional[List[str]] = None  # Related/adjacent fields

    def to_dict(self) -> Dict:
        """Convert to dictionary for caching."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'FieldProfile':
        """Create from dictionary (for cache retrieval)."""
        return cls(**data)


class DomainAnalyzer:
    """
    Analyzes research domains/fields using Perplexity API.

    Uses Perplexity's sonar model to:
    1. Identify and classify research domains
    2. Gather field-specific information
    3. Map field taxonomy and relationships
    """

    def __init__(self, perplexity_api_key: str):
        """
        Initialize domain analyzer.

        Args:
            perplexity_api_key: Perplexity API key for field queries
        """
        self.api_key = perplexity_api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"

        if not self.api_key:
            logger.warning("No Perplexity API key provided - field analysis will be limited")

    def analyze_field(
        self,
        field_keywords: List[str],
        paper_context: Optional[str] = None
    ) -> FieldProfile:
        """
        Analyze a research field based on keywords and optional paper context.

        Args:
            field_keywords: Keywords representing the field (e.g., ["transformers", "attention", "NLP"])
            paper_context: Optional paper title/abstract for context

        Returns:
            FieldProfile with comprehensive field information
        """
        try:
            # Construct query for field analysis
            query = self._construct_field_query(field_keywords, paper_context)

            logger.info(f"Analyzing field for keywords: {field_keywords}")

            # Query Perplexity API
            field_info = self._query_perplexity(query)

            # Parse response into FieldProfile
            profile = self._parse_field_response(field_info, field_keywords)

            logger.info(f"✅ Field analysis complete: {profile.field_name}")
            return profile

        except Exception as e:
            logger.error(f"Error analyzing field: {e}")
            # Return minimal profile on error
            return self._create_fallback_profile(field_keywords)

    def _construct_field_query(
        self,
        keywords: List[str],
        paper_context: Optional[str]
    ) -> str:
        """Construct Perplexity query for field analysis."""

        keywords_str = ", ".join(keywords[:5])  # Limit to 5 keywords

        query = f"""Analyze the research field related to: {keywords_str}

Provide a comprehensive overview including:
1. Field name and primary domain (e.g., Computer Science, Physics, Biology)
2. Subdomains and specializations
3. Brief description of what the field studies
4. 5-7 key concepts and terminology
5. 3-5 leading researchers or research groups
6. Major conferences and journals (top 3-5)
7. Research scope and boundaries
8. Current state of the art (recent developments in last 2-3 years)
"""

        if paper_context:
            query += f"\n\nContext from related paper: {paper_context[:200]}..."

        query += "\n\nProvide factual, well-structured information suitable for academic researchers."

        return query

    def _query_perplexity(self, query: str) -> str:
        """
        Query Perplexity API for field information.

        Args:
            query: Field analysis query

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
            "model": "llama-3.1-sonar-small-128k-online",  # Fast, accurate, cost-effective
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert research analyst providing comprehensive field analysis for academic researchers. Be factual, detailed, and well-structured."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.2,  # Low temperature for factual responses
            "max_tokens": 1500  # Enough for comprehensive analysis
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

    def _parse_field_response(
        self,
        response_text: str,
        keywords: List[str]
    ) -> FieldProfile:
        """
        Parse Perplexity response into FieldProfile.

        Uses pattern matching and heuristics to extract structured information.
        """
        # Extract field name (first major heading or use keywords)
        field_name = self._extract_field_name(response_text, keywords)

        # Extract primary domain
        primary_domain = self._extract_primary_domain(response_text)

        # Extract subdomains
        subdomains = self._extract_list_items(response_text, ["subdomain", "specialization", "area"])

        # Extract description (usually first paragraph)
        description = self._extract_description(response_text)

        # Extract key concepts
        key_concepts = self._extract_list_items(response_text, ["concept", "terminology", "term"])

        # Extract researchers
        key_researchers = self._extract_list_items(response_text, ["researcher", "scientist", "expert"])

        # Extract venues
        major_venues = self._extract_list_items(response_text, ["conference", "journal", "venue"])

        # Extract research scope
        research_scope = self._extract_section(response_text, ["scope", "covers", "studies"])

        # Extract current state
        current_state = self._extract_section(response_text, ["current", "recent", "state of the art"])

        # Extract related fields
        related_fields = self._extract_list_items(response_text, ["related field", "adjacent", "connected"])

        return FieldProfile(
            field_name=field_name,
            primary_domain=primary_domain,
            subdomains=subdomains[:5],  # Limit to 5
            description=description,
            key_concepts=key_concepts[:7],  # Limit to 7
            key_researchers=key_researchers[:5],  # Limit to 5
            major_venues=major_venues[:5],  # Limit to 5
            research_scope=research_scope,
            current_state=current_state,
            related_fields=related_fields[:5] if related_fields else None
        )

    def _extract_field_name(self, text: str, keywords: List[str]) -> str:
        """Extract field name from response."""
        # Try to find field name in first few lines
        lines = text.split('\n')[:5]
        for line in lines:
            # Look for patterns like "Field: X" or "# X"
            if 'field' in line.lower() and ':' in line:
                return line.split(':')[1].strip()
            if line.startswith('#'):
                return line.replace('#', '').strip()

        # Fallback: use first keyword capitalized
        return ' '.join(word.capitalize() for word in keywords[0].split())

    def _extract_primary_domain(self, text: str) -> str:
        """Extract primary domain (Computer Science, Physics, etc.)."""
        domains = [
            "Computer Science", "Physics", "Biology", "Chemistry",
            "Mathematics", "Engineering", "Medicine", "Psychology",
            "Economics", "Neuroscience", "Materials Science"
        ]

        text_lower = text.lower()
        for domain in domains:
            if domain.lower() in text_lower:
                return domain

        return "Interdisciplinary"  # Default

    def _extract_list_items(self, text: str, keywords: List[str]) -> List[str]:
        """Extract list items based on keywords."""
        items = []
        lines = text.split('\n')

        # Find section with keywords
        in_section = False
        for line in lines:
            # Check if we're in relevant section
            if any(kw in line.lower() for kw in keywords):
                in_section = True
                continue

            # If in section, extract list items
            if in_section:
                # Stop at next section
                if line.startswith('#') or (line and line[0].isupper() and ':' in line):
                    in_section = False
                    continue

                # Extract bullet points or numbered lists
                if line.strip().startswith(('-', '*', '•')):
                    item = line.strip().lstrip('-*•').strip()
                    if item:
                        items.append(item)
                elif re.match(r'^\d+\.', line.strip()):
                    item = re.sub(r'^\d+\.\s*', '', line.strip())
                    if item:
                        items.append(item)

        return items[:10]  # Limit to 10

    def _extract_description(self, text: str) -> str:
        """Extract field description (usually first paragraph)."""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        # Find first substantial paragraph
        for para in paragraphs:
            if len(para) > 100 and not para.startswith('#'):
                return para[:500]  # Limit length

        return paragraphs[0][:500] if paragraphs else "No description available"

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
                if line.strip():
                    section_text.append(line.strip())

        return ' '.join(section_text)[:500] if section_text else "Not available"

    def _create_fallback_profile(self, keywords: List[str]) -> FieldProfile:
        """Create minimal fallback profile on error."""
        field_name = ' '.join(word.capitalize() for word in keywords[0].split())

        return FieldProfile(
            field_name=field_name,
            primary_domain="Unknown",
            subdomains=[],
            description=f"Research field related to {', '.join(keywords)}",
            key_concepts=keywords,
            key_researchers=[],
            major_venues=[],
            research_scope="Unable to fetch detailed information",
            current_state="Unable to fetch current state"
        )
