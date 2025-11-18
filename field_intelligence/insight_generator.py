"""
Field Insight Generator - AI-Powered Field Analysis Summaries

This module generates AI-powered summaries and insights about research fields
using Gemini 2.0 Flash.

Provides multiple levels of field insights:
- Quick summary (100-150 tokens) - For UI cards
- Standard analysis (300-500 tokens) - With trends and directions
- Deep analysis (800-1200 tokens) - Comprehensive with all details
"""

from typing import Optional, Dict
from loguru import logger

try:
    import google.generativeai as genai
except ImportError:
    logger.warning("google-generativeai not installed, field insights will be limited")
    genai = None

from .domain_analyzer import FieldProfile
from .trend_detector import FieldTrends


class FieldInsightGenerator:
    """
    Generates AI-powered insights about research fields using Gemini.

    Uses Gemini 2.0 Flash to create context-aware summaries combining:
    - Field profile information
    - Trends and breakthroughs
    - Research directions
    - Relevance to current paper/query
    """

    def __init__(self, api_key: str):
        """
        Initialize field insight generator.

        Args:
            api_key: Google API key for Gemini
        """
        self.api_key = api_key

        if not api_key or not genai:
            logger.warning("Gemini API key or library not available - using fallback insights")
            self.model = None
        else:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                logger.info("✅ Gemini model initialized for field insights")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.model = None

    def generate_quick_summary(
        self,
        field_profile: FieldProfile,
        paper_context: Optional[str] = None
    ) -> str:
        """
        Generate quick field summary (100-150 tokens).

        Perfect for UI cards and quick overviews.

        Args:
            field_profile: Field profile with basic information
            paper_context: Optional paper title/abstract for context

        Returns:
            Concise summary string
        """
        if not self.model:
            return self._fallback_quick_summary(field_profile)

        try:
            prompt = f"""Generate a concise 2-3 sentence summary (100-150 tokens) of this research field:

Field: {field_profile.field_name}
Domain: {field_profile.primary_domain}
Description: {field_profile.description}

Make it informative and accessible. Focus on what makes this field important and unique."""

            if paper_context:
                prompt += f"\n\nContext: This summary is for a reader of: {paper_context[:100]}..."

            response = self.model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error generating quick summary: {e}")
            return self._fallback_quick_summary(field_profile)

    def generate_standard_analysis(
        self,
        field_profile: FieldProfile,
        trends: Optional[FieldTrends] = None,
        paper_context: Optional[str] = None
    ) -> str:
        """
        Generate standard field analysis (300-500 tokens).

        Includes field overview, trends, and directions.

        Args:
            field_profile: Comprehensive field profile
            trends: Optional trends and breakthroughs
            paper_context: Optional paper context

        Returns:
            Formatted analysis string
        """
        if not self.model:
            return self._fallback_standard_analysis(field_profile, trends)

        try:
            prompt = f"""Generate a comprehensive field analysis (300-500 tokens) with these sections:

**Field Information:**
- Name: {field_profile.field_name}
- Domain: {field_profile.primary_domain}
- Key Concepts: {', '.join(field_profile.key_concepts[:5])}
- Major Venues: {', '.join(field_profile.major_venues[:3])}
- Scope: {field_profile.research_scope}
"""

            if trends:
                prompt += f"""
**Recent Trends:**
- Breakthroughs: {', '.join(trends.recent_breakthroughs[:3])}
- Emerging Trends: {', '.join(trends.emerging_trends[:3])}
- Key Challenges: {', '.join(trends.key_challenges[:3])}
"""

            prompt += """
Structure your response as:
1. **Overview**: What is this field about? (2-3 sentences)
2. **Current State**: What's happening now? Recent developments
3. **Research Directions**: Where is the field heading?
"""

            if paper_context:
                prompt += f"\n4. **Relevance**: How does this relate to: {paper_context[:100]}..."

            prompt += "\n\nMake it engaging and informative for researchers. Use markdown formatting."

            response = self.model.generate_content(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error generating standard analysis: {e}")
            return self._fallback_standard_analysis(field_profile, trends)

    def generate_deep_analysis(
        self,
        field_profile: FieldProfile,
        trends: FieldTrends,
        paper_context: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate deep field analysis (800-1200 tokens).

        Comprehensive analysis with multiple sections.

        Args:
            field_profile: Complete field profile
            trends: Complete trends analysis
            paper_context: Optional paper context

        Returns:
            Dictionary with multiple analysis sections
        """
        if not self.model:
            return self._fallback_deep_analysis(field_profile, trends)

        try:
            # Generate comprehensive analysis
            prompt = f"""Generate a comprehensive research field analysis with the following sections:

**Field Profile:**
- Name: {field_profile.field_name}
- Domain: {field_profile.primary_domain}
- Subdomains: {', '.join(field_profile.subdomains)}
- Key Concepts: {', '.join(field_profile.key_concepts)}
- Key Researchers: {', '.join(field_profile.key_researchers)}
- Major Venues: {', '.join(field_profile.major_venues)}

**Trends & Developments:**
- Recent Breakthroughs: {', '.join(trends.recent_breakthroughs)}
- Emerging Trends: {', '.join(trends.emerging_trends)}
- Future Directions: {', '.join(trends.research_directions)}
- Key Challenges: {', '.join(trends.key_challenges)}
- Hot Topics: {', '.join(trends.hot_topics)}

Create these sections (each 150-250 tokens):

1. **FIELD OVERVIEW**: Comprehensive introduction to the field
2. **EVOLUTION & STATE**: Historical context and current state of the art
3. **RESEARCH LANDSCAPE**: Key researchers, institutions, venues, and community
4. **TRENDS & BREAKTHROUGHS**: Recent developments and emerging trends
5. **FUTURE DIRECTIONS**: Where the field is heading, open problems
"""

            if paper_context:
                prompt += f"\n6. **RELEVANCE**: How this field relates to: {paper_context[:200]}..."

            prompt += "\n\nProvide scholarly, well-researched analysis. Use markdown formatting with headers."

            response = self.model.generate_content(prompt)
            full_text = response.text.strip()

            # Parse into sections
            sections = self._parse_sections(full_text)

            return sections

        except Exception as e:
            logger.error(f"Error generating deep analysis: {e}")
            return self._fallback_deep_analysis(field_profile, trends)

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Parse Gemini response into sections."""
        sections = {}
        current_section = None
        current_content = []

        for line in text.split('\n'):
            # Check for section headers (markdown ## or **)
            if line.startswith('##') or (line.startswith('**') and line.endswith('**')):
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()

                # Start new section
                current_section = line.replace('#', '').replace('**', '').strip().upper()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    # Fallback methods (when Gemini is not available)

    def _fallback_quick_summary(self, profile: FieldProfile) -> str:
        """Fallback quick summary without Gemini."""
        return f"""**{profile.field_name}** is a {profile.primary_domain} field focusing on {profile.description[:150]}.

Key areas include {', '.join(profile.subdomains[:3])} with major research venues like {', '.join(profile.major_venues[:2])}."""

    def _fallback_standard_analysis(
        self,
        profile: FieldProfile,
        trends: Optional[FieldTrends]
    ) -> str:
        """Fallback standard analysis without Gemini."""
        analysis = f"""## {profile.field_name}

**Overview**: {profile.description}

**Domain**: {profile.primary_domain}
**Subdomains**: {', '.join(profile.subdomains)}

**Key Concepts**: {', '.join(profile.key_concepts[:5])}

**Major Venues**: {', '.join(profile.major_venues[:3])}

**Research Scope**: {profile.research_scope}
"""

        if trends:
            analysis += f"""
**Recent Breakthroughs**:
{chr(10).join(f'- {b}' for b in trends.recent_breakthroughs[:3])}

**Emerging Trends**:
{chr(10).join(f'- {t}' for t in trends.emerging_trends[:3])}

**Future Directions**:
{chr(10).join(f'- {d}' for d in trends.research_directions[:3])}
"""

        return analysis

    def _fallback_deep_analysis(
        self,
        profile: FieldProfile,
        trends: FieldTrends
    ) -> Dict[str, str]:
        """Fallback deep analysis without Gemini."""
        return {
            "FIELD OVERVIEW": f"{profile.field_name} is a {profile.primary_domain} field. {profile.description}",
            "EVOLUTION & STATE": f"Current state: {profile.current_state}. Research scope: {profile.research_scope}",
            "RESEARCH LANDSCAPE": f"Key researchers: {', '.join(profile.key_researchers)}. Major venues: {', '.join(profile.major_venues)}",
            "TRENDS & BREAKTHROUGHS": f"Recent breakthroughs: {', '.join(trends.recent_breakthroughs)}. Emerging trends: {', '.join(trends.emerging_trends)}",
            "FUTURE DIRECTIONS": f"Research directions: {', '.join(trends.research_directions)}. Key challenges: {', '.join(trends.key_challenges)}"
        }
