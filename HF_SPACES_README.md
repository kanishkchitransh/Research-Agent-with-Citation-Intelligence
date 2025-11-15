---
title: Research Agent Citation Intelligence
emoji: 🔬
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.16.0
app_file: app.py
pinned: false
license: mit
---

# Research Agent with Citation Intelligence

An AI-powered research assistant that helps researchers understand research papers through intelligent citation analysis.

## 🎯 What This Does

Upload a research paper (PDF) and this agent will:
1. **Extract all citations** from the paper
2. **Find cited papers on the web** (ArXiv, IEEE, ACM, Google Scholar, etc.)
3. **Explain why papers cite each other** using AI
4. **Save you hours** of manual research!

## ✨ Key Features

- 🔍 **Citation Intelligence**: Automatically finds and explains cited papers
- 🌐 **Multi-Source Search**: Searches ArXiv, IEEE, ACM, and more via Perplexity AI
- 💡 **AI-Powered Explanations**: Understands WHY papers cite each other
- 📚 **Cross-Document Reasoning**: Ask questions across multiple papers

## 🚀 How to Use

1. Upload your research paper (PDF)
2. Wait for citations to be extracted
3. Select any citation you want to understand
4. Click "Explain" and get instant insights!

## 🔧 Technology

- **LLM**: Gemini 2.0 Flash (reasoning & function calling)
- **Search**: Perplexity AI (finds papers on web)
- **RAG**: ChromaDB + sentence-transformers
- **Agent**: ReAct pattern with multi-step reasoning

## 🎓 Built For Researchers

Created by an NLP researcher who understands the pain of literature reviews.
Unlike ChatPDF and similar tools, this agent actively finds and explains citations!

## ⚙️ Setup (for deployment)

### Required Secrets (in HF Spaces Settings):

1. `HF_GOOGLE_API_KEY`: Your Google AI API key (for Gemini)
   - Get one at: https://makersuite.google.com/app/apikey

2. `HF_PERPLEXITY_API_KEY`: Your Perplexity API key (optional but recommended)
   - Get one at: https://www.perplexity.ai/api-platform

Without these keys, the app will work in limited mode (ArXiv-only citations).

## 📝 License

MIT License - Free for academic and commercial use

## 🔗 Links

- GitHub: https://github.com/yourusername/Research-Agent-with-Citation-Intelligence
- Demo Video: [Coming soon]

---

**Tip**: Try uploading a paper from your field and explore how it connects to other research!
