"""Test script for citation intelligence features."""

import sys
from pathlib import Path

from loguru import logger

from agent import ResearchAgent, ToolRegistry
from config import config
from rag import DocumentProcessor, Retriever, VectorStore

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_citation_intelligence():
    """Test the citation intelligence features."""
    print("=" * 70)
    print("Citation Intelligence Testing")
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
        tool_registry = ToolRegistry(retriever, api_key=config.model.api_key)

        agent = ResearchAgent(
            tool_registry=tool_registry,
            api_key=config.model.api_key,
            model_name=config.model.name,
            max_iterations=config.agent.max_iterations,
            temperature=config.model.temperature,
            verbose=config.agent.verbose,
        )

        print("   [OK] System initialized with citation intelligence")

        # Check tools
        stats = agent.get_stats()
        print(f"   [OK] Agent has {stats['num_tools']} tools (including 2 citation intelligence tools)")

        # Get paper ID
        papers = retriever.list_papers()
        if not papers:
            print("\n   [ERROR] No papers in corpus. Run test_ingestion.py first.")
            return 1

        paper_id = papers[0]["paper_id"]
        print(f"\n[2/3] Testing with paper: {papers[0]['title'][:50]}...")

        # Test queries
        test_queries = [
            {
                "name": "Extract Citations",
                "query": f"Extract all citations from the paper with ID '{paper_id}'",
                "description": "Tests extract_citations tool",
            },
            {
                "name": "Find Citation Context",
                "query": f"What citations are mentioned in the paper '{paper_id}'? Show me the context of one of them.",
                "description": "Tests citation extraction and context retrieval",
            },
        ]

        print(f"\n[3/3] Running {len(test_queries)} citation intelligence tests...")
        print("-" * 70)

        results = []
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n[Test {i}/{len(test_queries)}] {test_case['name']}")
            print(f"Question: {test_case['query']}")
            print(f"\nAgent is thinking...\n")

            try:
                response = agent.query(test_case['query'])

                if response.success:
                    print(f"[SUCCESS] Answer:")
                    print(f"{response.answer}\n")
                    print(f"[Steps: {len(response.steps)}, Tools used: {[s.tool_name for s in response.steps]}]")
                    results.append({"test": test_case['name'], "status": "PASS"})
                else:
                    print(f"[FAILED] Error: {response.error}")
                    results.append({"test": test_case['name'], "status": "FAIL", "error": response.error})

            except Exception as e:
                print(f"[ERROR] Exception: {str(e)}")
                results.append({"test": test_case['name'], "status": "ERROR", "error": str(e)})

            print("-" * 70)

        # Summary
        print("\nTest Summary")
        print("=" * 70)
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] in ["FAIL", "ERROR"])

        for result in results:
            status_symbol = {
                "PASS": "[OK]",
                "FAIL": "[FAIL]",
                "ERROR": "[ERROR]"
            }[result["status"]]
            print(f"{status_symbol} {result['test']}")

        print(f"\nTotal: {len(results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print("=" * 70)

        if passed == len(results):
            print("\n[SUCCESS] All citation intelligence tests passed!")
            return 0
        else:
            print(f"\n[WARNING] {failed} test(s) did not pass")
            return 1

    except Exception as e:
        print(f"\n[FATAL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_citation_intelligence()
    sys.exit(exit_code)
