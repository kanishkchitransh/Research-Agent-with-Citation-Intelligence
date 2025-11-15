"""
Entry point for Hugging Face Spaces deployment.
This file is required for HF Spaces to recognize the app.
"""

import os
import sys
from pathlib import Path

# Hugging Face Spaces environment setup
if os.getenv("SPACE_ID"):  # Running on HF Spaces
    print("🚀 Running on Hugging Face Spaces!")

    # Set API keys from HF Secrets (if configured)
    if "GOOGLE_API_KEY" not in os.environ and os.getenv("HF_GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.getenv("HF_GOOGLE_API_KEY")

    if "PERPLEXITY_API_KEY" not in os.environ and os.getenv("HF_PERPLEXITY_API_KEY"):
        os.environ["PERPLEXITY_API_KEY"] = os.getenv("HF_PERPLEXITY_API_KEY")

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and launch the Gradio app
from ui.gradio_app import demo

if __name__ == "__main__":
    demo.launch()
