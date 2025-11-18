"""
Research Agent with Citation Intelligence - Gradio Web Interface

This app demonstrates the unique citation intelligence feature:
- Upload research papers (PDF)
- Automatically extract citations
- Find cited papers on the web (ArXiv, IEEE, ACM, etc.)
- AI-powered explanation of why papers cite each other
- Author Intelligence: Get comprehensive profiles of paper authors
- Field Intelligence: Understand research field context

Built by an NLP researcher, for researchers.
"""

import gradio as gr
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import ResearchAgent, ToolRegistry
from rag import DocumentProcessor, Retriever, VectorStore
from config import config

# Global variables
agent = None
retriever = None
current_paper_id = None
current_citations = []
session_states = {}  # Store session preferences


def initialize_system():
    """Initialize the Research Agent system."""
    global agent, retriever

    if agent is not None:
        return "System already initialized!"

    try:
        print("🔧 Initializing Research Agent...")

        # Initialize RAG components
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

        # Initialize agent with author intelligence support
        perplexity_key = os.getenv("PERPLEXITY_API_KEY", config.perplexity.api_key if hasattr(config, 'perplexity') else None)

        tool_registry = ToolRegistry(
            retriever=retriever,
            api_key=config.model.api_key,
            perplexity_api_key=perplexity_key
        )

        agent = ResearchAgent(
            tool_registry=tool_registry,
            api_key=config.model.api_key,
            model_name=config.model.name,
            max_iterations=config.agent.max_iterations,
            verbose=False
        )

        print("✅ Research Agent initialized successfully!")

        # Check which features are available
        features = []
        if config.model.api_key:
            features.append("Citation Intelligence ✓")
        if perplexity_key:
            features.append("Author Intelligence ✓")

        return f"System initialized successfully! Available features: {', '.join(features)}"

    except Exception as e:
        error_msg = f"Error initializing system: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def get_session_id(session_state: Optional[Dict]) -> str:
    """Get or create session ID."""
    if session_state is None or "session_id" not in session_state:
        return str(uuid.uuid4())
    return session_state["session_id"]


def get_author_intelligence_for_paper(paper_id: str, session_id: str, detail_level: str = "standard") -> str:
    """Get author intelligence for the current paper."""
    global agent

    if agent is None:
        return "❌ Please initialize the system first by uploading a paper."

    if not paper_id:
        return "❌ Please upload a paper first!"

    try:
        print(f"👤 Fetching author intelligence for paper: {paper_id}")

        # First, check if we should offer author intelligence
        should_offer_query = f"Should I offer author intelligence for paper '{paper_id}' in session '{session_id}'?"
        should_offer_response = agent.query(should_offer_query)

        if "should_offer" in should_offer_response.answer.lower() and "false" in should_offer_response.answer.lower():
            return "ℹ️ Author intelligence was declined for this session. Click 'Reset Preferences' to enable again."

        # Fetch paper authors
        authors_query = f"Get all authors for paper '{paper_id}' with primary author focus"
        authors_response = agent.query(authors_query)

        if not authors_response.success:
            return f"❌ Could not fetch authors: {authors_response.error}"

        # Extract author names from response (simplified parsing)
        import re
        author_lines = [line for line in authors_response.answer.split('\n') if line.strip() and not line.startswith('#')]

        if not author_lines:
            return "ℹ️ No authors found for this paper."

        # Get detailed intelligence for first author (primary)
        first_author = author_lines[0].strip().replace('**', '').replace('-', '').strip()
        if ':' in first_author:
            first_author = first_author.split(':')[0].strip()

        intelligence_query = f"Get author intelligence for '{first_author}' from paper '{paper_id}' with detail level '{detail_level}'"
        intelligence_response = agent.query(intelligence_query)

        if intelligence_response.success:
            return intelligence_response.answer
        else:
            return f"❌ Could not generate author intelligence: {intelligence_response.error}"

    except Exception as e:
        error_msg = f"❌ Error fetching author intelligence: {str(e)}"
        print(error_msg)
        return error_msg


