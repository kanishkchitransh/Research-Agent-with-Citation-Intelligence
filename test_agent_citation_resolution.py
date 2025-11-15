"""Test agent with full Perplexity citation resolution."""

import os
from dotenv import load_dotenv
from pathlib import Path

from agent import ResearchAgent, ToolRegistry
from rag import DocumentProcessor, Retriever, VectorStore
from config import config

load_dotenv()

print("="*70)
print("AGENT TEST: CITATION INTELLIGENCE WITH PERPLEXITY")
print("="*70)

# Initialize system (quietly)
doc_processor = DocumentProcessor(chunk_size=config.rag.chunk_size, chunk_overlap=config.rag.chunk_overlap)
vector_store = VectorStore(db_path=config.vector_store.db_path, collection_name=config.vector_store.collection_name, embedding_model_name=config.embedding.model_name)
retriever = Retriever(vector_store, doc_processor)

# Initialize agent
tool_registry = ToolRegistry(retriever)
agent = ResearchAgent(
    tool_registry=tool_registry,
    api_key=config.model.api_key,
    model_name=config.model.name,
    max_iterations=10,
    verbose=True  # Show agent reasoning
)

paper_id = "Mechanisms vs Outcomes- Probing for Syntax Fails to Explain Performance on Targeted Syntactic Evaluation"

# Test explaining a specific citation with Perplexity resolution
print("\n" + "="*70)
print("TESTING: Explain Citation with Web Search (Perplexity)")
print("="*70)
print(f"\nPaper: {paper_id}")
print(f"Citation: (Devlin et al., 2019)")
print(f"\nThis will:")
print(f"  1. Extract citation context from the paper")
print(f"  2. Use Perplexity to search for 'Devlin et al. 2019'")
print(f"  3. Scrape the paper from web")
print(f"  4. Explain why it's cited")
print("\n" + "-"*70)

query = f"Explain citation '(Devlin et al., 2019)' in paper '{paper_id}' - use web search to find the cited paper"

response = agent.query(query)

print("\n" + "="*70)
print("AGENT RESPONSE")
print("="*70)
print(response.answer)

if response.steps:
    print("\n" + "="*70)
    print(f"REASONING STEPS ({len(response.steps)} steps)")
    print("="*70)
    for step in response.steps:
        print(f"\nStep {step.step_num}: {step.tool_name}")
        print(f"  Input: {step.tool_input}")
        print(f"  Output (first 200 chars): {step.tool_output[:200]}...")

print("\n" + "="*70)
print("TEST COMPLETE!")
print("="*70)
