"""Test script for citation explanation with ArXiv resolution."""

import sys
from pathlib import Path

from loguru import logger

from agent import ResearchAgent, ToolRegistry
from config import config
from rag import DocumentProcessor, Retriever, VectorStore

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_citation_explanation():
    """Test the citation explanation feature with ArXiv resolution."""
    print("=" * 70)
    print("Citation Explanation Testing")
    print("=" * 70)

    try:
        # Initialize system
        print("\n[1/3] Initializing system...")

        doc_processor = DocumentProcessor(
            chunk_size=config.rag.chunk_size,
            chunk_overlap=config.rag.chunk_overlap,
        )

        vector_store = VectorStore(
            db_path=config.vector_store.db_path,
            collection_name=config.vector_store.collection_name,
            embedding_model_name=config.embedding.model_name,
        )

        retriever = Retriever(vector_store, doc_processor)
        tool_registry = ToolRegistry(
            retriever,
            api_key=config.model.api_key,
            perplexity_api_key=config.model.perplexity_api_key
        )

        agent = ResearchAgent(
            tool_registry=tool_registry,
            api_key=config.model.api_key,
            model_name=config.model.name,
            max_iterations=config.agent.max_iterations,
            temperature=config.model.temperature,
            verbose=config.agent.verbose,
        )

        print("   [OK] System initialized")

        # Get paper ID
        papers = retriever.list_papers()
        if not papers:
            print("\n   [ERROR] No papers in corpus. Run test_ingestion.py first.")
            return 1

        paper_id = papers[0]["paper_id"]
        print(f"\n[2/3] Testing with paper: {papers[0]['title'][:50]}...")

        # Test citation explanation
        print("\n[3/3] Testing citation explanation with ArXiv resolution...")
        print("-" * 70)

        query = f"Explain why the citation 'Tucker et al. (2021)' is relevant in paper '{paper_id}'. Resolve it to the actual paper."

        print(f"\nQuestion: {query}")
        print(f"\nAgent is thinking...\n")

        try:
            response = agent.query(query)

            if response.success:
                print(f"[SUCCESS] Answer:\n")
                print(f"{response.answer}\n")
                print(f"[Steps: {len(response.steps)}, Tools used: {[s.tool_name for s in response.steps]}]")
                print(f"\n[OK] Citation explanation feature working!")
                return 0
            else:
                print(f"[FAILED] Error: {response.error}")
                return 1

        except Exception as e:
            print(f"[ERROR] Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1

    except Exception as e:
        print(f"\n[FATAL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_citation_explanation()
    sys.exit(exit_code)