def get_field_intelligence_for_paper(paper_id: str) -> str:
    """Get field intelligence for the current paper."""
    global agent

    if agent is None:
        return "❌ Please initialize the system first by uploading a paper."

    if not paper_id:
        return "❌ Please upload a paper first!"

    try:
        print(f"🔬 Fetching field intelligence for paper: {paper_id}")

        # Use agent to get field context (combines keyword extraction + field intelligence)
        field_query = f"Get comprehensive field context for paper '{paper_id}'"
        field_response = agent.query(field_query)

        if field_response.success:
            return field_response.answer
        else:
            return f"❌ Could not generate field intelligence: {field_response.error}"

    except Exception as e:
        error_msg = f"❌ Error fetching field intelligence: {str(e)}"
        print(error_msg)
        return error_msg


def reset_session_preferences(session_id: str) -> str:
    """Reset session preferences."""
    global session_states

    if session_id in session_states:
        session_states[session_id] = {"session_id": session_id}
        return "✅ Session preferences reset! Author intelligence will be offered again."
    else:
        return "ℹ️ No preferences to reset."


def upload_and_process_paper(pdf_file, session_state):
    """Upload and process a research paper."""
    global current_paper_id, current_citations, retriever, agent

    # Initialize session
    if session_state is None:
        session_state = {"session_id": str(uuid.uuid4())}

    if agent is None:
        init_msg = initialize_system()
        if "Error" in init_msg:
            return init_msg, "System initialization failed", [], session_state, gr.update()

    if pdf_file is None:
        return "❌ Please upload a PDF file", "", [], session_state, gr.update()

    try:
        # Save the uploaded file
        pdf_path = Path(pdf_file.name)
        print(f"📄 Processing: {pdf_path.name}")

        # Ingest paper into RAG system
        paper_id = retriever.ingest_paper(pdf_path)
        current_paper_id = paper_id

        # Store paper ID in session
        session_state["current_paper_id"] = paper_id

        # Get paper details
        paper = retriever._get_paper(paper_id)

        # Extract citations using agent
        print("🔍 Extracting citations...")
        citations_response = agent.query(f"Extract all citations from paper '{paper_id}'")

        # Parse citations from response (simplified)
        # We'll extract citations from the agent's response text
        response_text = citations_response.answer

        # Try to extract citation markers from the response
        import re
        citation_patterns = [
            r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?(?:,\s*\d{4})?)\)',  # (Author, Year)
            r'\[(\d+)\]',  # [1]
            r'\[([A-Z][a-z]+(?:\s+et\s+al\.)?)\]'  # [Author et al.]
        ]

        citations_found = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, response_text)
            citations_found.extend([f"({m})" if not m.startswith('[') else m for m in matches])

        # Remove duplicates and sort
        citations_found = sorted(list(set(citations_found)))[:20]  # Limit to 20 for UI
        current_citations = citations_found

        # Format paper info
        paper_info = f"## ✅ Paper Processed Successfully!\n\n"
        paper_info += f"**Title:** {paper.title}\n\n"
        paper_info += f"**Paper ID:** {paper_id}\n\n"

        if paper.authors:
            paper_info += f"**Authors:** {', '.join(paper.authors[:3])}"
            if len(paper.authors) > 3:
                paper_info += f" et al. ({len(paper.authors)} total)\n\n"
            else:
                paper_info += "\n\n"

        if paper.abstract:
            paper_info += f"**Abstract:** {paper.abstract[:300]}...\n\n"

        paper_info += f"**Citations Found:** {len(citations_found)}\n\n"
        paper_info += "👇 Select a citation below to explain it!"

        print(f"✅ Processed successfully! Found {len(citations_found)} citations")

        # Return updated components including PDF viewer
        return (
            paper_info,
            citations_response.answer,
            gr.update(choices=citations_found, value=citations_found[0] if citations_found else None),
            session_state,
            gr.update(value=pdf_file.name)
        )

    except Exception as e:
        error_msg = f"❌ Error processing paper: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return error_msg, "", [], session_state, gr.update()


