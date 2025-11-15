"""Citation extraction from research papers.

This module extracts citation markers and their context from paper text.
Supports multiple citation formats: [1], [Smith et al.], (Author, Year), etc.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class Citation:
    """Represents a citation found in text."""

    marker: str  # e.g., "[1]", "[Smith et al.]"
    context: str  # Surrounding text
    position: int  # Character position in text
    citation_type: str  # "numeric", "author-year", "named"


@dataclass
class ExtractedCitations:
    """Result of citation extraction."""

    citations: List[Citation]
    total_count: int
    unique_markers: List[str]


class CitationExtractor:
    """
    Extracts citations from research paper text.

    Supports multiple citation formats:
    - Numeric: [1], [2, 3], [1-5]
    - Author-year: (Smith, 2020), (Smith et al., 2020)
    - Named: [Smith et al.]
    """

    def __init__(self, context_window: int = 200):
        """
        Initialize the citation extractor.

        Args:
            context_window: Number of characters to extract around citation
        """
        self.context_window = context_window

        # Citation patterns (ordered by specificity)
        self.patterns = [
            # Numeric citations: [1], [2,3], [1-5], [1, 2, 3]
            (
                r"\[(\d+(?:\s*[-,]\s*\d+)*)\]",
                "numeric",
            ),
            # Named citations: [Smith et al.], [Smith and Jones]
            (
                r"\[([A-Z][a-z]+(?:\s+(?:et al\.|and)\s+[A-Z][a-z]+)?)\]",
                "named",
            ),
            # Author-year citations: (Smith, 2020), (Smith et al., 2020)
            # Handles newlines and multiple spaces between author and year
            (
                r"\(([A-Z][a-z]+(?:\s+et al\.)?[,\s]+\d{4}[a-z]?)\)",
                "author-year",
            ),
            # Superscript/footnote citations: ¹, ², ³, etc. (Unicode superscripts)
            (
                r"([¹²³⁴⁵⁶⁷⁸⁹⁰]+)",
                "footnote",
            ),
            # Caret-style footnotes: ^1, ^2, ^3 (plain text representation)
            (
                r"\^(\d+)",
                "footnote",
            ),
        ]

        logger.info(
            f"CitationExtractor initialized (context_window={context_window})"
        )

    def extract(self, text: str) -> ExtractedCitations:
        """
        Extract all citations from text.

        Args:
            text: Text to extract citations from

        Returns:
            ExtractedCitations object with all found citations
        """
        all_citations = []
        seen_markers = set()

        for pattern, citation_type in self.patterns:
            matches = re.finditer(pattern, text)

            for match in matches:
                marker = match.group(0)  # Full match including brackets
                position = match.start()

                # Normalize marker (remove extra whitespace/newlines)
                normalized_marker = ' '.join(marker.split())

                # Extract context around citation
                context = self._extract_context(text, position, len(marker))

                citation = Citation(
                    marker=normalized_marker,
                    context=context,
                    position=position,
                    citation_type=citation_type,
                )

                all_citations.append(citation)
                seen_markers.add(normalized_marker)

        # Sort by position
        all_citations.sort(key=lambda c: c.position)

        result = ExtractedCitations(
            citations=all_citations,
            total_count=len(all_citations),
            unique_markers=sorted(list(seen_markers)),
        )

        logger.info(
            f"Extracted {result.total_count} citations "
            f"({len(result.unique_markers)} unique)"
        )

        return result

    def extract_citation_context(
        self,
        text: str,
        citation_marker: str,
        context_window: Optional[int] = None,
    ) -> Optional[str]:
        """
        Extract context around a specific citation marker.

        Args:
            text: Full text
            citation_marker: Citation to find (e.g., "[1]")
            context_window: Override default context window

        Returns:
            Context string or None if not found
        """
        window = context_window or self.context_window

        # Find the citation in text
        position = text.find(citation_marker)
        if position == -1:
            logger.warning(f"Citation marker '{citation_marker}' not found in text")
            return None

        return self._extract_context(text, position, len(citation_marker))

    def _extract_context(
        self, text: str, position: int, marker_length: int
    ) -> str:
        """
        Extract context around a citation at a given position.

        Args:
            text: Full text
            position: Starting position of citation
            marker_length: Length of citation marker

        Returns:
            Context string with citation highlighted
        """
        start = max(0, position - self.context_window)
        end = min(len(text), position + marker_length + self.context_window)

        # Try to break at sentence boundaries
        context_before = text[start:position]
        context_after = text[position + marker_length : end]

        # Find sentence start before citation
        sentence_start = max(
            context_before.rfind(". "),
            context_before.rfind("! "),
            context_before.rfind("? "),
        )
        if sentence_start != -1:
            context_before = context_before[sentence_start + 2 :]

        # Find sentence end after citation
        sentence_end = min(
            [
                idx
                for idx in [
                    context_after.find(". "),
                    context_after.find("! "),
                    context_after.find("? "),
                ]
                if idx != -1
            ]
            + [len(context_after)],
        )
        context_after = context_after[:sentence_end]

        citation_marker = text[position : position + marker_length]
        context = f"{context_before}{citation_marker}{context_after}"

        return context.strip()

    def parse_numeric_citation(self, marker: str) -> List[int]:
        """
        Parse numeric citation marker to extract citation numbers.

        Examples:
            "[1]" -> [1]
            "[2,3]" -> [2, 3]
            "[1-5]" -> [1, 2, 3, 4, 5]

        Args:
            marker: Citation marker (e.g., "[1,2-5]")

        Returns:
            List of citation numbers
        """
        # Remove brackets
        inner = marker.strip("[]")

        citation_nums = []

        # Split by comma
        parts = inner.split(",")

        for part in parts:
            part = part.strip()

            # Check for range (e.g., "1-5")
            if "-" in part:
                start, end = part.split("-")
                citation_nums.extend(range(int(start.strip()), int(end.strip()) + 1))
            else:
                # Single number
                citation_nums.append(int(part))

        return sorted(list(set(citation_nums)))

    def get_citation_stats(self, text: str) -> Dict[str, int]:
        """
        Get statistics about citations in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with citation statistics
        """
        result = self.extract(text)

        # Count by type
        type_counts = {}
        for citation in result.citations:
            type_counts[citation.citation_type] = (
                type_counts.get(citation.citation_type, 0) + 1
            )

        return {
            "total_citations": result.total_count,
            "unique_citations": len(result.unique_markers),
            "numeric": type_counts.get("numeric", 0),
            "named": type_counts.get("named", 0),
            "author_year": type_counts.get("author-year", 0),
            "footnote": type_counts.get("footnote", 0),
        }
