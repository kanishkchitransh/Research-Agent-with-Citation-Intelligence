"""
Insight Generator using Gemini 2.5 Flash for author intelligence summaries.

Generates:
- Quick summaries (100-200 tokens)
- Standard summaries (300-500 tokens)
- Deep analysis (multiple structured calls)
"""

import os
from typing import Dict, Optional

import google.generativeai as genai
from loguru import logger

from .profile_fetcher import AuthorProfile
from .trajectory_analyzer import ResearchTrajectory


class InsightGenerator:
    """
    Generates natural language insights about authors using Gemini.

    All summaries are contextual - they explain how the author's background
    relates to the current paper being analyzed.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize insight generator.

        Args:
            api_key: Google AI API key (uses env var if not provided)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError("Google API key required for InsightGenerator")

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

        logger.info("InsightGenerator initialized with Gemini 2.0 Flash")

    def generate_quick_summary(
        self,
        profile: AuthorProfile,
        paper_context: Optional[str] = None,
    ) -> str:
        """
        Generate quick summary (100-200 tokens) for UI cards.

        Args:
            profile: AuthorProfile
            paper_context: Context about the current paper

        Returns:
            Quick summary string
        """
        logger.info(f"Generating quick summary for {profile.name}")

        prompt = self._build_quick_prompt(profile, paper_context)

        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            logger.info(f"✓ Generated quick summary ({len(summary)} chars)")
            return summary
        except Exception as e:
            logger.error(f"Error generating quick summary: {e}")
            return f"Researcher specializing in {', '.join(profile.expertise_areas[:2]) if profile.expertise_areas else 'various fields'}."

    def generate_standard_summary(
        self,
        profile: AuthorProfile,
        trajectory: Optional[ResearchTrajectory] = None,
        paper_context: Optional[str] = None,
    ) -> str:
        """
        Generate standard summary (300-500 tokens) with research journey.

        Args:
            profile: AuthorProfile
            trajectory: ResearchTrajectory (optional)
            paper_context: Context about the current paper

        Returns:
            Standard summary string
        """
        logger.info(f"Generating standard summary for {profile.name}")

        prompt = self._build_standard_prompt(profile, trajectory, paper_context)

        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
            logger.info(f"✓ Generated standard summary ({len(summary)} chars)")
            return summary
        except Exception as e:
            logger.error(f"Error generating standard summary: {e}")
            return self._fallback_standard_summary(profile)

    def generate_deep_analysis(
        self,
        profile: AuthorProfile,
        trajectory: ResearchTrajectory,
        paper_context: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate deep analysis with multiple structured sections.

        Args:
            profile: AuthorProfile
            trajectory: ResearchTrajectory
            paper_context: Context about the current paper

        Returns:
            Dict with sections: {
                "overview": str,
                "research_journey": str,
                "key_contributions": str,
                "relevance_to_paper": str,
            }
        """
        logger.info(f"Generating deep analysis for {profile.name}")

        analysis = {}

        # Generate each section
        sections = ["overview", "research_journey", "key_contributions", "relevance_to_paper"]

        for section in sections:
            prompt = self._build_deep_prompt(section, profile, trajectory, paper_context)
            try:
                response = self.model.generate_content(prompt)
                analysis[section] = response.text.strip()
            except Exception as e:
                logger.error(f"Error generating {section}: {e}")
                analysis[section] = f"[Error generating {section}]"

        return analysis

    def _build_quick_prompt(
        self,
        profile: AuthorProfile,
        paper_context: Optional[str],
    ) -> str:
        """Build prompt for quick summary."""
        prompt = f"""Generate a brief 2-3 sentence summary about researcher {profile.name}.

**Author Information:**
- Institution: {profile.institution or 'Unknown'}
- Expertise: {', '.join(profile.expertise_areas[:3]) if profile.expertise_areas else 'Not specified'}
- Publications: {profile.publication_count} papers, {profile.citation_count} citations
- H-index: {profile.h_index}
"""

        if paper_context:
            prompt += f"\n**Paper Context:** This paper is about {paper_context[:100]}..."

        prompt += """

**Task:** Write a concise, informative summary highlighting:
1. Main research area
2. Career stage (junior/established/senior)
3. Relevance to this paper

Be conversational and researcher-friendly. 2-3 sentences only."""

        return prompt

    def _build_standard_prompt(
        self,
        profile: AuthorProfile,
        trajectory: Optional[ResearchTrajectory],
        paper_context: Optional[str],
    ) -> str:
        """Build prompt for standard summary."""
        prompt = f"""Generate a comprehensive summary about researcher {profile.name}.

**Author Information:**
- Name: {profile.name}
- Institution: {profile.institution or 'Unknown'}
- Expertise: {', '.join(profile.expertise_areas) if profile.expertise_areas else 'Various fields'}
- Career: {profile.years_active or 'Active researcher'}

**Publication Metrics:**
- Papers: {profile.publication_count}
- Citations: {profile.citation_count}
- H-index: {profile.h_index}

**Career Overview:**
{profile.career_overview[:500] if profile.career_overview else 'Experienced researcher in their field.'}
"""

        if trajectory:
            prompt += f"\n**Research Evolution:**\n{trajectory.research_evolution}\n"

        if profile.top_papers:
            prompt += "\n**Notable Papers:**\n"
            for paper in profile.top_papers[:3]:
                prompt += f"- {paper['title']} ({paper['year']}) - {paper['citations']} citations\n"

        if paper_context:
            prompt += f"\n**Current Paper Context:** {paper_context[:200]}...\n"

        prompt += """

**Task:** Write a narrative summary (4-6 sentences) that:
1. Describes their research journey and evolution
2. Highlights key contributions and expertise
3. Explains their relevance to the current paper
4. Uses clear, accessible language for researchers

Be informative but conversational."""

        return prompt

    def _build_deep_prompt(
        self,
        section: str,
        profile: AuthorProfile,
        trajectory: ResearchTrajectory,
        paper_context: Optional[str],
    ) -> str:
        """Build prompt for deep analysis sections."""
        base_info = f"""Author: {profile.name}
Publications: {profile.publication_count} papers
Citations: {profile.citation_count}
H-index: {profile.h_index}
Expertise: {', '.join(profile.expertise_areas)}
"""

        if section == "overview":
            return f"""{base_info}

Write a comprehensive overview (1 paragraph) of {profile.name}'s academic career and contributions."""

        elif section == "research_journey":
            return f"""{base_info}
Career Evolution: {trajectory.research_evolution}

Describe {profile.name}'s research journey (1-2 paragraphs), highlighting how their work has evolved and key milestones."""

        elif section == "key_contributions":
            papers_str = "\n".join([f"- {p['title']} ({p['year']})" for p in profile.top_papers[:5]])
            return f"""{base_info}
Top Papers:
{papers_str}

Describe {profile.name}'s key research contributions (1 paragraph), focusing on impact and innovation."""

        elif section == "relevance_to_paper":
            return f"""{base_info}
Current Paper: {paper_context[:200] if paper_context else 'Research paper'}

Explain (1 paragraph) why {profile.name}'s background and expertise is relevant to understanding this paper."""

        return "Generate analysis."

    def _fallback_standard_summary(self, profile: AuthorProfile) -> str:
        """Generate fallback summary if API fails."""
        parts = [f"{profile.name} is a researcher"]

        if profile.expertise_areas:
            parts.append(f"specializing in {', '.join(profile.expertise_areas[:2])}")

        if profile.institution:
            parts.append(f"affiliated with {profile.institution}")

        parts.append(
            f"with {profile.publication_count} publications and {profile.citation_count} citations"
        )

        return ". ".join(parts) + "."