def explain_selected_citation(citation_marker):
    """Explain a selected citation using the agent."""
    global current_paper_id, agent

    if agent is None:
        return "❌ Please initialize the system first by uploading a paper."

    if not current_paper_id:
        return "❌ Please upload a paper first!"

    if not citation_marker:
        return "❌ Please select a citation to explain!"

    try:
        print(f"🔍 Explaining citation: {citation_marker}")

        # Use agent to explain citation (this will use Perplexity search!)
        query = f"Explain citation '{citation_marker}' in paper '{current_paper_id}'"

        response = agent.query(query)

        if response.success:
            # Format the explanation nicely
            explanation = f"## 🎯 Citation Explanation\n\n"
            explanation += f"**Citation:** {citation_marker}\n\n"
            explanation += f"---\n\n"
            explanation += response.answer
            explanation += f"\n\n---\n\n"
            explanation += f"*Used {len(response.steps)} reasoning steps to find and explain this citation.*"

            print(f"✅ Explanation generated successfully!")
            return explanation
        else:
            return f"❌ Failed to explain citation: {response.error}"

    except Exception as e:
        error_msg = f"❌ Error explaining citation: {str(e)}"
        print(error_msg)
        return error_msg


def ask_question(question):
    """Ask a general question about the papers."""
    global agent, current_paper_id

    if agent is None:
        return "❌ Please initialize the system first by uploading a paper."

    if not question or not question.strip():
        return "❌ Please enter a question!"

    try:
        print(f"💬 Question: {question}")

        response = agent.query(question)

        if response.success:
            answer = f"## 🤖 Agent Response\n\n"
            answer += response.answer
            answer += f"\n\n---\n\n"
            answer += f"*Used {len(response.steps)} reasoning steps*"

            print(f"✅ Answer generated!")
            return answer
        else:
            return f"❌ Error: {response.error}"

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)
        return error_msg


