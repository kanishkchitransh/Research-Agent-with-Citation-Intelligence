"""Quick launcher for the Gradio app."""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Run the app
if __name__ == "__main__":
    from ui.gradio_app import demo
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # Set True for public link
    )
