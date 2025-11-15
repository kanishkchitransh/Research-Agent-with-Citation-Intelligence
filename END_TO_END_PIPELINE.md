# End-to-End Pipeline Design for Web/App

## Current State vs. Desired State

### ❌ Current State (Hardcoded)
```python
# Test code - hardcoded citation
citation = "Tucker et al. (2021)"  # ← Hardcoded!
response = agent.query(f"Explain citation '{citation}'")
```

### ✅ Desired State (Interactive)
```
User → Upload PDF → See all citations → Pick one → Agent explains it
```

---

## Proper User Flow for Website/App

### **Step 1: User Uploads PDF**
```
User action: Upload research paper PDF
Backend: Store PDF, extract text
```

### **Step 2: System Shows All Citations**
```
Backend: Call extract_citations tool
Frontend: Display clickable list of citations
```

Example UI:
```
📄 Paper: "Mechanisms vs Outcomes..."

Found 17 citations:
┌────────────────────────────────────┐
│ 1. (Almazrouei et al., 2023)      │ [Explain] ← Click
│ 2. (Belinkov, 2022)               │ [Explain]
│ 3. (Devlin et al., 2019)          │ [Explain]
│ 4. (Clark et al., 2020)           │ [Explain]
│ ...                               │
└────────────────────────────────────┘
```

### **Step 3: User Clicks "Explain" on a Citation**
```
User action: Click "Explain" button
Frontend: Send citation_marker + paper_id to backend
Backend: Call explain_citation tool
```

### **Step 4: Agent Resolves & Explains**
```
Backend workflow:
1. Extract context around citation from paper
2. Search web (Perplexity) for cited paper
3. Scrape cited paper details
4. Generate AI explanation
5. Return to frontend
```

### **Step 5: Show Explanation to User**
```
Frontend displays:
┌─────────────────────────────────────────────┐
│ Citation: (Devlin et al., 2019)            │
│                                             │
│ Cited Paper:                                │
│ "BERT: Pre-training of Deep Bidirectional  │
│  Transformers for Language Understanding"   │
│                                             │
│ Authors: Jacob Devlin, Ming-Wei Chang, ...  │
│ Year: 2018 | ArXiv: 1810.04805            │
│                                             │
│ Why cited:                                  │
│ The citing paper uses BERT as a baseline   │
│ model to compare against their novel       │
│ approach for syntactic evaluation...        │
│                                             │
│ [Read Full Paper] [See Abstract]          │
└─────────────────────────────────────────────┘
```

---

## Implementation for Web/App

### Backend API Endpoints Needed

#### 1. **Upload Paper**
```python
POST /api/papers/upload
Body: { file: PDF }
Response: { paper_id: "unique_id", title: "..." }
```

#### 2. **Extract Citations**
```python
GET /api/papers/{paper_id}/citations
Response: {
  "citations": [
    {"marker": "(Devlin et al., 2019)", "type": "author-year"},
    {"marker": "(Clark et al., 2020)", "type": "author-year"},
    ...
  ],
  "total": 17
}
```

#### 3. **Explain Citation**
```python
POST /api/papers/{paper_id}/explain-citation
Body: { citation_marker: "(Devlin et al., 2019)" }
Response: {
  "cited_paper": {
    "title": "BERT: Pre-training...",
    "authors": ["Jacob Devlin", ...],
    "year": "2018",
    "arxiv_id": "1810.04805",
    "pdf_url": "https://arxiv.org/pdf/1810.04805",
    "abstract": "We introduce a new..."
  },
  "explanation": {
    "why_cited": "The citing paper uses BERT...",
    "relationship": "provides-background",
    "relevance_score": 0.85
  }
}
```

---

## Code Structure for Web App

### **Backend (FastAPI/Flask)**
```
backend/
├── api/
│   ├── routes.py           # API endpoints
│   ├── paper_service.py    # Paper upload & processing
│   └── citation_service.py # Citation extraction & explanation
├── agent/                  # Your existing agent code
├── rag/                    # Your existing RAG code
└── main.py                 # App entry point
```

### **Frontend (React/Gradio)**
```
frontend/
├── components/
│   ├── PaperUpload.jsx    # PDF upload component
│   ├── CitationList.jsx   # Display citations
│   └── CitationExplainer.jsx # Show explanation
└── App.jsx                 # Main app
```

---

## Sample Backend Code (FastAPI)

```python
from fastapi import FastAPI, UploadFile, File
from agent import ResearchAgent, ToolRegistry
from rag import DocumentProcessor, Retriever, VectorStore
from pathlib import Path

app = FastAPI()

# Initialize system once at startup
doc_processor = DocumentProcessor()
vector_store = VectorStore(db_path="./data/vector_db")
retriever = Retriever(vector_store, doc_processor)
tool_registry = ToolRegistry(retriever)
agent = ResearchAgent(tool_registry, api_key=config.model.api_key)

@app.post("/api/papers/upload")
async def upload_paper(file: UploadFile = File(...)):
    """Upload and process a PDF paper."""
    # Save PDF
    pdf_path = Path(f"./data/papers/{file.filename}")
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    # Ingest into RAG system
    paper_id = retriever.ingest_paper(pdf_path)

    return {
        "paper_id": paper_id,
        "filename": file.filename,
        "status": "processed"
    }

@app.get("/api/papers/{paper_id}/citations")
async def get_citations(paper_id: str):
    """Get all citations from a paper."""
    # Use agent to extract citations
    response = agent.query(f"Extract all citations from paper '{paper_id}'")

    # Parse response into structured format
    # (You'd make this more robust in production)
    return {
        "paper_id": paper_id,
        "citations": parse_citations(response.answer),
        "raw_response": response.answer
    }

@app.post("/api/papers/{paper_id}/explain-citation")
async def explain_citation(paper_id: str, citation: dict):
    """Explain a specific citation."""
    citation_marker = citation.get("marker")

    # Use agent to explain citation (with Perplexity search!)
    response = agent.query(
        f"Explain citation '{citation_marker}' in paper '{paper_id}'"
    )

    return {
        "citation_marker": citation_marker,
        "explanation": response.answer,
        "steps_used": len(response.steps)
    }

def parse_citations(agent_response: str):
    """Parse agent response into structured citations."""
    # Implementation depends on response format
    # Could use regex or ask agent to return JSON
    pass
```

