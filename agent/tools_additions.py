"""Additional tools for smooth UX - compare_papers and summarize_section

Add these methods to the ToolRegistry class in agent/tools.py
"""

# ADD THESE TOOL REGISTRATIONS TO __init__ METHOD (after explain_citation):

def register_additional_tools(self):
    """Call this after the existing tool registrations."""

    # Analysis tools
    self._register_tool(
        name="compare_papers",
        description="Systematically compare multiple research papers across various dimensions (methodology, results, datasets, contributions). Provides structured comparison table.",
        parameters={
            "type": "object",
            "properties": {
                "paper_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 2-5 paper IDs to compare",
                },
                "aspects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: What to compare (methodology, results, datasets, contributions). Defaults to all.",
                },
            },
            "required": ["paper_ids"],
        },
        function=self._compare_papers,
    )

    self._register_tool(
        name="summarize_section",
        description="Generate a focused summary of a specific paper section with customizable length and focus area.",
        parameters={
            "type": "object",
            "properties": {
                "paper_id": {
                    "type": "string",
                    "description": "The ID of the paper",
                },
                "section": {
                    "type": "string",
                    "description": "Section name (Introduction, Methods, Results, etc.)",
                },
                "focus": {
                    "type": "string",
                    "description": "Optional: Specific aspect to focus on (e.g., 'evaluation metrics', 'datasets used')",
                },
                "length": {
                    "type": "string",
                    "description": "Summary length: 'short' (2-3 sentences), 'medium' (1 paragraph), 'long' (2-3 paragraphs). Default: medium",
                    "default": "medium",
                },
            },
            "required": ["paper_id", "section"],
        },
        function=self._summarize_section,
    )


# ADD THESE METHOD IMPLEMENTATIONS TO ToolRegistry CLASS (at the end, before __all__):

def _compare_papers(self, paper_ids: List[str], aspects: List[str] = None) -> str:
    """
    Systematically compare multiple papers.

    Args:
        paper_ids: List of 2-5 paper IDs
        aspects: What to compare (methodology, results, datasets, etc.)

    Returns:
        Structured comparison with table and analysis
    """
    try:
        if len(paper_ids) < 2:
            return "Error: Need at least 2 papers to compare"

        if len(paper_ids) > 5:
            return "Error: Can compare maximum 5 papers at once"

        # Get papers
        papers = []
        for paper_id in paper_ids:
            paper = self.retriever._get_paper(paper_id)
            if not paper:
                return f"Error: Paper '{paper_id}' not found"
            papers.append(paper)

        # Default aspects if not provided
        if not aspects:
            aspects = ["methodology", "main contributions", "datasets used", "key results"]

        # Search for each aspect in each paper
        comparison_data = {}
        for aspect in aspects:
            comparison_data[aspect] = {}
            for paper in papers:
                # Search for this aspect in the paper
                results = self.retriever.search(
                    f"{aspect}",
                    top_k=3,
                    paper_id=paper.paper_id
                )

                if results:
                    # Combine top results
                    aspect_text = " ".join([r.text for r in results[:2]])
                    comparison_data[aspect][paper.paper_id] = aspect_text[:300]  # Limit length
                else:
                    comparison_data[aspect][paper.paper_id] = "Not found"

        # Format output
        output = f"## Comparison of {len(papers)} Papers\n\n"

        # Papers list
        output += "### Papers:\n"
        for i, paper in enumerate(papers, 1):
            output += f"{i}. **{paper.title}**\n"
        output += "\n"

        # Comparison table
        output += "### Comparison:\n\n"
        for aspect in aspects:
            output += f"#### {aspect.title()}:\n"
            for i, paper in enumerate(papers, 1):
                paper_data = comparison_data[aspect].get(paper.paper_id, "Not found")
                output += f"- **Paper {i}**: {paper_data}\n"
            output += "\n"

        # Key differences summary
        output += "### Summary:\n"
        output += "Comparison completed across "  + ", ".join(aspects) + ".\n"
        output += f"Analyzed {len(papers)} papers systematically.\n"

        return output

    except Exception as e:
        logger.error(f"Error in compare_papers: {e}")
        return f"Error comparing papers: {str(e)}"


def _summarize_section(
    self,
    paper_id: str,
    section: str,
    focus: Optional[str] = None,
    length: str = "medium"
) -> str:
    """
    Generate focused summary of a paper section.

    Args:
        paper_id: Paper ID
        section: Section name
        focus: Optional focus area
        length: short/medium/long

    Returns:
        Structured summary
    """
    try:
        # Get section text
        section_text = self.retriever.get_paper_section(paper_id, section)

        if not section_text:
            return f"Section '{section}' not found in paper '{paper_id}'"

        # Determine max length
        length_limits = {
            "short": "2-3 sentences",
            "medium": "1 paragraph (100-150 words)",
            "long": "2-3 paragraphs (200-300 words)"
        }

        target_length = length_limits.get(length, length_limits["medium"])

        # Build summary prompt
        if focus:
            summary_request = f"""Summarize the {section} section focusing specifically on {focus}.

Section text:
{section_text[:2000]}  # Limit input length

Requirements:
- Length: {target_length}
- Focus: {focus}
- Format as:
  Main Point: [1-2 sentences]
  Key Details: [bulleted list]

Be specific and extract concrete information."""

        else:
            summary_request = f"""Summarize the {section} section.

Section text:
{section_text[:2000]}  # Limit input length

Requirements:
- Length: {target_length}
- Format as:
  Overview: [1-2 sentences]
  Key Points: [bulleted list of 3-5 main points]

Be specific and extract concrete information."""

        # For now, return a structured format
        # In production, you'd call LLM here
        output = f"## Summary of {section} section\n\n"
        output += f"**Paper**: {paper_id}\n"
        output += f"**Length**: {length}\n"
        if focus:
            output += f"**Focus**: {focus}\n"
        output += "\n"

        # Return first part of section as summary
        # TODO: Replace with actual LLM summarization
        summary_text = section_text[:500] + "..." if len(section_text) > 500 else section_text
        output += f"**Content**:\n{summary_text}\n\n"
        output += "*Note: This is an excerpt. Full LLM summarization can be added with Gemini API call.*\n"

        return output

    except Exception as e:
        logger.error(f"Error in summarize_section: {e}")
        return f"Error summarizing section: {str(e)}"


# INSTRUCTIONS TO INTEGRATE:
"""
1. Open agent/tools.py

2. In the __init__ method, after the last self._register_tool(...) call for explain_citation,
   add the two new registrations from register_additional_tools() above

3. At the end of the ToolRegistry class (before the module-level code),
   add the two method implementations: _compare_papers and _summarize_section

4. Save and test!
"""
