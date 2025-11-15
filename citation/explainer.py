"""Citation explanation using Gemini.

This module uses Gemini to analyze and explain why citations are relevant
and what relationship exists between citing and cited papers.
"""

from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai
from loguru import logger

from .resolver import ResolvedCitation


@dataclass
class CitationExplanation:
    """Explanation of a citation's relevance and context."""

    citation_marker: str
    relevance_score: float  # 0-1 score
    relationship_type: str  # e.g., "builds-on", "contradicts", "compares-with"
    explanation: str  # Natural language explanation
    key_points: list[str]  # Bullet points of key relationships


class CitationExplainer:
    """
    Explains citations using Gemini to analyze relevance and relationships.

    Uses the context where a citation appears and the cited paper's metadata
    to generate explanations of why the citation is relevant.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash-lite",
        temperature: float = 0.3,
    ):
        """
        Initialize the citation explainer.

        Args:
            api_key: Google AI API key
            model_name: Gemini model to use
            temperature: Model temperature (lower = more focused)
        """
        self.model_name = model_name
        self.temperature = temperature

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": temperature},
        )

        logger.info(
            f"CitationExplainer initialized with {model_name} (temp={temperature})"
        )

    def explain(
        self,
        citation_context: str,
        resolved_citation: ResolvedCitation,
        citing_paper_context: Optional[str] = None,
    ) -> CitationExplanation:
        """
        Generate an explanation for why a citation is relevant.

        Args:
            citation_context: The context where citation appears
            resolved_citation: The resolved cited paper
            citing_paper_context: Optional broader context from citing paper

        Returns:
            CitationExplanation with analysis
        """
        # Build prompt
        prompt = self._build_explanation_prompt(
            citation_context, resolved_citation, citing_paper_context
        )

        try:
            # Generate explanation
            response = self.model.generate_content(prompt)
            explanation_text = response.text

            # Parse the response
            explanation = self._parse_explanation(
                explanation_text, resolved_citation.citation_marker
            )

            logger.info(
                f"Generated explanation for '{resolved_citation.citation_marker}' "
                f"(relevance={explanation.relevance_score:.2f})"
            )

            return explanation

        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            # Return a fallback explanation
            return CitationExplanation(
                citation_marker=resolved_citation.citation_marker,
                relevance_score=0.5,
                relationship_type="unknown",
                explanation=f"Citation to: {resolved_citation.title}",
                key_points=[
                    f"Cited paper: {resolved_citation.title}",
                    f"Authors: {', '.join(resolved_citation.authors[:3])}",
                ],
            )

    def _build_explanation_prompt(
        self,
        citation_context: str,
        resolved_citation: ResolvedCitation,
        citing_paper_context: Optional[str] = None,
    ) -> str:
        """Build prompt for citation explanation."""
        prompt = f"""You are analyzing a citation in a research paper to explain its relevance and relationship.

**Citation Context** (where the citation appears):
{citation_context}

**Cited Paper Information**:
- Title: {resolved_citation.title}
- Authors: {', '.join(resolved_citation.authors[:5])}
- Abstract: {resolved_citation.abstract[:500]}...

"""

        if citing_paper_context:
            prompt += f"""**Citing Paper Context**:
{citing_paper_context[:500]}...

"""

        prompt += """Please analyze this citation and provide:

1. **Relevance Score** (0.0-1.0): How relevant is this citation to the citing context?
2. **Relationship Type**: Choose ONE from:
   - builds-on: The citing paper builds upon this work
   - compares-with: The citing paper compares approaches
   - contradicts: The citing paper challenges this work
   - provides-background: Background/related work
   - extends: Extends or improves upon this work
   - uses-method: Uses methodology from this work
   - cites-data: References data or results

3. **Explanation** (2-3 sentences): Why is this citation relevant and what is the relationship?

4. **Key Points** (2-4 bullet points): Specific connections between the papers

Format your response as:
RELEVANCE: [score]
RELATIONSHIP: [type]
EXPLANATION: [text]
KEY_POINTS:
- [point 1]
- [point 2]
- [point 3]
"""

        return prompt

    def _parse_explanation(
        self, response_text: str, citation_marker: str
    ) -> CitationExplanation:
        """Parse the model's explanation response."""
        # Initialize defaults
        relevance_score = 0.5
        relationship_type = "provides-background"
        explanation = ""
        key_points = []

        # Parse structured response
        lines = response_text.strip().split("\n")

        in_key_points = False
        explanation_lines = []

        for line in lines:
            line = line.strip()

            if line.startswith("RELEVANCE:"):
                try:
                    score_text = line.split(":", 1)[1].strip()
                    relevance_score = float(score_text)
                    relevance_score = max(0.0, min(1.0, relevance_score))
                except (ValueError, IndexError):
                    pass

            elif line.startswith("RELATIONSHIP:"):
                try:
                    relationship_type = line.split(":", 1)[1].strip().lower()
                except IndexError:
                    pass

            elif line.startswith("EXPLANATION:"):
                try:
                    explanation = line.split(":", 1)[1].strip()
                    in_key_points = False
                except IndexError:
                    pass

            elif line.startswith("KEY_POINTS:"):
                in_key_points = True

            elif in_key_points and line.startswith("-"):
                key_point = line.lstrip("- ").strip()
                if key_point:
                    key_points.append(key_point)

            elif explanation and not in_key_points and line:
                # Continuation of explanation
                explanation_lines.append(line)

        # Combine explanation lines
        if explanation_lines:
            explanation += " " + " ".join(explanation_lines)

        # Fallback if parsing failed
        if not explanation:
            explanation = response_text[:200]

        if not key_points:
            key_points = ["Relevant citation to related work"]

        return CitationExplanation(
            citation_marker=citation_marker,
            relevance_score=relevance_score,
            relationship_type=relationship_type,
            explanation=explanation.strip(),
            key_points=key_points[:4],  # Limit to 4 points
        )

    def explain_batch(
        self,
        citations: list[tuple[str, ResolvedCitation]],
        citing_paper_context: Optional[str] = None,
    ) -> dict[str, CitationExplanation]:
        """
        Explain multiple citations in batch.

        Args:
            citations: List of (context, resolved_citation) tuples
            citing_paper_context: Optional broader context

        Returns:
            Dictionary mapping citation markers to explanations
        """
        results = {}

        for context, resolved_citation in citations:
            try:
                explanation = self.explain(
                    context, resolved_citation, citing_paper_context
                )
                results[resolved_citation.citation_marker] = explanation
            except Exception as e:
                logger.error(
                    f"Error explaining '{resolved_citation.citation_marker}': {e}"
                )

        logger.info(f"Generated {len(results)} citation explanations")
        return results
