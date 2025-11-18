"""Author Intelligence module for understanding paper authors."""

from .profile_fetcher import AuthorProfileFetcher
from .trajectory_analyzer import TrajectoryAnalyzer
from .insight_generator import InsightGenerator

__all__ = [
    "AuthorProfileFetcher",
    "TrajectoryAnalyzer",
    "InsightGenerator",
]