# Create Gradio Interface
with gr.Blocks(
    title="Research Agent - Citation Intelligence",
    theme=gr.themes.Soft(),
    css="""
    .citation-card {
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .author-card {
        border: 2px solid #4A90E2;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .field-card {
        border: 2px solid #50C878;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        background: linear-gradient(135deg, #f5fef8 0%, #d4f4dd 100%);
    }
    .pdf-viewer {
        border: 2px solid #ddd;
        border-radius: 10px;
        padding: 10px;
        max-height: 600px;
        overflow-y: auto;
    }
    """
) as demo:

    # Session state
    session_state = gr.State(value={"session_id": str(uuid.uuid4())})

    # Header
    gr.Markdown("""
    # 🔬 Research Agent with Citation Intelligence

    ### Your AI Assistant for Understanding Research Papers

    **What makes this special:**
    - 📄 Upload research papers (PDF)
    - 🔍 Automatically extract citations
    - 🌐 **Find cited papers on the web** (ArXiv, IEEE, ACM, Google Scholar, etc.)
    - 💡 **AI explains WHY papers cite each other**
    - 👤 **Author Intelligence**: Get comprehensive author profiles
    - 🔬 **Field Intelligence**: Analyze research domains, trends, and breakthroughs

    ---

    **🎯 Unique Features:**
    - Automatically searches the web to find cited papers
    - Fetches author profiles from multiple sources (Perplexity + Semantic Scholar)
    - Provides context-aware explanations
    - Permanent caching for faster responses
    """)

    # Main content
    with gr.Tabs():

        # Tab 1: Citation Intelligence
        with gr.Tab("🔍 Citation Intelligence"):
            gr.Markdown("## Upload & Explore Citations")

            with gr.Row():
                with gr.Column(scale=1):
                    pdf_upload = gr.File(
                        label="📤 Upload Research Paper (PDF)",
                        file_types=[".pdf"],
                        type="filepath"
                    )
                    upload_btn = gr.Button(
                        "🚀 Process Paper",
                        variant="primary",
                        size="lg"
                    )

                with gr.Column(scale=1):
                    paper_info = gr.Markdown(
                        "### 📋 Paper Info\n\nUpload a paper to get started!"
                    )

            gr.Markdown("---")

            # NEW: PDF Viewer (collapsed by default)
            with gr.Accordion("📄 View PDF", open=False):
                pdf_viewer = gr.File(
                    label="Uploaded PDF",
                    interactive=False,
                    elem_classes="pdf-viewer"
                )
                gr.Markdown("*Your uploaded PDF will be displayed here for reference*")

            gr.Markdown("---")

            # NEW: Author Intelligence Panel (collapsed by default)
            with gr.Accordion("👤 Author Intelligence", open=False, elem_classes="author-card"):
                gr.Markdown("""
                **Get comprehensive author profiles:**
                - Career overview and expertise
                - Publication metrics (h-index, citations)
                - Research trajectory analysis
                - Contextual insights powered by AI
                """)

                with gr.Row():
                    author_detail_level = gr.Radio(
                        choices=["quick", "standard", "deep"],
                        value="standard",
                        label="Detail Level",
                        info="Quick: Brief overview | Standard: With trajectory | Deep: Comprehensive analysis"
                    )
                    fetch_author_btn = gr.Button(
                        "🔍 Fetch Author Intelligence",
                        variant="primary"
                    )

                author_intelligence_output = gr.Markdown(
                    "*Click 'Fetch Author Intelligence' to get comprehensive profiles of paper authors*"
                )

                with gr.Row():
                    reset_preferences_btn = gr.Button(
                        "🔄 Reset Preferences",
                        size="sm"
                    )

            gr.Markdown("---")

            # NEW: Field Intelligence Panel (collapsed by default)
            with gr.Accordion("🔬 Field Intelligence", open=False, elem_classes="field-card"):
                gr.Markdown("""
                **Understand the research field context:**
                - Current state of the art
                - Recent breakthroughs and trends (last 2-3 years)
                - Key research directions and challenges
                - Hot topics and emerging areas
                - Field evolution and timeline

                *Automatically extracts keywords and analyzes the research domain*
                """)

                fetch_field_btn = gr.Button(
                    "🔍 Fetch Field Intelligence",
                    variant="primary"
                )

                field_intelligence_output = gr.Markdown(
                    "*Click 'Fetch Field Intelligence' to get comprehensive analysis of the research field*"
                )

            gr.Markdown("---")

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📚 All Citations Found")
                    citations_list = gr.Textbox(
                        label="Citations",
                        lines=10,
                        placeholder="Citations will appear here after processing..."
                    )

                with gr.Column():
                    gr.Markdown("### 🎯 Select Citation to Explain")
                    citation_dropdown = gr.Dropdown(
                        label="Citation",
                        choices=[],
                        interactive=True,
                        info="Select a citation from the dropdown"
                    )
                    explain_btn = gr.Button(
                        "💡 Explain This Citation",
                        variant="primary",
                        size="lg"
                    )

            gr.Markdown("---")

            gr.Markdown("### 📖 Citation Explanation")
            explanation_output = gr.Markdown(
                "*Select a citation above and click 'Explain' to see details about the cited paper*"
            )

        # Tab 2: Q&A
        with gr.Tab("💬 Ask Questions"):
            gr.Markdown("""
            ## Ask Questions About Your Papers

            You can ask questions like:
            - "What are the main contributions of this paper?"
            - "What methodology is used?"
            - "Compare this with the BERT paper"
            - "What datasets are used?"
            """)

            question_input = gr.Textbox(
                label="Your Question",
                placeholder="e.g., What is the main contribution of this paper?",
                lines=3
            )
            ask_btn = gr.Button("🔍 Ask", variant="primary", size="lg")

            answer_output = gr.Markdown("*Your answer will appear here*")

        # Tab 3: About
        with gr.Tab("ℹ️ About"):
            gr.Markdown("""
            ## About This Project

            ### 🎯 The Problem
            When reading research papers, understanding citations is crucial but time-consuming:
            - What is this cited paper about?
            - Why was it cited?
            - How does it relate to the current paper?

            Currently, you have to:
            1. Google the citation
            2. Find the paper on ArXiv/IEEE/ACM
            3. Read the abstract
            4. Figure out the connection yourself

            **This takes 5-10 minutes per citation!**

            ### ✅ The Solution
            This Research Agent automates the entire process:
            1. **Extracts** all citations from your paper
            2. **Searches** the web for cited papers (Perplexity AI)
            3. **Finds** the paper on ArXiv, IEEE, ACM, Google Scholar, etc.
            4. **Scrapes** the paper details (title, authors, abstract)
            5. **Explains** why it was cited using AI

            **Result: 30 seconds instead of 5-10 minutes!**

            ### 🔧 Technology Stack
            - **LLM**: Gemini 2.0 Flash (reasoning & explanation)
            - **Search**: Perplexity AI (web search for papers)
            - **RAG**: ChromaDB + sentence-transformers
            - **Agent**: ReAct pattern with function calling
            - **Scraping**: Custom scrapers for ArXiv, IEEE, ACM

            ### 🌟 What Makes This Unique
            Unlike ChatPDF or other document Q&A tools, this agent:
            - ✅ Finds cited papers on the web (not just your uploads)
            - ✅ Searches multiple sources (ArXiv, IEEE, ACM, Scholar)
            - ✅ Explains citation relationships with AI
            - ✅ Built specifically for academic research

            ### 👨‍💻 Built By
            An NLP researcher who understands the pain of literature reviews!

            **GitHub**: [Research-Agent-with-Citation-Intelligence](https://github.com/yourusername/Research-Agent-with-Citation-Intelligence)

            ---

            **💡 Tip**: Try uploading a paper from your field and explore its citations!
            """)

    # Event handlers
    upload_btn.click(
        fn=upload_and_process_paper,
        inputs=[pdf_upload, session_state],
        outputs=[paper_info, citations_list, citation_dropdown, session_state, pdf_viewer]
    )

    explain_btn.click(
        fn=explain_selected_citation,
        inputs=[citation_dropdown],
        outputs=[explanation_output]
    )

    ask_btn.click(
        fn=ask_question,
        inputs=[question_input],
        outputs=[answer_output]
    )

    # NEW: Author Intelligence event handlers
    fetch_author_btn.click(
        fn=lambda detail, state: get_author_intelligence_for_paper(
            state.get("current_paper_id", ""),
            state.get("session_id", ""),
            detail
        ),
        inputs=[author_detail_level, session_state],
        outputs=[author_intelligence_output]
    )

    reset_preferences_btn.click(
        fn=lambda state: reset_session_preferences(state.get("session_id", "")),
        inputs=[session_state],
        outputs=[author_intelligence_output]
    )

    # NEW: Field Intelligence event handler
    fetch_field_btn.click(
        fn=lambda state: get_field_intelligence_for_paper(state.get("current_paper_id", "")),
        inputs=[session_state],
        outputs=[field_intelligence_output]
    )

    # Footer
    gr.Markdown("""
    ---
    <div style="text-align: center; color: #666;">
        <p>🔬 Research Agent with Citation + Author + Field Intelligence | Built with ❤️ for Researchers</p>
        <p>Powered by Gemini 2.0 Flash + Perplexity AI + Semantic Scholar + ChromaDB</p>
        <p><small>Session ID: Unique per browser session | Field intelligence cached for 30 days</small></p>
    </div>
    """)


# Launch
if __name__ == "__main__":
    print("="*70)
    print("🚀 Starting Research Agent Web Interface")
    print("="*70)
    print("\n⚙️  Initializing system on startup...")

    # Initialize on startup
    try:
        initialize_system()
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize on startup: {e}")
        print("   System will initialize on first paper upload.")

    print("\n✅ Server starting...")
    print("🌐 Access the app at: http://localhost:7860")
    print("\n💡 Tip: Upload a research paper to get started!")
    print("="*70 + "\n")

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # Set to True for temporary public link
    )
