"""
Trajectory Analyzer for understanding author's research evolution.

Analyzes:
- Research journey: early work → breakthrough → current focus
- Evolution of research interests
- Career milestones
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger

from .profile_fetcher import AuthorProfile


@dataclass
class ResearchTrajectory:
    """Represents an author's research trajectory."""

    author_name: str
    career_stages: List[str]  # ["Early (2015-2018): Topic modeling", "Recent (2019-2024): Transformers"]
    key_transitions: List[str]  # ["Shifted from RNNs to Transformers in 2019"]
    research_evolution: str  # Narrative description
    current_direction: Optional[str] = None


class TrajectoryAnalyzer:
    """Analyzes author research trajectories."""

    def __init__(self):
        """Initialize trajectory analyzer."""
        logger.info("TrajectoryAnalyzer initialized")

    def analyze_trajectory(self, profile: AuthorProfile) -> ResearchTrajectory:
        """
        Analyze author's research trajectory.

        Args:
            profile: AuthorProfile object

        Returns:
            ResearchTrajectory object
        """
        logger.info(f"Analyzing trajectory for {profile.name}")

        trajectory = ResearchTrajectory(
            author_name=profile.name,
            career_stages=[],
            key_transitions=[],
            research_evolution="",
            current_direction=profile.current_focus,
        )

        # Analyze career stages from top papers
        if profile.top_papers:
            stages = self._identify_career_stages(profile.top_papers)
            trajectory.career_stages = stages

        # Identify key transitions in research interests
        if profile.expertise_areas:
            transitions = self._identify_transitions(profile)
            trajectory.key_transitions = transitions

        # Create research evolution narrative
        trajectory.research_evolution = self._create_evolution_narrative(profile, trajectory)

        return trajectory

    def _identify_career_stages(self, top_papers: List[Dict]) -> List[str]:
        """
        Identify career stages based on publication timeline.

        Args:
            top_papers: List of {title, year, citations}

        Returns:
            List of career stage descriptions
        """
        if not top_papers:
            return []

        # Group papers by time period
        stages = []

        # Sort by year
        sorted_papers = sorted(top_papers, key=lambda p: p.get("year", 0))

        if not sorted_papers:
            return []

        # Simple grouping: early vs recent
        years = [p.get("year", 0) for p in sorted_papers if p.get("year")]
        if not years:
            return []

        min_year = min(years)
        max_year = max(years)
        mid_year = min_year + (max_year - min_year) // 2

        early_papers = [p for p in sorted_papers if p.get("year", 0) <= mid_year]
        recent_papers = [p for p in sorted_papers if p.get("year", 0) > mid_year]

        if early_papers:
            early_titles = ", ".join([p["title"][:50] for p in early_papers[:2]])
            stages.append(f"Early work ({min_year}-{mid_year}): {early_titles}...")

        if recent_papers:
            recent_titles = ", ".join([p["title"][:50] for p in recent_papers[:2]])
            stages.append(f"Recent work ({mid_year + 1}-{max_year}): {recent_titles}...")

        return stages

    def _identify_transitions(self, profile: AuthorProfile) -> List[str]:
        """
        Identify key transitions in research focus.

        Args:
            profile: AuthorProfile

        Returns:
            List of transition descriptions
        """
        transitions = []

        # Based on expertise areas and career overview
        if profile.expertise_areas and len(profile.expertise_areas) > 1:
            # Assume evolution from first to last area
            transitions.append(
                f"Research focus evolved across: {', '.join(profile.expertise_areas[:3])}"
            )

        if profile.breakthrough_papers:
            transitions.append(
                f"Notable contributions: {len(profile.breakthrough_papers)} breakthrough papers"
            )

        return transitions

    def _create_evolution_narrative(
        self,
        profile: AuthorProfile,
        trajectory: ResearchTrajectory,
    ) -> str:
        """
        Create a narrative description of research evolution.

        Args:
            profile: AuthorProfile
            trajectory: Partial trajectory with stages and transitions

        Returns:
            Narrative string
        """
        narrative_parts = []

        # Career overview
        if profile.career_overview:
            # Extract first 2-3 sentences
            sentences = profile.career_overview.split('.')[:3]
            narrative_parts.append('. '.join(sentences) + '.')

        # Publication metrics
        if profile.publication_count:
            narrative_parts.append(
                f"Has published {profile.publication_count} papers "
                f"with {profile.citation_count} citations (h-index: {profile.h_index})."
            )

        # Career stages
        if trajectory.career_stages:
            narrative_parts.append(" ".join(trajectory.career_stages))

        # Current focus
        if profile.current_focus:
            narrative_parts.append(f"Currently: {profile.current_focus}")

        return " ".join(narrative_parts)

    def get_collaborator_network(self, profile: AuthorProfile) -> List[str]:
        """
        Get list of frequent collaborators.

        Args:
            profile: AuthorProfile

        Returns:
            List of collaborator names
        """
        # For MVP, return from profile if available
        return profile.collaborators[:10] if profile.collaborators else []
