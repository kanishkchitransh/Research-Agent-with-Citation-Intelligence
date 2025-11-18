"""Tool definitions and implementations for the Research Agent."""

import json
from typing import Any, Callable, Dict, List, Optional

import arxiv
import requests
from loguru import logger

from author_intelligence import AuthorProfileFetcher, InsightGenerator, TrajectoryAnalyzer
from citation import CitationExplainer, CitationExtractor, CitationResolver
from field_intelligence import DomainAnalyzer, TrendDetector, FieldInsightGenerator
from rag.cache_manager import CacheManager
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

    def __init__(
        self,
        retriever: Retriever,
        api_key: Optional[str] = None,
        perplexity_api_key: Optional[str] = None
    ):
        """
        Initialize the tool registry.

        Args:
            retriever: Retriever instance for RAG operations
            api_key: Optional Google API key for citation intelligence and LLM
            perplexity_api_key: Optional Perplexity API key for citation search
        """
        self.retriever = retriever
        self.tools: Dict[str, Tool] = {}
        self.api_key = api_key
        self.perplexity_api_key = perplexity_api_key

        # Initialize citation intelligence components
        self.citation_extractor = CitationExtractor(context_window=200)
        self.citation_resolver = CitationResolver(
            max_results=3,
            google_api_key=api_key,
            perplexity_api_key=perplexity_api_key
        )
        self.citation_explainer = None

        # Initialize explainer if API key provided
        if api_key:
            try:
                self.citation_explainer = CitationExplainer(api_key=api_key)
                logger.info("Citation intelligence initialized with explainer and search APIs")
            except Exception as e:
                logger.warning(f"Could not initialize CitationExplainer: {e}")

        # Initialize author intelligence components
        self.author_profile_fetcher = None
        self.trajectory_analyzer = None
        self.insight_generator = None

        if perplexity_api_key:
            try:
                self.author_profile_fetcher = AuthorProfileFetcher(
                    perplexity_api_key=perplexity_api_key,
                    use_semantic_scholar=True
                )
                self.trajectory_analyzer = TrajectoryAnalyzer()

                if api_key:  # Need Gemini for insights
                    self.insight_generator = InsightGenerator(api_key=api_key)

                logger.info("Author intelligence initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize author intelligence: {e}")

        # Initialize field intelligence components
        self.domain_analyzer = None
        self.trend_detector = None
        self.field_insight_generator = None

        if perplexity_api_key:
            try:
                self.domain_analyzer = DomainAnalyzer(perplexity_api_key=perplexity_api_key)
                self.trend_detector = TrendDetector(perplexity_api_key=perplexity_api_key)

                if api_key:  # Need Gemini for field insights
                    self.field_insight_generator = FieldInsightGenerator(api_key=api_key)

                logger.info("Field intelligence initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize field intelligence: {e}")

        # Initialize cache manager
        self.cache_manager = CacheManager(retriever.vector_store)

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

        # Citation Intelligence tools
        self._register_tool(
            name="extract_citations",
            description="Extract all citations from a paper and get statistics. Shows citation markers, types, and frequency.",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The ID of the paper to extract citations from",
                    },
                },
                "required": ["paper_id"],
            },
            function=self._extract_citations,
        )

        self._register_tool(
            name="explain_citation",
            description="Explain why a citation is relevant and what relationship exists between the citing and cited papers. Requires the citation marker and context.",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The ID of the paper containing the citation",
                    },
                    "citation_marker": {
                        "type": "string",
                        "description": "The citation marker (e.g., '[1]', '[Smith et al.]')",
                    },
                },
                "required": ["paper_id", "citation_marker"],
            },
            function=self._explain_citation,
        )

        # Author Intelligence Tools
        self._register_tool(
            name="get_author_intelligence",
            description="Get comprehensive intelligence about a paper's author including career overview, expertise, publications, and relevance to the current paper. Cached permanently.",
            parameters={
                "type": "object",
                "properties": {
                    "author_name": {
                        "type": "string",
                        "description": "Full name of the author to research",
                    },
                    "paper_id": {
                        "type": "string",
                        "description": "ID of the paper (for context)",
                    },
                    "detail_level": {
                        "type": "string",
                        "description": "Level of detail: 'quick', 'standard', or 'deep'",
                        "enum": ["quick", "standard", "deep"],
                    },
                },
                "required": ["author_name", "paper_id"],
            },
            function=self._get_author_intelligence,
        )

        self._register_tool(
            name="fetch_paper_authors",
            description="Fetch author profiles for all authors of a paper. Prioritizes first and last authors (primary contributors).",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "ID of the paper",
                    },
                    "focus_primary": {
                        "type": "boolean",
                        "description": "If true, only fetch first and last authors immediately",
                    },
                },
                "required": ["paper_id"],
            },
            function=self._fetch_paper_authors,
        )

        self._register_tool(
            name="should_offer_author_intelligence",
            description="Check if author intelligence should be offered to the user based on session preferences. Returns whether to ask user.",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "ID of the paper just uploaded",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Current session ID",
                    },
                },
                "required": ["paper_id", "session_id"],
            },
            function=self._should_offer_author_intelligence,
        )

        # Field Intelligence Tools
        self._register_tool(
            name="get_field_intelligence",
            description="Get comprehensive intelligence about a research field including current state, trends, breakthroughs, and future directions. Cached for 30 days.",
            parameters={
                "type": "object",
                "properties": {
                    "field_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords representing the field (e.g., ['transformers', 'attention', 'NLP'])",
                    },
                    "paper_context": {
                        "type": "string",
                        "description": "Optional paper title/abstract for context",
                    },
                    "detail_level": {
                        "type": "string",
                        "description": "Level of detail: 'quick', 'standard', or 'deep'",
                        "enum": ["quick", "standard", "deep"],
                    },
                },
                "required": ["field_keywords"],
            },
            function=self._get_field_intelligence,
        )

        self._register_tool(
            name="extract_field_keywords",
            description="Extract key research field keywords from a paper using AI. Use this to identify the research domain before getting field intelligence.",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "ID of the paper to analyze",
                    },
                    "max_keywords": {
                        "type": "integer",
                        "description": "Maximum number of keywords to extract (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["paper_id"],
            },
            function=self._extract_field_keywords,
        )

        self._register_tool(
            name="analyze_field_trends",
            description="Analyze recent trends and breakthroughs in a research field. Returns emerging trends, hot topics, and future directions.",
            parameters={
                "type": "object",
                "properties": {
                    "field_name": {
                        "type": "string",
                        "description": "Name of the research field (e.g., 'Natural Language Processing', 'Computer Vision')",
                    },
                    "field_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional keywords for more specific trend analysis",
                    },
                },
                "required": ["field_name"],
            },
            function=self._analyze_field_trends,
        )

        self._register_tool(
            name="get_field_context",
            description="Get quick field context for a paper - combines keyword extraction and field intelligence in one step.",
            parameters={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "ID of the paper",
                    },
                },
                "required": ["paper_id"],
            },
            function=self._get_field_context,
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

    def _extract_citations(self, paper_id: str) -> str:
        """Extract citations from a paper."""
        try:
            # Get paper from retriever
            paper = self.retriever._get_paper(paper_id)

            if not paper:
                return f"Paper '{paper_id}' not found."

            # Extract citations from full text
            extracted = self.citation_extractor.extract(paper.full_text)

            if extracted.total_count == 0:
                return f"No citations found in paper '{paper_id}'."

            # Get statistics
            stats = self.citation_extractor.get_citation_stats(paper.full_text)

            # Format output
            output = f"Citations in paper '{paper_id}':\n\n"
            output += f"Total citations: {stats['total_citations']}\n"
            output += f"Unique citations: {stats['unique_citations']}\n"
            output += f"Citation types:\n"
            output += f"  - Numeric (brackets): {stats['numeric']}\n"
            output += f"  - Named: {stats['named']}\n"
            output += f"  - Author-year: {stats['author_year']}\n"
            output += f"  - Footnote/Endnote: {stats['footnote']}\n\n"

            # Show first 10 unique citations
            output += f"Sample citations:\n"
            for i, marker in enumerate(extracted.unique_markers[:10], 1):
                output += f"  {i}. {marker}\n"

            if len(extracted.unique_markers) > 10:
                output += f"  ... and {len(extracted.unique_markers) - 10} more\n"

            return output

        except Exception as e:
            logger.error(f"Error in extract_citations: {e}")
            return f"Error extracting citations: {str(e)}"

    def _explain_citation(self, paper_id: str, citation_marker: str) -> str:
        """Explain why a citation is relevant."""
        try:
            # Get paper
            paper = self.retriever._get_paper(paper_id)
            if not paper:
                return f"Paper '{paper_id}' not found."

            # Get citation context
            context = self.citation_extractor.extract_citation_context(
                paper.full_text, citation_marker
            )

            if not context:
                return f"Citation '{citation_marker}' not found in paper '{paper_id}'."

            # Try to resolve the citation
            resolved = self.citation_resolver.resolve(citation_marker, context)

            if not resolved:
                return (
                    f"Context around citation '{citation_marker}':\n\n{context}\n\n"
                    f"Note: Could not resolve this citation to an ArXiv paper. "
                    f"The citation may reference a non-ArXiv source or use an "
                    f"unrecognized format."
                )

            # Generate explanation if explainer is available
            if self.citation_explainer:
                explanation = self.citation_explainer.explain(
                    context, resolved, paper.abstract
                )

                output = f"Explanation for citation '{citation_marker}':\n\n"
                output += f"**Cited Paper**: {resolved.title}\n"
                output += f"**Authors**: {', '.join(resolved.authors[:3])}\n"
                output += f"**ArXiv ID**: {resolved.arxiv_id}\n"
                output += f"**Published**: {resolved.published}\n\n"
                output += f"**Relevance Score**: {explanation.relevance_score:.2f}/1.0\n"
                output += f"**Relationship**: {explanation.relationship_type}\n\n"
                output += f"**Explanation**:\n{explanation.explanation}\n\n"
                output += f"**Key Points**:\n"
                for point in explanation.key_points:
                    output += f"  - {point}\n"
                output += f"\n**Citation Context**:\n{context}\n"

                return output
            else:
                # Return basic resolution info without explanation
                output = f"Citation '{citation_marker}' resolved to:\n\n"
                output += f"**Title**: {resolved.title}\n"
                output += f"**Authors**: {', '.join(resolved.authors[:3])}\n"
                output += f"**ArXiv ID**: {resolved.arxiv_id}\n"
                output += f"**Published**: {resolved.published}\n\n"
                output += f"**Context**:\n{context}\n\n"
                output += f"Note: Citation explanation requires API key configuration."

                return output

        except Exception as e:
            logger.error(f"Error in explain_citation: {e}")
            return f"Error explaining citation: {str(e)}"

    # Author Intelligence Tool Implementations

    def _get_author_intelligence(
        self,
        author_name: str,
        paper_id: str,
        detail_level: str = "standard",
    ) -> str:
        """
        Get comprehensive author intelligence with caching.

        Args:
            author_name: Author's full name
            paper_id: Paper ID for context
            detail_level: 'quick', 'standard', or 'deep'

        Returns:
            Formatted author intelligence
        """
        if not self.author_profile_fetcher:
            return "❌ Author intelligence not available (Perplexity API key required)"

        try:
            # Normalize author name for caching
            normalized_name = self.author_profile_fetcher.normalize_author_name(author_name)

            # Check cache first (PERMANENT)
            cached_profile = self.cache_manager.get_cached_author(normalized_name)

            if cached_profile:
                logger.info(f"✓ Using cached profile for {author_name}")
                # Generate fresh summary even with cached data
                profile = cached_profile  # Already a dict
            else:
                # Fetch fresh profile
                logger.info(f"Fetching fresh profile for {author_name}")

                # Get paper context
                paper = self.retriever._get_paper(paper_id)
                paper_context = paper.abstract if paper and paper.abstract else None

                # Fetch profile
                profile_obj = self.author_profile_fetcher.fetch_profile(
                    author_name=author_name,
                    paper_context=paper_context
                )

                # Convert to dict for caching
                profile = {
                    "name": profile_obj.name,
                    "normalized_name": profile_obj.normalized_name,
                    "institution": profile_obj.institution,
                    "years_active": profile_obj.years_active,
                    "expertise_areas": profile_obj.expertise_areas,
                    "career_overview": profile_obj.career_overview,
                    "recent_work": profile_obj.recent_work,
                    "breakthrough_papers": profile_obj.breakthrough_papers,
                    "current_focus": profile_obj.current_focus,
                    "publication_count": profile_obj.publication_count,
                    "citation_count": profile_obj.citation_count,
                    "h_index": profile_obj.h_index,
                    "top_papers": profile_obj.top_papers,
                    "collaborators": profile_obj.collaborators,
                    "fetched_at": profile_obj.fetched_at,
                    "sources_used": profile_obj.sources_used,
                }

                # Cache permanently
                self.cache_manager.store_author_cache(normalized_name, profile)
                logger.info(f"✓ Cached profile for {author_name} permanently")

            # Generate summary based on detail level
            output = f"## Author Intelligence: {author_name}\n\n"

            if detail_level == "quick":
                # Quick summary (for UI cards)
                output += f"**Institution:** {profile.get('institution', 'Unknown')}\n"
                output += f"**Expertise:** {', '.join(profile.get('expertise_areas', [])[:3])}\n"
                output += f"**Publications:** {profile.get('publication_count', 0)} papers, "
                output += f"{profile.get('citation_count', 0)} citations (h-index: {profile.get('h_index', 0)})\n\n"

                if profile.get('current_focus'):
                    output += f"**Current Focus:** {profile.get('current_focus')}\n"

            elif detail_level == "standard":
                # Standard summary with trajectory
                output += f"**Institution:** {profile.get('institution', 'Unknown')}\n"
                output += f"**Expertise Areas:** {', '.join(profile.get('expertise_areas', []))}\n"
                output += f"**Years Active:** {profile.get('years_active', 'Active researcher')}\n\n"

                output += f"**Publication Metrics:**\n"
                output += f"- Papers: {profile.get('publication_count', 0)}\n"
                output += f"- Citations: {profile.get('citation_count', 0)}\n"
                output += f"- H-index: {profile.get('h_index', 0)}\n\n"

                if profile.get('career_overview'):
                    output += f"**Career Overview:**\n{profile.get('career_overview')[:500]}...\n\n"

                if profile.get('top_papers'):
                    output += "**Notable Papers:**\n"
                    for paper in profile.get('top_papers', [])[:3]:
                        output += f"- {paper['title']} ({paper['year']}) - {paper['citations']} citations\n"
                    output += "\n"

            elif detail_level == "deep":
                # Deep analysis with all details
                output += self._format_deep_author_analysis(profile)

            output += f"\n*Data sources: {', '.join(profile.get('sources_used', []))}, cached permanently*"

            return output

        except Exception as e:
            logger.error(f"Error in get_author_intelligence: {e}")
            return f"❌ Error fetching author intelligence: {str(e)}"

    def _fetch_paper_authors(self, paper_id: str, focus_primary: bool = True) -> str:
        """
        Fetch profiles for all authors of a paper.

        Args:
            paper_id: Paper ID
            focus_primary: If True, prioritize first and last authors

        Returns:
            Formatted list of author profiles
        """
        if not self.author_profile_fetcher:
            return "❌ Author intelligence not available"

        try:
            # Get paper
            paper = self.retriever._get_paper(paper_id)

            if not paper:
                return f"❌ Paper '{paper_id}' not found"

            # Extract author names (for MVP, assume from paper metadata)
            # In production, would parse from PDF properly
            author_names = []

            # Try to extract from paper title/abstract (simplified)
            if hasattr(paper, 'authors') and paper.authors:
                author_names = paper.authors
            else:
                return f"⚠️ No author information found for paper '{paper_id}'"

            if not author_names:
                return f"⚠️ Could not extract author names from paper"

            # Fetch profiles
            profiles = self.author_profile_fetcher.fetch_multiple_authors(
                author_names,
                prioritize_first_last=focus_primary
            )

            # Format output
            output = f"## Authors of '{paper.title}'\n\n"
            output += f"Found {len(profiles)} authors:\n\n"

            for i, profile_obj in enumerate(profiles, 1):
                output += f"### {i}. {profile_obj.name}\n"
                output += f"- Institution: {profile_obj.institution or 'Unknown'}\n"
                output += f"- Expertise: {', '.join(profile_obj.expertise_areas[:2]) if profile_obj.expertise_areas else 'N/A'}\n"
                output += f"- Publications: {profile_obj.publication_count} ({profile_obj.h_index} h-index)\n"

                if i <= 1 or i == len(profiles):  # First or last
                    output += f"  *Primary author - full profile available*\n"

                output += "\n"

            return output

        except Exception as e:
            logger.error(f"Error in fetch_paper_authors: {e}")
            return f"❌ Error fetching authors: {str(e)}"

    def _should_offer_author_intelligence(self, paper_id: str, session_id: str) -> str:
        """
        Check if author intelligence should be offered based on session preferences.

        Args:
            paper_id: Paper ID just uploaded
            session_id: Current session ID

        Returns:
            JSON string with {should_offer: bool, message: str}
        """
        try:
            # Check session preference
            declined = self.cache_manager.get_session_preference(
                session_id,
                "author_intelligence_declined"
            )

            if declined:
                logger.info(f"User previously declined author intelligence in session {session_id}")
                return json.dumps({
                    "should_offer": False,
                    "message": "User previously declined author intelligence this session"
                })

            # Get paper details
            paper = self.retriever._get_paper(paper_id)

            if not paper:
                return json.dumps({
                    "should_offer": False,
                    "message": "Paper not found"
                })

            # Suggest asking user
            message = f"Would you like to know about the authors of '{paper.title}'? " \
                      f"I can provide background on their research and expertise."

            return json.dumps({
                "should_offer": True,
                "message": message,
                "paper_title": paper.title
            })

        except Exception as e:
            logger.error(f"Error in should_offer_author_intelligence: {e}")
            return json.dumps({
                "should_offer": False,
                "message": f"Error: {str(e)}"
            })

    def _format_deep_author_analysis(self, profile: Dict) -> str:
        """Format deep author analysis."""
        output = ""

        # Full details
        output += f"**Name:** {profile.get('name')}\n"
        output += f"**Institution:** {profile.get('institution', 'Unknown')}\n"
        output += f"**Normalized Name:** {profile.get('normalized_name')}\n"
        output += f"**Years Active:** {profile.get('years_active', 'Active')}\n"
        output += f"**Expertise Areas:** {', '.join(profile.get('expertise_areas', []))}\n\n"

        output += f"**Publication Metrics:**\n"
        output += f"- Total Papers: {profile.get('publication_count', 0)}\n"
        output += f"- Total Citations: {profile.get('citation_count', 0)}\n"
        output += f"- H-index: {profile.get('h_index', 0)}\n\n"

        if profile.get('career_overview'):
            output += f"**Career Overview:**\n{profile.get('career_overview')}\n\n"

        if profile.get('recent_work'):
            output += f"**Recent Work:**\n{profile.get('recent_work')}\n\n"

        if profile.get('current_focus'):
            output += f"**Current Focus:**\n{profile.get('current_focus')}\n\n"

        if profile.get('top_papers'):
            output += "**Top Papers (by citations):**\n"
            for paper in profile.get('top_papers', [])[:5]:
                output += f"- **{paper['title']}** ({paper['year']})\n"
                output += f"  Citations: {paper['citations']}\n"
            output += "\n"

        if profile.get('collaborators'):
            output += f"**Key Collaborators:** {', '.join(profile.get('collaborators', [])[:10])}\n\n"

        output += f"**Data Sources:** {', '.join(profile.get('sources_used', []))}\n"
        output += f"**Last Updated:** {profile.get('fetched_at')}\n"

        return output

    # Field Intelligence Tool Implementations

    def _get_field_intelligence(
        self,
        field_keywords: List[str],
        paper_context: Optional[str] = None,
        detail_level: str = "standard",
    ) -> str:
        """
        Get comprehensive field intelligence with caching.

        Args:
            field_keywords: Keywords representing the field
            paper_context: Optional paper context
            detail_level: 'quick', 'standard', or 'deep'

        Returns:
            Formatted field intelligence
        """
        if not self.domain_analyzer:
            return "❌ Field intelligence not available (Perplexity API key required)"

        try:
            # Create hash for caching (keywords + context)
            import hashlib
            cache_key_data = '|'.join(sorted(field_keywords))
            if paper_context:
                cache_key_data += f"|{paper_context[:100]}"
            domain_hash = hashlib.md5(cache_key_data.encode()).hexdigest()

            logger.info(f"Getting field intelligence for keywords: {field_keywords}")

            # Check cache first (30-day TTL)
            cached_field = self.cache_manager.get_cached_field(domain_hash)

            if cached_field:
                logger.info(f"✓ Using cached field data")
                field_profile = cached_field.get('field_profile')
                trends = cached_field.get('trends')
            else:
                logger.info(f"Fetching fresh field data")

                # Analyze domain
                field_profile_obj = self.domain_analyzer.analyze_field(
                    field_keywords=field_keywords,
                    paper_context=paper_context
                )

                # Detect trends
                trends_obj = None
                if self.trend_detector:
                    trends_obj = self.trend_detector.detect_trends(
                        field_name=field_profile_obj.field_name,
                        field_keywords=field_keywords
                    )

                # Convert to dict for caching
                field_profile = field_profile_obj.to_dict()
                trends = trends_obj.to_dict() if trends_obj else None

                # Cache for 30 days
                cache_data = {
                    'field_profile': field_profile,
                    'trends': trends
                }
                self.cache_manager.store_field_cache(domain_hash, cache_data)

            # Generate output based on detail level
            if detail_level == "quick":
                if self.field_insight_generator:
                    from field_intelligence import FieldProfile
                    profile_obj = FieldProfile.from_dict(field_profile)
                    return self.field_insight_generator.generate_quick_summary(
                        profile_obj,
                        paper_context
                    )
                else:
                    return self._format_quick_field_summary(field_profile)

            elif detail_level == "standard":
                if self.field_insight_generator and trends:
                    from field_intelligence import FieldProfile, FieldTrends
                    profile_obj = FieldProfile.from_dict(field_profile)
                    trends_obj = FieldTrends.from_dict(trends) if trends else None
                    return self.field_insight_generator.generate_standard_analysis(
                        profile_obj,
                        trends_obj,
                        paper_context
                    )
                else:
                    return self._format_standard_field_analysis(field_profile, trends)

            elif detail_level == "deep":
                if self.field_insight_generator and trends:
                    from field_intelligence import FieldProfile, FieldTrends
                    profile_obj = FieldProfile.from_dict(field_profile)
                    trends_obj = FieldTrends.from_dict(trends)
                    sections = self.field_insight_generator.generate_deep_analysis(
                        profile_obj,
                        trends_obj,
                        paper_context
                    )
                    return self._format_deep_field_sections(sections)
                else:
                    return self._format_deep_field_analysis(field_profile, trends)

        except Exception as e:
            logger.error(f"Error in get_field_intelligence: {e}")
            return f"❌ Error fetching field intelligence: {str(e)}"

    def _extract_field_keywords(
        self,
        paper_id: str,
        max_keywords: int = 5
    ) -> str:
        """
        Extract field keywords from a paper using AI.

        Args:
            paper_id: Paper ID
            max_keywords: Maximum keywords to extract

        Returns:
            JSON string with extracted keywords
        """
        if not self.field_insight_generator:
            return json.dumps({
                "success": False,
                "error": "Keyword extraction requires Gemini API key"
            })

        try:
            # Get paper
            paper = self.retriever._get_paper(paper_id)

            if not paper:
                return json.dumps({
                    "success": False,
                    "error": f"Paper '{paper_id}' not found"
                })

            # Use Gemini to extract keywords
            import google.generativeai as genai

            prompt = f"""Extract {max_keywords} key research field keywords from this paper.

Title: {paper.title}
Abstract: {paper.abstract[:500] if paper.abstract else 'Not available'}

Return ONLY a comma-separated list of keywords (e.g., "transformers, attention mechanism, NLP, language models, deep learning").
Focus on field/domain keywords, not specific techniques."""

            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(prompt)
            keywords_str = response.text.strip()

            # Parse keywords
            keywords = [k.strip() for k in keywords_str.split(',')][:max_keywords]

            return json.dumps({
                "success": True,
                "keywords": keywords,
                "paper_title": paper.title
            })

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    def _analyze_field_trends(
        self,
        field_name: str,
        field_keywords: Optional[List[str]] = None
    ) -> str:
        """
        Analyze trends in a research field.

        Args:
            field_name: Name of the field
            field_keywords: Optional keywords for specific analysis

        Returns:
            Formatted trends analysis
        """
        if not self.trend_detector:
            return "❌ Trend analysis not available (Perplexity API key required)"

        try:
            logger.info(f"Analyzing trends for field: {field_name}")

            # Detect trends
            trends = self.trend_detector.detect_trends(
                field_name=field_name,
                field_keywords=field_keywords
            )

            # Format output
            output = f"## 🔬 Field Trends: {field_name}\n\n"

            output += "### 🚀 Recent Breakthroughs (Last 2-3 Years)\n"
            for i, breakthrough in enumerate(trends.recent_breakthroughs, 1):
                output += f"{i}. {breakthrough}\n"
            output += "\n"

            output += "### 📈 Emerging Trends\n"
            for i, trend in enumerate(trends.emerging_trends, 1):
                output += f"{i}. {trend}\n"
            output += "\n"

            output += "### 🎯 Future Research Directions\n"
            for i, direction in enumerate(trends.research_directions, 1):
                output += f"{i}. {direction}\n"
            output += "\n"

            output += "### 🔥 Hot Topics\n"
            for i, topic in enumerate(trends.hot_topics, 1):
                output += f"{i}. {topic}\n"
            output += "\n"

            output += "### ⚠️ Key Challenges\n"
            for i, challenge in enumerate(trends.key_challenges, 1):
                output += f"{i}. {challenge}\n"
            output += "\n"

            if trends.timeline_summary:
                output += f"### 📅 Evolution\n{trends.timeline_summary}\n\n"

            if trends.impact_areas:
                output += "### 🌍 Real-World Impact\n"
                for i, impact in enumerate(trends.impact_areas, 1):
                    output += f"{i}. {impact}\n"

            return output

        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return f"❌ Error analyzing trends: {str(e)}"

    def _get_field_context(self, paper_id: str) -> str:
        """
        Get quick field context for a paper (combines keyword extraction + field intelligence).

        Args:
            paper_id: Paper ID

        Returns:
            Formatted field context
        """
        try:
            # First, extract keywords
            keywords_result = self._extract_field_keywords(paper_id, max_keywords=5)
            keywords_data = json.loads(keywords_result)

            if not keywords_data.get('success'):
                return f"❌ Could not extract keywords: {keywords_data.get('error')}"

            keywords = keywords_data.get('keywords', [])

            if not keywords:
                return "❌ No keywords extracted from paper"

            # Get paper context
            paper = self.retriever._get_paper(paper_id)
            paper_context = f"{paper.title}\n{paper.abstract[:200]}" if paper and paper.abstract else paper.title if paper else None

            # Get field intelligence
            field_intel = self._get_field_intelligence(
                field_keywords=keywords,
                paper_context=paper_context,
                detail_level="standard"
            )

            # Combine results
            output = f"## 📊 Field Context for '{paper.title}'\n\n"
            output += f"**Extracted Keywords:** {', '.join(keywords)}\n\n"
            output += "---\n\n"
            output += field_intel

            return output

        except Exception as e:
            logger.error(f"Error getting field context: {e}")
            return f"❌ Error getting field context: {str(e)}"

    # Field Intelligence Formatting Helpers

    def _format_quick_field_summary(self, field_profile: Dict) -> str:
        """Fallback quick field summary."""
        return f"""**{field_profile.get('field_name')}** ({field_profile.get('primary_domain')})

{field_profile.get('description', 'No description available')[:200]}...

Key areas: {', '.join(field_profile.get('subdomains', [])[:3])}"""

    def _format_standard_field_analysis(self, field_profile: Dict, trends: Optional[Dict]) -> str:
        """Fallback standard field analysis."""
        output = f"## 🔬 {field_profile.get('field_name')}\n\n"
        output += f"**Domain:** {field_profile.get('primary_domain')}\n\n"
        output += f"**Description:** {field_profile.get('description')}\n\n"
        output += f"**Subdomains:** {', '.join(field_profile.get('subdomains', []))}\n\n"
        output += f"**Key Concepts:** {', '.join(field_profile.get('key_concepts', [])[:5])}\n\n"
        output += f"**Major Venues:** {', '.join(field_profile.get('major_venues', [])[:3])}\n\n"

        if trends:
            output += "### Recent Trends\n\n"
            output += f"**Breakthroughs:** {', '.join(trends.get('recent_breakthroughs', [])[:3])}\n\n"
            output += f"**Emerging:** {', '.join(trends.get('emerging_trends', [])[:3])}\n\n"

        return output

    def _format_deep_field_analysis(self, field_profile: Dict, trends: Optional[Dict]) -> str:
        """Fallback deep field analysis."""
        output = self._format_standard_field_analysis(field_profile, trends)

        output += f"\n**Current State:** {field_profile.get('current_state', 'Not available')}\n\n"
        output += f"**Key Researchers:** {', '.join(field_profile.get('key_researchers', []))}\n\n"

        if trends:
            output += f"**Future Directions:** {', '.join(trends.get('research_directions', []))}\n\n"
            output += f"**Key Challenges:** {', '.join(trends.get('key_challenges', []))}\n"

        return output

    def _format_deep_field_sections(self, sections: Dict[str, str]) -> str:
        """Format deep field sections from Gemini."""
        output = ""
        for section_name, content in sections.items():
            output += f"## {section_name}\n\n{content}\n\n"
        return output
