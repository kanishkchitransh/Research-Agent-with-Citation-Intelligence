"""Document processing for research papers - PDF parsing and chunking."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from loguru import logger
from pydantic import BaseModel


class DocumentChunk(BaseModel):
    """A chunk of document text with metadata."""

    text: str
    paper_id: str
    chunk_id: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    metadata: Dict = {}


class Paper(BaseModel):
    """A research paper with metadata."""

    paper_id: str
    title: str
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    full_text: str
    sections: Dict[str, str] = {}
    citations: List[str] = []
    metadata: Dict = {}


class DocumentProcessor:
    """Process research papers - extract text, parse sections, chunk content."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the document processor.

        Args:
            chunk_size: Maximum size of each text chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(
            f"DocumentProcessor initialized (chunk_size={chunk_size}, overlap={chunk_overlap})"
        )

    def process_pdf(self, pdf_path: Path) -> Paper:
        """
        Process a PDF research paper.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Paper object with extracted content and metadata
        """
        logger.info(f"Processing PDF: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            paper_id = pdf_path.stem

            # Extract text from all pages
            full_text = ""
            page_texts = []
            for page_num, page in enumerate(doc):
                text = page.get_text()
                page_texts.append((page_num + 1, text))
                full_text += text + "\n"

            # Extract title (usually first large text on first page)
            title = self._extract_title(doc)

            # Extract abstract
            abstract = self._extract_abstract(full_text)

            # Parse sections
            sections = self._parse_sections(full_text)

            # Extract citations
            citations = self._extract_citations(full_text)

            paper = Paper(
                paper_id=paper_id,
                title=title,
                abstract=abstract,
                full_text=full_text,
                sections=sections,
                citations=citations,
                metadata={
                    "file_path": str(pdf_path),
                    "num_pages": len(doc),
                },
            )

            doc.close()
            logger.info(
                f"Successfully processed {paper_id}: {len(full_text)} chars, {len(sections)} sections"
            )
            return paper

        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise

    def _extract_title(self, doc: fitz.Document) -> str:
        """Extract title from the first page."""
        try:
            first_page = doc[0]
            blocks = first_page.get_text("blocks")

            # Find the largest text block in the top portion of the page
            title_candidates = []
            for block in blocks:
                x0, y0, x1, y1, text, block_no, block_type = block
                # Only consider blocks in the top 30% of the page
                if y0 < first_page.rect.height * 0.3:
                    text = text.strip()
                    if len(text) > 10 and len(text) < 300:  # Reasonable title length
                        title_candidates.append((text, y0))

            if title_candidates:
                # Return the topmost substantial text
                title_candidates.sort(key=lambda x: x[1])
                return title_candidates[0][0].replace("\n", " ")

            return "Untitled"
        except Exception as e:
            logger.warning(f"Could not extract title: {e}")
            return "Untitled"

    def _extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from the paper text."""
        # Common patterns for abstract section
        patterns = [
            r"Abstract[:\s]+(.*?)(?=\n\s*\n|\n\s*(?:1\.|I\.|Introduction))",
            r"ABSTRACT[:\s]+(.*?)(?=\n\s*\n|\n\s*(?:1\.|I\.|INTRODUCTION))",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                abstract = match.group(1).strip()
                # Clean up the abstract
                abstract = re.sub(r"\s+", " ", abstract)
                return abstract

        return None

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Parse paper into sections (Introduction, Methods, etc.)."""
        sections = {}

        # Common section headers in research papers
        section_patterns = [
            r"(?:^|\n)\s*(?:\d+\.?\s+)?([A-Z][A-Za-z\s]+?)(?:\n|$)",
        ]

        # Common section names
        common_sections = [
            "Introduction",
            "Related Work",
            "Background",
            "Method",
            "Methods",
            "Methodology",
            "Approach",
            "Experiments",
            "Results",
            "Discussion",
            "Conclusion",
            "Future Work",
            "References",
        ]

        # Find section headers
        lines = text.split("\n")
        section_indices = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            for section_name in common_sections:
                # Check if line is a section header
                if (
                    line_stripped.lower() == section_name.lower()
                    or line_stripped.lower().startswith(section_name.lower())
                ):
                    section_indices.append((i, section_name, line_stripped))
                    break

        # Extract section content
        for idx, (line_num, section_name, header) in enumerate(section_indices):
            start = line_num + 1
            end = (
                section_indices[idx + 1][0] if idx + 1 < len(section_indices) else len(lines)
            )
            content = "\n".join(lines[start:end]).strip()
            sections[section_name] = content

        return sections

    def _extract_citations(self, text: str) -> List[str]:
        """Extract citation references from the paper."""
        citations = []

        # Pattern for numbered citations like [1], [12]
        numbered_pattern = r"\[(\d+)\]"
        numbered_matches = re.findall(numbered_pattern, text)
        citations.extend([f"[{num}]" for num in set(numbered_matches)])

        # Pattern for author-year citations like (Smith et al., 2020)
        author_year_pattern = r"\(([A-Z][a-z]+(?:\s+et\s+al\.)?(?:,\s*\d{4})?)\)"
        author_year_matches = re.findall(author_year_pattern, text)
        citations.extend(list(set(author_year_matches)))

        return citations

    def chunk_paper(self, paper: Paper, include_metadata: bool = True) -> List[DocumentChunk]:
        """
        Chunk a paper into smaller pieces for vector storage.

        Args:
            paper: Paper object to chunk
            include_metadata: Whether to include metadata in chunks

        Returns:
            List of DocumentChunk objects
        """
        chunks = []

        # Chunk by sections if available
        if paper.sections:
            for section_name, section_text in paper.sections.items():
                section_chunks = self._chunk_text(section_text)
                for idx, chunk_text in enumerate(section_chunks):
                    chunk = DocumentChunk(
                        text=chunk_text,
                        paper_id=paper.paper_id,
                        chunk_id=f"{paper.paper_id}_section_{section_name}_{idx}",
                        section=section_name,
                        metadata=paper.metadata if include_metadata else {},
                    )
                    chunks.append(chunk)
        else:
            # Chunk the full text if sections not available
            text_chunks = self._chunk_text(paper.full_text)
            for idx, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    text=chunk_text,
                    paper_id=paper.paper_id,
                    chunk_id=f"{paper.paper_id}_chunk_{idx}",
                    metadata=paper.metadata if include_metadata else {},
                )
                chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks for paper {paper.paper_id}")
        return chunks

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # If not at the end, try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence boundary (period, question mark, exclamation)
                for char in [". ", "? ", "! ", "\n"]:
                    boundary = text.rfind(char, start, end)
                    if boundary != -1:
                        end = boundary + 1
                        break
                else:
                    # If no sentence boundary, look for word boundary
                    boundary = text.rfind(" ", start, end)
                    if boundary != -1:
                        end = boundary

            chunks.append(text[start:end].strip())

            # Move start position with overlap
            start = end - self.chunk_overlap

        return chunks

    def batch_process_directory(self, directory: Path) -> List[Paper]:
        """
        Process all PDF files in a directory.

        Args:
            directory: Directory containing PDF files

        Returns:
            List of processed Paper objects
        """
        papers = []
        pdf_files = list(directory.glob("*.pdf"))

        logger.info(f"Found {len(pdf_files)} PDF files in {directory}")

        for pdf_path in pdf_files:
            try:
                paper = self.process_pdf(pdf_path)
                papers.append(paper)
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {e}")
                continue

        logger.info(f"Successfully processed {len(papers)} papers")
        return papers
