"""Retriever for RAG - combines document processing and vector search."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .document_processor import DocumentProcessor, Paper
from .vector_store import VectorStore


class SearchResult:
    """A search result with context."""

    def __init__(
        self,
        text: str,
        paper_id: str,
        paper_title: str,
        section: str,
        score: float,
        metadata: Dict[str, Any],
    ):
        self.text = text
        self.paper_id = paper_id
        self.paper_title = paper_title
        self.section = section
        self.score = score
        self.metadata = metadata

    def __repr__(self) -> str:
        return f"SearchResult(paper={self.paper_id}, section={self.section}, score={self.score:.3f})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "paper_id": self.paper_id,
            "paper_title": self.paper_title,
            "section": self.section,
            "score": self.score,
            "metadata": self.metadata,
        }


class Retriever:
    """
    High-level retriever that manages document processing and vector search.
    Main interface for RAG operations.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        document_processor: DocumentProcessor,
    ):
        """
        Initialize the retriever.

        Args:
            vector_store: VectorStore instance
            document_processor: DocumentProcessor instance
        """
        self.vector_store = vector_store
        self.document_processor = document_processor
        self._papers_cache: Dict[str, Paper] = {}
        logger.info("Retriever initialized")

    def ingest_paper(self, pdf_path: Path) -> str:
        """
        Ingest a research paper into the system.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Paper ID
        """
        logger.info(f"Ingesting paper: {pdf_path}")

        # Process the PDF
        paper = self.document_processor.process_pdf(pdf_path)

        # Chunk the paper
        chunks = self.document_processor.chunk_paper(paper)

        # Add to vector store
        self.vector_store.add_paper(paper, chunks)

        # Cache the paper
        self._papers_cache[paper.paper_id] = paper

        logger.info(f"Successfully ingested paper: {paper.paper_id}")
        return paper.paper_id

    def ingest_directory(self, directory: Path) -> List[str]:
        """
        Ingest all papers from a directory.

        Args:
            directory: Directory containing PDF files

        Returns:
            List of paper IDs
        """
        logger.info(f"Ingesting papers from directory: {directory}")

        papers = self.document_processor.batch_process_directory(directory)
        paper_ids = []

        for paper in papers:
            try:
                chunks = self.document_processor.chunk_paper(paper)
                self.vector_store.add_paper(paper, chunks)
                self._papers_cache[paper.paper_id] = paper
                paper_ids.append(paper.paper_id)
            except Exception as e:
                logger.error(f"Failed to ingest paper {paper.paper_id}: {e}")
                continue

        logger.info(f"Successfully ingested {len(paper_ids)} papers")
        return paper_ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        paper_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Search for relevant content across papers.

        Args:
            query: Search query
            top_k: Number of results to return
            paper_id: Optional paper ID to search within

        Returns:
            List of SearchResult objects
        """
        logger.info(f"Searching: '{query}' (top_k={top_k}, paper_id={paper_id})")

        if paper_id:
            raw_results = self.vector_store.search_by_paper(query, paper_id, top_k)
        else:
            raw_results = self.vector_store.search(query, top_k)

        # Convert to SearchResult objects
        search_results = []
        for result in raw_results:
            metadata = result["metadata"]
            search_result = SearchResult(
                text=result["text"],
                paper_id=metadata.get("paper_id", "unknown"),
                paper_title=metadata.get("title", "Unknown"),
                section=metadata.get("section", "unknown"),
                score=1.0 - result.get("distance", 0.0),  # Convert distance to similarity
                metadata=metadata,
            )
            search_results.append(search_result)

        logger.info(f"Found {len(search_results)} results")
        return search_results

    def get_paper_section(self, paper_id: str, section_name: str) -> Optional[str]:
        """
        Get a specific section from a paper.

        Args:
            paper_id: Paper ID
            section_name: Name of the section (e.g., "Introduction", "Methods")

        Returns:
            Section text or None if not found
        """
        paper = self._get_paper(paper_id)
        if not paper:
            logger.warning(f"Paper {paper_id} not found")
            return None

        # Try exact match first
        if section_name in paper.sections:
            return paper.sections[section_name]

        # Try case-insensitive match
        for key, value in paper.sections.items():
            if key.lower() == section_name.lower():
                return value

        logger.warning(f"Section '{section_name}' not found in paper {paper_id}")
        return None

    def get_paper_abstract(self, paper_id: str) -> Optional[str]:
        """
        Get the abstract of a paper.

        Args:
            paper_id: Paper ID

        Returns:
            Abstract text or None if not found
        """
        paper = self._get_paper(paper_id)
        if not paper:
            return None
        return paper.abstract

    def get_paper_citations(self, paper_id: str) -> List[str]:
        """
        Get all citations from a paper.

        Args:
            paper_id: Paper ID

        Returns:
            List of citation strings
        """
        paper = self._get_paper(paper_id)
        if not paper:
            return []
        return paper.citations

    def get_citation_context(
        self,
        paper_id: str,
        citation_ref: str,
        context_window: int = 500,
    ) -> Optional[str]:
        """
        Get the context around a specific citation in a paper.

        Args:
            paper_id: Paper ID
            citation_ref: Citation reference (e.g., "[12]" or "Smith et al.")
            context_window: Number of characters before and after citation

        Returns:
            Context string or None if not found
        """
        paper = self._get_paper(paper_id)
        if not paper:
            return None

        full_text = paper.full_text
        citation_pos = full_text.find(citation_ref)

        if citation_pos == -1:
            logger.warning(f"Citation '{citation_ref}' not found in paper {paper_id}")
            return None

        # Extract context
        start = max(0, citation_pos - context_window)
        end = min(len(full_text), citation_pos + len(citation_ref) + context_window)

        context = full_text[start:end]
        return context

    def list_papers(self) -> List[Dict[str, str]]:
        """
        List all papers in the system.

        Returns:
            List of paper info dictionaries
        """
        paper_ids = self.vector_store.get_all_papers()
        papers_info = []

        for paper_id in paper_ids:
            paper = self._get_paper(paper_id)
            if paper:
                papers_info.append(
                    {
                        "paper_id": paper_id,
                        "title": paper.title,
                        "num_sections": len(paper.sections),
                        "num_citations": len(paper.citations),
                    }
                )

        return papers_info

    def get_stats(self) -> Dict[str, Any]:
        """
        Get system statistics.

        Returns:
            Dictionary with statistics
        """
        vector_stats = self.vector_store.get_stats()
        return {
            "vector_store": vector_stats,
            "cached_papers": len(self._papers_cache),
        }

    def _get_paper(self, paper_id: str) -> Optional[Paper]:
        """
        Get a paper from cache or vector store.

        Args:
            paper_id: Paper ID

        Returns:
            Paper object or None
        """
        # Check cache first
        if paper_id in self._papers_cache:
            return self._papers_cache[paper_id]

        # Try to reconstruct from vector store
        chunks = self.vector_store.get_paper_chunks(paper_id)
        if not chunks:
            return None

        # Get metadata from first chunk
        if chunks and chunks[0]["metadata"]:
            metadata = chunks[0]["metadata"]

            # Reconstruct full text from all chunks (sorted by chunk_id)
            sorted_chunks = sorted(chunks, key=lambda c: c["metadata"].get("chunk_id", c["id"]))
            full_text = "\n".join([chunk["text"] for chunk in sorted_chunks])

            # Reconstruct sections (group chunks by section)
            sections = {}
            for chunk in chunks:
                section_name = chunk["metadata"].get("section", "unknown")
                if section_name not in sections:
                    sections[section_name] = []
                sections[section_name].append(chunk["text"])

            # Combine section texts
            sections = {k: "\n".join(v) for k, v in sections.items()}

            # Create Paper object with reconstructed data
            paper = Paper(
                paper_id=paper_id,
                title=metadata.get("title", "Unknown"),
                full_text=full_text,
                sections=sections,
                citations=[],  # Would need separate storage for citations
            )
            self._papers_cache[paper_id] = paper
            return paper

        return None