---

## Sample Frontend Code (React)

```javascript
import React, { useState } from 'react';

function CitationExplorer() {
  const [paperId, setPaperId] = useState(null);
  const [citations, setCitations] = useState([]);
  const [explanation, setExplanation] = useState(null);

  // Step 1: Upload PDF
  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/papers/upload', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();
    setPaperId(data.paper_id);

    // Automatically fetch citations after upload
    fetchCitations(data.paper_id);
  };

  // Step 2: Fetch citations
  const fetchCitations = async (id) => {
    const response = await fetch(`/api/papers/${id}/citations`);
    const data = await response.json();
    setCitations(data.citations);
  };

  // Step 3: Explain citation
  const explainCitation = async (marker) => {
    setExplanation({ loading: true });

    const response = await fetch(`/api/papers/${paperId}/explain-citation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ marker })
    });

    const data = await response.json();
    setExplanation(data);
  };

  return (
    <div className="citation-explorer">
      {/* Upload Section */}
      <input type="file" onChange={(e) => handleUpload(e.target.files[0])} />

      {/* Citations List */}
      {citations.length > 0 && (
        <div className="citations-list">
          <h2>Found {citations.length} citations</h2>
          {citations.map((citation, idx) => (
            <div key={idx} className="citation-item">
              <span>{citation.marker}</span>
              <button onClick={() => explainCitation(citation.marker)}>
                Explain
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Explanation Panel */}
      {explanation && (
        <div className="explanation-panel">
          {explanation.loading ? (
            <p>Searching for cited paper...</p>
          ) : (
            <div>
              <h3>{explanation.citation_marker}</h3>
              <p>{explanation.explanation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CitationExplorer;
```

---

## Gradio Alternative (Simpler!)

If you want to avoid building a full React app, use Gradio:

```python
import gradio as gr

def process_paper_and_explain(pdf_file, citation_marker):
    """End-to-end: Upload → Extract → Explain"""

    # Upload paper
    pdf_path = Path(pdf_file.name)
    paper_id = retriever.ingest_paper(pdf_path)

    # Extract citations
    citations_response = agent.query(f"Extract all citations from '{paper_id}'")

    # If user provided citation, explain it
    if citation_marker:
        explanation_response = agent.query(
            f"Explain citation '{citation_marker}' in paper '{paper_id}'"
        )
        return citations_response.answer, explanation_response.answer
    else:
        return citations_response.answer, "Select a citation to explain"

# Gradio Interface
demo = gr.Interface(
    fn=process_paper_and_explain,
    inputs=[
        gr.File(label="Upload Research Paper (PDF)"),
        gr.Textbox(label="Citation to Explain (e.g., 'Devlin et al., 2019')",
                   placeholder="Leave empty to see all citations first")
    ],
    outputs=[
        gr.Textbox(label="All Citations Found"),
        gr.Textbox(label="Citation Explanation")
    ],
    title="Research Agent - Citation Intelligence",
    description="Upload a paper, see citations, pick one, and get AI-powered explanation!"
)

demo.launch()
```

---

## What's Missing in Current Code

### ❌ Not Implemented:
1. **Interactive citation selection** - User can't pick from a list
2. **Web API endpoints** - No REST API
3. **Frontend UI** - No user interface
4. **Session management** - Can't handle multiple users

### ✅ Already Implemented:
1. Citation extraction (`extract_citations` tool)
2. Citation explanation (`explain_citation` tool)
3. Perplexity search integration
4. Web scraping
5. Agent reasoning

---

## Next Steps to Build Web/App

### Option A: Quick Gradio App (1-2 hours)
1. Create `ui/gradio_app.py`
2. Implement the Gradio interface above
3. Run with `python ui/gradio_app.py`
4. Deploy to Hugging Face Spaces (free!)

### Option B: Full React + FastAPI (1-2 days)
1. Create FastAPI backend with endpoints above
2. Build React frontend with upload + citation list
3. Connect frontend to backend
4. Deploy (Vercel frontend + Render/Railway backend)

### Option C: Streamlit App (2-3 hours)
1. Create `ui/streamlit_app.py`
2. Similar to Gradio but with Streamlit
3. Better for dashboards and analytics

---

## Recommendation

**Start with Gradio (Option A)** because:
- ✅ Fastest to build (1-2 hours)
- ✅ Good enough for demo/portfolio
- ✅ Free deployment to Hugging Face Spaces
- ✅ Can upgrade to React later if needed

**Then upgrade to FastAPI + React** when:
- You need more customization
- You want to add user accounts
- You want better performance
- You're ready to monetize

---

## Summary

Your concern is **100% valid**:
- ❌ Current code: Hardcoded citations in tests
- ✅ Needed: Interactive flow where user picks citations

**Solution**: Build a web UI (Gradio/Streamlit/React) that:
1. Lets user upload PDF
2. Shows all citations
3. Lets user click to explain any citation
4. Uses your existing agent tools under the hood

Want me to implement the Gradio app right now? It'll take ~30 minutes to build a working prototype!
