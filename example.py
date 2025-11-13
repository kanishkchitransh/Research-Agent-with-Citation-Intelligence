"""Example usage of the Research Agent."""

from pathlib import Path

from loguru import logger

from agent import ResearchAgent, ToolRegistry
from config import config
from rag import DocumentProcessor, Retriever, VectorStore


def main():
    """Run example queries."""

    logger.info("Setting up Research Agent...")

    # 1. Initialize components
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

    # 2. Ingest papers (if not already done)
    papers_dir = Path("./data/papers")
    if papers_dir.exists():
        pdf_files = list(papers_dir.glob("*.pdf"))
        if pdf_files:
            print(f"\nFound {len(pdf_files)} PDF files. Ingesting...")
            paper_ids = retriever.ingest_directory(papers_dir)
            print(f"Successfully ingested {len(paper_ids)} papers:\n")
            for paper_id in paper_ids:
                print(f"  - {paper_id}")
        else:
            print("\nNo PDF files found. Add some papers to ./data/papers/")
            return
    else:
        print("\nPapers directory not found. Add papers to ./data/papers/")
        return

    # 3. Initialize agent
    tool_registry = ToolRegistry(retriever)
    agent = ResearchAgent(
        tool_registry=tool_registry,
        api_key=config.model.api_key,
        model_name=config.model.name,
        max_iterations=config.agent.max_iterations,
        verbose=True,
    )

    print("\n" + "=" * 70)
    print("Research Agent Examples")
    print("=" * 70)

    # Example 1: List papers
    print("\n\nExample 1: List all papers")
    print("-" * 70)
    response = agent.query("List all papers in the corpus with their titles")
    print(f"\nAnswer:\n{response.answer}")
    print(f"\nSteps taken: {len(response.steps)}")

    # Example 2: Search across papers
    print("\n\nExample 2: Search for information")
    print("-" * 70)
    response = agent.query("What are the main contributions of these papers?")
    print(f"\nAnswer:\n{response.answer}")
    print(f"\nSteps taken: {len(response.steps)}")

    # Example 3: Get specific section
    if paper_ids:
        print("\n\nExample 3: Get specific section")
        print("-" * 70)
        response = agent.query(
            f"What does the Introduction section of paper '{paper_ids[0]}' say?"
        )
        print(f"\nAnswer:\n{response.answer}")
        print(f"\nSteps taken: {len(response.steps)}")

    # Example 4: Citation intelligence
    print("\n\nExample 4: Citation intelligence")
    print("-" * 70)
    response = agent.query(
        "Find a citation in one of the papers and explain what it's about"
    )
    print(f"\nAnswer:\n{response.answer}")
    print(f"\nSteps taken: {len(response.steps)}")

    # Example 5: Comparison
    if len(paper_ids) > 1:
        print("\n\nExample 5: Compare papers")
        print("-" * 70)
        response = agent.query(
            "Compare the methodologies used in the first two papers"
        )
        print(f"\nAnswer:\n{response.answer}")
        print(f"\nSteps taken: {len(response.steps)}")

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
