"""Test script for the Research Agent - Non-interactive mode."""

import sys
from pathlib import Path

from loguru import logger

from agent import ResearchAgent, ToolRegistry
from config import config
from rag import DocumentProcessor, Retriever, VectorStore

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_agent():
    """Test the Research Agent with sample queries."""
    print("=" * 70)
    print("Research Agent Testing (Non-interactive)")
    print("=" * 70)

    try:
        # Initialize system
        print("\n[1/4] Initializing system components...")

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

        print("   [OK] System initialized")

        # Check vector store stats
        print("\n[2/4] Checking vector store...")
        stats = vector_store.get_stats()
        print(f"   [OK] Total papers: {stats['total_papers']}")
        print(f"   [OK] Total chunks: {stats['total_chunks']}")

        if stats['total_papers'] == 0:
            print("\n   [WARNING] No papers in vector store!")
            print("   Please run test_ingestion.py first to ingest papers.")
            return

        # Define test queries
        test_queries = [
            {
                "name": "List Papers",
                "query": "List all papers in the corpus",
                "description": "Tests list_papers tool"
            },
            {
                "name": "Get Abstract",
                "query": "What is the abstract of the paper?",
                "description": "Tests retrieval and paper_abstract tool"
            },
            {
                "name": "Search Query",
                "query": "What are the main findings about syntax evaluation?",
                "description": "Tests search_corpus tool"
            },
        ]

        print(f"\n[3/4] Running {len(test_queries)} test queries...")
        print("-" * 70)

        results = []
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n[Query {i}/{len(test_queries)}] {test_case['name']}")
            print(f"Question: {test_case['query']}")
            print(f"Purpose: {test_case['description']}")
            print("\nAgent is thinking...\n")

            try:
                response = agent.query(test_case['query'])

                if response.success:
                    print(f"[SUCCESS] Answer:")
                    print(f"{response.answer}\n")
                    print(f"[Steps used: {len(response.steps)}]")
                    results.append({"test": test_case['name'], "status": "PASS"})
                else:
                    print(f"[FAILED] Error: {response.error}")
                    results.append({"test": test_case['name'], "status": "FAIL", "error": response.error})

            except Exception as e:
                print(f"[ERROR] Exception occurred: {str(e)}")
                results.append({"test": test_case['name'], "status": "ERROR", "error": str(e)})

            print("-" * 70)

        # Summary
        print("\n[4/4] Test Summary")
        print("=" * 70)
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        errors = sum(1 for r in results if r["status"] == "ERROR")

        for result in results:
            status_symbol = {
                "PASS": "[OK]",
                "FAIL": "[FAIL]",
                "ERROR": "[ERROR]"
            }[result["status"]]
            print(f"{status_symbol} {result['test']}")
            if "error" in result:
                print(f"      Error: {result['error']}")

        print(f"\nTotal: {len(results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print("=" * 70)

        if passed == len(results):
            print("\n[SUCCESS] All tests passed!")
            return 0
        else:
            print(f"\n[WARNING] {failed + errors} test(s) did not pass")
            return 1

    except Exception as e:
        print(f"\n[FATAL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_agent()
    sys.exit(exit_code)
