"""
Field Intelligence Module

This module provides comprehensive research field/domain analysis:
- Domain identification and classification
- Current state of the art analysis
- Trend detection and breakthrough identification
- Research direction prediction
- Subfield mapping

Designed for academic research with 30-day caching.
"""

from .domain_analyzer import DomainAnalyzer, FieldProfile
from .trend_detector import TrendDetector, FieldTrends
from .insight_generator import FieldInsightGenerator

__all__ = [
    "DomainAnalyzer",
    "FieldProfile",
    "TrendDetector",
    "FieldTrends",
    "FieldInsightGenerator",
]
