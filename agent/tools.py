"""Tool definitions and implementations for the Research Agent."""

import json
from typing import Any, Callable, Dict, List, Optional

import arxiv
import requests
from loguru import logger

from rag.retriever import Retriever


class Tool:
    """A tool that the agent can use."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable,
    ):
        """
        Initialize a tool.

        Args:
            name: Tool name
            description: Description of what the tool does
            parameters: JSON schema for tool parameters
            function: The function to call
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self.function = function

    def __call__(self, **kwargs) -> Any:
        """Execute the tool."""
        return self.function(**kwargs)

    def to_gemini_format(self) -> Dict[str, Any]:
        """Convert tool definition to Gemini function calling format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Registry of tools available to the agent."""

    def __init__(self, retriever: Retriever):
        """
        Initialize the tool registry.

        Args:
            retriever: Retriever instance for RAG operations
        """
        self.retriever = retriever
        self.tools: Dict[str, Tool] = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available tools."""
        # Core RAG tools
        self._register_tool(
            name="search_corpus",
            description="Search across all research papers in the corpus using semantic similarity. Returns relevant passages from papers.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant information",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
            function=self._search_corpus,
        )

        self._register_tool(
            name="get_paper_section",
            description="Get a specific section from a research paper (e.g., Introduction, Methods, Results, Conclusion).",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The ID of the paper",
                    },
                    "section_name": {
                        "type": "string",
                        "description": "Name of the section to retrieve",
                    },
                },
                "required": ["paper_id", "section_name"],
            },
            function=self._get_paper_section,
        )

        self._register_tool(
            name="get_citation_context",
            description="Get the context around a specific citation in a paper. Returns the text surrounding the citation to understand why it was cited.",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The ID of the paper containing the citation",
                    },
                    "citation_ref": {
                        "type": "string",
                        "description": "The citation reference (e.g., '[12]' or 'Smith et al.')",
                    },
                },
                "required": ["paper_id", "citation_ref"],
            },
            function=self._get_citation_context,
        )

        # Citation intelligence tools
        self._register_tool(
            name="search_arxiv",
            description="Search ArXiv for research papers. Useful for finding cited papers or related work.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (can be paper title, authors, or keywords)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 3)",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
            function=self._search_arxiv,
        )

        self._register_tool(
            name="get_arxiv_paper",
            description="Get detailed information about a paper from ArXiv using its ID.",
            parameters={
                "type": "object",
                "properties": {
                    "arxiv_id": {
                        "type": "string",
                        "description": "ArXiv paper ID (e.g., '2103.14030')",
                    },
                },
                "required": ["arxiv_id"],
            },
            function=self._get_arxiv_paper,
        )

        # Analysis tools
        self._register_tool(
            name="list_papers",
            description="List all papers currently in the corpus with their metadata.",
            parameters={
                "type": "object",
                "properties": {},
            },
            function=self._list_papers,
        )

        self._register_tool(
            name="search_within_paper",
            description="Search for specific content within a single paper.",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The ID of the paper to search within",
                    },
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["paper_id", "query"],
            },
            function=self._search_within_paper,
        )

        self._register_tool(
            name="get_paper_abstract",
            description="Get the abstract of a specific paper.",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The ID of the paper",
                    },
                },
                "required": ["paper_id"],
            },
            function=self._get_paper_abstract,
        )

    def _register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable,
    ):
        """Register a tool."""
        tool = Tool(name, description, parameters, function)
        self.tools[name] = tool
        logger.debug(f"Registered tool: {name}")

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self.tools.values())

    def get_tools_for_gemini(self) -> List[Dict[str, Any]]:
        """Get all tools in Gemini function calling format."""
        return [tool.to_gemini_format() for tool in self.tools.values()]

    # Tool implementations
    def _search_corpus(self, query: str, top_k: int = 5) -> str:
        """Search across all papers."""
        try:
            results = self.retriever.search(query, top_k=top_k)

            if not results:
                return "No relevant results found."

            output = f"Found {len(results)} relevant passages:\n\n"
            for i, result in enumerate(results, 1):
                output += f"Result {i} (from '{result.paper_title}' - {result.section}):\n"
                output += f"{result.text}\n"
                output += f"[Score: {result.score:.3f}]\n\n"

            return output

        except Exception as e:
            logger.error(f"Error in search_corpus: {e}")
            return f"Error searching corpus: {str(e)}"

    def _get_paper_section(self, paper_id: str, section_name: str) -> str:
        """Get a specific section from a paper."""
        try:
            section_text = self.retriever.get_paper_section(paper_id, section_name)

            if not section_text:
                return f"Section '{section_name}' not found in paper '{paper_id}'."

            return f"Section '{section_name}' from paper '{paper_id}':\n\n{section_text}"

        except Exception as e:
            logger.error(f"Error in get_paper_section: {e}")
            return f"Error retrieving section: {str(e)}"

    def _get_citation_context(self, paper_id: str, citation_ref: str) -> str:
        """Get context around a citation."""
        try:
            context = self.retriever.get_citation_context(paper_id, citation_ref)

            if not context:
                return f"Citation '{citation_ref}' not found in paper '{paper_id}'."

            return f"Context around citation '{citation_ref}' in paper '{paper_id}':\n\n{context}"

        except Exception as e:
            logger.error(f"Error in get_citation_context: {e}")
            return f"Error retrieving citation context: {str(e)}"

    def _search_arxiv(self, query: str, max_results: int = 3) -> str:
        """Search ArXiv for papers."""
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )

            results = list(search.results())

            if not results:
                return f"No papers found on ArXiv for query: '{query}'"

            output = f"Found {len(results)} papers on ArXiv:\n\n"
            for i, paper in enumerate(results, 1):
                output += f"{i}. {paper.title}\n"
                output += f"   Authors: {', '.join([author.name for author in paper.authors])}\n"
                output += f"   Published: {paper.published.strftime('%Y-%m-%d')}\n"
                output += f"   ArXiv ID: {paper.entry_id.split('/')[-1]}\n"
                output += f"   Abstract: {paper.summary[:200]}...\n\n"

            return output

        except Exception as e:
            logger.error(f"Error in search_arxiv: {e}")
            return f"Error searching ArXiv: {str(e)}"

    def _get_arxiv_paper(self, arxiv_id: str) -> str:
        """Get paper details from ArXiv."""
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(search.results())

            output = f"Paper: {paper.title}\n\n"
            output += f"Authors: {', '.join([author.name for author in paper.authors])}\n"
            output += f"Published: {paper.published.strftime('%Y-%m-%d')}\n"
            output += f"ArXiv ID: {arxiv_id}\n\n"
            output += f"Abstract:\n{paper.summary}\n\n"
            output += f"PDF: {paper.pdf_url}\n"

            return output

        except Exception as e:
            logger.error(f"Error in get_arxiv_paper: {e}")
            return f"Error retrieving ArXiv paper: {str(e)}"

    def _list_papers(self) -> str:
        """List all papers in the corpus."""
        try:
            papers = self.retriever.list_papers()

            if not papers:
                return "No papers in the corpus yet."

            output = f"Papers in corpus ({len(papers)}):\n\n"
            for i, paper in enumerate(papers, 1):
                output += f"{i}. {paper['title']}\n"
                output += f"   ID: {paper['paper_id']}\n"
                output += f"   Sections: {paper['num_sections']}, Citations: {paper['num_citations']}\n\n"

            return output

        except Exception as e:
            logger.error(f"Error in list_papers: {e}")
            return f"Error listing papers: {str(e)}"

    def _search_within_paper(self, paper_id: str, query: str, top_k: int = 5) -> str:
        """Search within a specific paper."""
        try:
            results = self.retriever.search(query, top_k=top_k, paper_id=paper_id)

            if not results:
                return f"No relevant results found in paper '{paper_id}'."

            output = f"Found {len(results)} relevant passages in paper '{paper_id}':\n\n"
            for i, result in enumerate(results, 1):
                output += f"Result {i} ({result.section}):\n"
                output += f"{result.text}\n"
                output += f"[Score: {result.score:.3f}]\n\n"

            return output

        except Exception as e:
            logger.error(f"Error in search_within_paper: {e}")
            return f"Error searching within paper: {str(e)}"

    def _get_paper_abstract(self, paper_id: str) -> str:
        """Get paper abstract."""
        try:
            abstract = self.retriever.get_paper_abstract(paper_id)

            if not abstract:
                return f"Abstract not found for paper '{paper_id}'."

            return f"Abstract of paper '{paper_id}':\n\n{abstract}"

        except Exception as e:
            logger.error(f"Error in get_paper_abstract: {e}")
            return f"Error retrieving abstract: {str(e)}"
