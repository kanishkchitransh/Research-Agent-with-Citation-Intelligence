"""Test script to debug PDF ingestion."""

import sys
import traceback
from pathlib import Path

from loguru import logger
from config import config
from rag import DocumentProcessor, VectorStore, Retriever

# Configure logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")

def test_ingestion():
    """Test PDF ingestion and see the full error."""
    try:
        print("=" * 70)
        print("Testing PDF Ingestion")
        print("=" * 70)

        # Initialize components
        print("\n1. Initializing DocumentProcessor...")
        doc_processor = DocumentProcessor(
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap,
        )
        print("   [OK] DocumentProcessor initialized")

        print("\n2. Initializing VectorStore...")
        vector_store = VectorStore(
            db_path=config.vector_store.db_path,
            collection_name=config.vector_store.collection_name,
            embedding_model_name=config.embedding.model_name,
        )
        print("   [OK] VectorStore initialized")

        print("\n3. Initializing Retriever...")
        retriever = Retriever(vector_store, doc_processor)
        print("   [OK] Retriever initialized")

        # Find PDF
        print("\n4. Finding PDF files...")
        papers_dir = config.paths.papers_dir
        pdf_files = list(papers_dir.glob("*.pdf"))

        if not pdf_files:
            print(f"   [ERROR] No PDF files found in {papers_dir}")
            return

        pdf_file = pdf_files[0]
        print(f"   [OK] Found PDF: {pdf_file.name}")

        # Process PDF
        print("\n5. Processing PDF...")
        paper = doc_processor.process_pdf(pdf_file)
        print(f"   [OK] Processed: {len(paper.full_text)} chars, {len(paper.sections)} sections")

        # Chunk paper
        print("\n6. Chunking paper...")
        chunks = doc_processor.chunk_paper(paper)
        print(f"   [OK] Created {len(chunks)} chunks")

        # Add to vector store (this is where it likely fails)
        print("\n7. Adding to vector store...")
        print("   (This may take 1-2 minutes for embedding generation...)")
        vector_store.add_paper(paper, chunks)
        print("   [OK] Successfully added to vector store!")

        # Verify
        print("\n8. Verifying...")
        stats = vector_store.get_stats()
        print(f"   [OK] Total chunks: {stats['total_chunks']}")
        print(f"   [OK] Total papers: {stats['total_papers']}")

        print("\n" + "=" * 70)
        print("SUCCESS: PDF ingestion test passed!")
        print("=" * 70)

    except Exception as e:
        print("\n" + "=" * 70)
        print("ERROR: PDF ingestion failed")
        print("=" * 70)
        print(f"\nError type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        print("=" * 70)
        sys.exit(1)

if __name__ == "__main__":
    test_ingestion()
