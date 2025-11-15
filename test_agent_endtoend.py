"""Test the full agent end-to-end with citation intelligence."""

import os
from dotenv import load_dotenv
from pathlib import Path

from agent import ResearchAgent, ToolRegistry
from rag import DocumentProcessor, Retriever, VectorStore
from config import config

load_dotenv()

print("="*70)
print("END-TO-END AGENT TEST WITH CITATION INTELLIGENCE")
print("="*70)

# Check papers
papers_dir = Path("./data/papers")
pdfs = list(papers_dir.glob("*.pdf"))
print(f"\nPapers in data/papers/: {len(pdfs)}")
if pdfs:
    for pdf in pdfs:
        print(f"  - {pdf.name}")

# Initialize system
print("\nInitializing RAG system...")
doc_processor = DocumentProcessor(
    chunk_size=config.rag.chunk_size,
    chunk_overlap=config.rag.chunk_overlap
)

vector_store = VectorStore(
    db_path=config.vector_store.db_path,
    collection_name=config.vector_store.collection_name,
    embedding_model_name=config.embedding.model_name
)

retriever = Retriever(vector_store, doc_processor)

# Check vector store stats
stats = vector_store.get_stats()
print(f"\nVector Store Stats:")
print(f"  Total chunks: {stats.get('total_chunks', 0)}")
print(f"  Total papers: {stats.get('total_papers', 0)}")
print(f"  Papers: {stats.get('papers', [])}")

# Initialize agent
print("\nInitializing Research Agent with Citation Intelligence...")
tool_registry = ToolRegistry(retriever)
agent = ResearchAgent(
    tool_registry=tool_registry,
    api_key=config.model.api_key,
    model_name=config.model.name,
    max_iterations=config.agent.max_iterations,
    verbose=False  # Less verbose for cleaner output
)

print(f"\nAgent initialized with {len(tool_registry.tools)} tools")
print("Tools available:", list(tool_registry.tools.keys()))

# Test 1: List papers
print("\n" + "="*70)
print("TEST 1: List Papers")
print("="*70)
response = agent.query("List all papers in the corpus")
print(f"\n{response.answer}")

# Test 2: Ask about the paper content
print("\n" + "="*70)
print("TEST 2: Query About Paper Content")
print("="*70)
response = agent.query("What is the main contribution of the paper?")
print(f"\n{response.answer}")
print(f"[Used {len(response.steps)} reasoning steps]")

# Test 3: Extract citations from the paper
print("\n" + "="*70)
print("TEST 3: Extract Citations")
print("="*70)
paper_id = stats.get('papers', [])[0] if stats.get('papers') else None
if paper_id:
    response = agent.query(f"Extract all citations from paper '{paper_id}'")
    print(f"\n{response.answer}")
    print(f"[Used {len(response.steps)} reasoning steps]")
else:
    print("No papers available for citation extraction")

# Test 4: Explain a specific citation (with Perplexity resolution!)
print("\n" + "="*70)
print("TEST 4: Explain Citation (WITH PERPLEXITY RESOLUTION)")
print("="*70)
if paper_id:
    # This will use Perplexity to find and explain the citation
    response = agent.query(f"Find a citation in paper '{paper_id}' and explain what it's about using web search")
    print(f"\n{response.answer}")
    print(f"[Used {len(response.steps)} reasoning steps]")

print("\n" + "="*70)
print("END-TO-END TEST COMPLETE!")
print("="*70)
