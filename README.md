# Research Agent with Citation Intelligence

An AI-powered research assistant that helps researchers understand research papers through multi-step reasoning, cross-document search, and intelligent citation analysis.

## Key Features

- **Cross-Document Reasoning**: Ask questions across multiple papers and get synthesized answers
- **Citation Intelligence**: Automatically find and explain citations - understands why papers cite each other
- **Multi-Step Reasoning**: Uses ReAct pattern to break down complex queries into steps
- **Vector Search**: Semantic search across paper corpus using sentence-transformers
- **ArXiv Integration**: Automatically searches ArXiv for cited papers
- **Section Extraction**: Get specific sections (Introduction, Methods, Results, etc.) from papers

## Why This Project?

This project demonstrates practical agent engineering skills:
- **Agentic Reasoning**: ReAct pattern with tool orchestration
- **RAG Implementation**: Vector search with ChromaDB and efficient chunking
- **Production Mindset**: Structured logging, error handling, configuration management
- **Domain Knowledge**: Built for researchers by an NLP researcher

## Architecture

```
research-agent/
├── agent/                 # ReAct agent implementation
│   ├── core.py           # Main agent loop (Gemini + function calling)
│   ├── tools.py          # Tool definitions and implementations
│   └── prompts.py        # System prompts
├── rag/                   # RAG components
│   ├── document_processor.py  # PDF parsing and chunking
│   ├── vector_store.py        # ChromaDB wrapper
│   └── retriever.py           # High-level RAG interface
├── citation/              # Citation intelligence (Week 2)
│   ├── extractor.py      # Extract citations from papers
│   ├── resolver.py       # Search ArXiv for cited papers
│   └── explainer.py      # Citation context explanation
├── evaluation/            # Evaluation framework (Week 3)
├── ui/                    # User interfaces (Week 4)
└── data/                  # Papers and vector DB
```

## Tech Stack

- **LLM**: Gemini 2.0 Flash (free tier, native function calling)
- **Vector DB**: ChromaDB (persistent, no server needed)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2
- **PDF Processing**: PyMuPDF (fast, accurate)
- **Citation Search**: ArXiv API

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Research-Agent-with-Citation-Intelligence.git
cd Research-Agent-with-Citation-Intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:
```
GOOGLE_API_KEY=your_google_api_key_here
```

Get a free API key at: https://makersuite.google.com/app/apikey

### 3. Add Research Papers

Place your PDF research papers in the `data/papers/` directory.

### 4. Run the Agent

```python
from pathlib import Path
from config import config
from rag import DocumentProcessor, VectorStore, Retriever
from agent import ResearchAgent, ToolRegistry

# Initialize components
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

# Ingest papers
papers_dir = Path("./data/papers")
paper_ids = retriever.ingest_directory(papers_dir)
print(f"Ingested {len(paper_ids)} papers")

# Initialize agent
tool_registry = ToolRegistry(retriever)
agent = ResearchAgent(
    tool_registry=tool_registry,
    api_key=config.model.api_key,
    model_name=config.model.name,
    max_iterations=config.agent.max_iterations,
    verbose=config.agent.verbose
)

# Ask questions
response = agent.query("What are the main contributions of these papers?")
print(response.answer)

# Ask about citations
response = agent.query("Explain citation [12] in paper 'attention_is_all_you_need'")
print(response.answer)
```

## Usage Examples

### Search Across Papers
```python
response = agent.query("What methods do these papers use for evaluation?")
```

### Explain Citations
```python
response = agent.query("Explain citation [3] in the transformer paper")
# The agent will:
# 1. Find the context around [3] in the paper
# 2. Extract citation details
# 3. Search ArXiv for the cited paper
# 4. Explain why it's cited and how it's relevant
```

### Compare Papers
```python
response = agent.query("How do these papers differ in their approach to attention mechanisms?")
```

### Get Specific Sections
```python
response = agent.query("Summarize the Methods section of paper X")
```

## Available Tools

The agent has access to these tools:

1. **search_corpus**: Search across all papers
2. **get_paper_section**: Extract specific sections
3. **get_citation_context**: Get context around citations
4. **search_arxiv**: Search ArXiv for papers
5. **get_arxiv_paper**: Get ArXiv paper details
6. **list_papers**: List all papers in corpus
7. **search_within_paper**: Search within a specific paper
8. **get_paper_abstract**: Get paper abstract

## Development Roadmap

### Week 1: RAG Foundation + Basic Agent ✅
- [x] PDF processing and chunking
- [x] Vector store with ChromaDB
- [x] Basic retrieval
- [x] ReAct agent with 8 tools
- [x] Gemini function calling integration

### Week 2: Citation Intelligence
- [ ] Citation extraction from papers
- [ ] ArXiv resolver
- [ ] Citation explanation workflow
- [ ] Citation graph visualization

### Week 3: Advanced Features + Evaluation
- [ ] Cross-paper comparison tools
- [ ] Evaluation framework (20+ test cases)
- [ ] Logging and metrics
- [ ] Cost tracking

### Week 4: Deployment + Documentation
- [ ] Gradio web interface
- [ ] CLI tool
- [ ] Demo video
- [ ] Complete documentation

## Project Structure Details

### RAG Components

**DocumentProcessor** (`rag/document_processor.py`):
- Parses PDFs with PyMuPDF
- Extracts title, abstract, sections
- Intelligent chunking with overlap
- Citation extraction

**VectorStore** (`rag/vector_store.py`):
- ChromaDB persistent storage
- Sentence-transformers embeddings
- Metadata filtering
- Batch operations

**Retriever** (`rag/retriever.py`):
- High-level RAG interface
- Paper ingestion
- Semantic search
- Section and citation retrieval

### Agent Components

**ResearchAgent** (`agent/core.py`):
- ReAct reasoning loop
- Gemini function calling
- Multi-step execution
- Error handling

**ToolRegistry** (`agent/tools.py`):
- Tool definitions
- Tool execution
- Result formatting

## Configuration

All configuration is managed through `config.py` and `.env`:

```python
# Model settings
MODEL_NAME=gemini-2.0-flash-exp
MAX_TOKENS=8192
TEMPERATURE=0.7

# RAG settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5

# Agent settings
MAX_ITERATIONS=10
AGENT_VERBOSE=true
```

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

## Performance

- **Embedding Generation**: ~100 chunks/second (CPU)
- **Vector Search**: <100ms for 1000+ chunks
- **Agent Response**: 2-10 seconds (depends on steps)
- **Cost**: $0 (using free tier Gemini)

## Limitations

- Free tier Gemini: 15 RPM rate limit
- Vector search: CPU-only (GPU embeddings in future)
- Citation extraction: Pattern-based (not ML)
- PDF parsing: May struggle with complex layouts

## Contributing

This is a portfolio project, but suggestions are welcome! Open an issue or PR.

## License

MIT License - see LICENSE file

## Author

Built by an NLP researcher who understands the pain of literature review.

## Acknowledgments

- Gemini API for free function calling
- ChromaDB for simple vector storage
- ArXiv for open research access
- PyMuPDF for reliable PDF parsing

---

## Next Steps

1. **Try it**: Add your papers and ask questions
2. **Customize**: Modify prompts for your domain
3. **Extend**: Add new tools for your use case
4. **Evaluate**: Run the evaluation framework

For questions or feedback, open an issue on GitHub.
