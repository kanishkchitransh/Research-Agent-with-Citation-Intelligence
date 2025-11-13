"""Main script to run the Research Agent."""

import sys
from pathlib import Path

from loguru import logger

from agent import ResearchAgent, ToolRegistry
from config import config
from rag import DocumentProcessor, Retriever, VectorStore

# Configure logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=config.paths.logs_dir.name if hasattr(config.paths, 'logs_dir') else "INFO",
)
logger.add(
    config.paths.logs_dir / "agent.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
)


def initialize_system():
    """Initialize all system components."""
    logger.info("Initializing Research Agent system...")

    # Initialize document processor
    doc_processor = DocumentProcessor(
        chunk_size=config.rag.chunk_size,
        chunk_overlap=config.rag.chunk_overlap,
    )

    # Initialize vector store
    vector_store = VectorStore(
        db_path=config.vector_store.db_path,
        collection_name=config.vector_store.collection_name,
        embedding_model_name=config.embedding.model_name,
    )

    # Initialize retriever
    retriever = Retriever(vector_store, doc_processor)

    # Check if we need to ingest papers
    stats = vector_store.get_stats()
    if stats.get("total_papers", 0) == 0:
        logger.info("No papers in vector store. Checking for papers to ingest...")
        papers_dir = config.paths.papers_dir

        if papers_dir.exists():
            pdf_files = list(papers_dir.glob("*.pdf"))
            if pdf_files:
                logger.info(f"Found {len(pdf_files)} PDF files. Ingesting...")
                paper_ids = retriever.ingest_directory(papers_dir)
                logger.info(f"Successfully ingested {len(paper_ids)} papers")
            else:
                logger.warning(
                    f"No PDF files found in {papers_dir}. "
                    f"Add some papers to get started!"
                )
        else:
            logger.warning(
                f"Papers directory {papers_dir} does not exist. "
                f"Creating it now. Add PDF files to this directory."
            )
            papers_dir.mkdir(parents=True, exist_ok=True)

    # Initialize tool registry
    tool_registry = ToolRegistry(retriever)

    # Initialize agent
    if not config.model.api_key:
        logger.error(
            "Google API key not found! "
            "Please set GOOGLE_API_KEY in your .env file"
        )
        sys.exit(1)

    agent = ResearchAgent(
        tool_registry=tool_registry,
        api_key=config.model.api_key,
        model_name=config.model.name,
        max_iterations=config.agent.max_iterations,
        temperature=config.model.temperature,
        verbose=config.agent.verbose,
    )

    logger.info("System initialized successfully!")

    return agent, retriever


def interactive_mode(agent: ResearchAgent):
    """Run the agent in interactive mode."""
    logger.info("Starting interactive mode. Type 'exit' or 'quit' to stop.")
    print("\n" + "=" * 70)
    print("Research Agent with Citation Intelligence")
    print("=" * 70)
    print("\nAvailable commands:")
    print("  - Ask any question about the papers")
    print("  - 'list' - List all papers in the corpus")
    print("  - 'stats' - Show system statistics")
    print("  - 'help' - Show this help message")
    print("  - 'exit' or 'quit' - Exit the program")
    print("\nExamples:")
    print("  - What are the main contributions of these papers?")
    print("  - Explain citation [3] in paper X")
    print("  - Compare the methods used in these papers")
    print("=" * 70 + "\n")

    while True:
        try:
            question = input("\nYou: ").strip()

            if not question:
                continue

            if question.lower() in ["exit", "quit", "q"]:
                print("\nGoodbye!")
                break

            if question.lower() == "help":
                print("\nAvailable commands:")
                print("  - Ask any question about the papers")
                print("  - 'list' - List all papers in the corpus")
                print("  - 'stats' - Show system statistics")
                print("  - 'exit' or 'quit' - Exit the program")
                continue

            if question.lower() == "stats":
                stats = agent.get_stats()
                print("\nSystem Statistics:")
                print(f"  Model: {stats['model']}")
                print(f"  Max iterations: {stats['max_iterations']}")
                print(f"  Available tools: {stats['num_tools']}")
                print(f"  Tools: {', '.join(stats['tools'])}")
                continue

            if question.lower() == "list":
                # Get list of papers from agent
                response = agent.query("List all papers in the corpus")
                print(f"\nAgent: {response.answer}")
                continue

            # Regular question
            print("\nAgent: Thinking...\n")
            response = agent.query(question)

            if response.success:
                print(f"Agent: {response.answer}")
                if response.steps and config.agent.verbose:
                    print(f"\n[Used {len(response.steps)} reasoning steps]")
            else:
                print(f"Agent: Sorry, I encountered an error: {response.error}")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"\nError: {e}")


def main():
    """Main entry point."""
    try:
        # Initialize system
        agent, retriever = initialize_system()

        # Show stats
        stats = retriever.get_stats()
        print(f"\nSystem ready! Loaded {stats['vector_store']['total_papers']} papers.")

        # Run interactive mode
        interactive_mode(agent)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
