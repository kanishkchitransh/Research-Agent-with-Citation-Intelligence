"""Citation Intelligence module.

This module provides citation extraction, resolution, and explanation capabilities.
"""

from .explainer import CitationExplainer, CitationExplanation
from .extractor import Citation, CitationExtractor, ExtractedCitations
from .resolver import CitationResolver, ResolvedCitation

__all__ = [
    # Extractor
    "CitationExtractor",
    "Citation",
    "ExtractedCitations",
    # Resolver
    "CitationResolver",
    "ResolvedCitation",
    # Explainer
    "CitationExplainer",
    "CitationExplanation",
]
