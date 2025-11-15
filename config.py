"""Configuration management for the Research Agent."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class ModelConfig(BaseModel):
    """LLM model configuration."""

    name: str = Field(default="gemini-2.5-flash-lite")
    api_key: str = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    perplexity_api_key: str = Field(default_factory=lambda: os.getenv("PERPLEXITY_API_KEY", ""))
    max_tokens: int = Field(default=8192)
    temperature: float = Field(default=0.7)
    top_p: float = Field(default=0.95)


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    model_name: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    device: str = Field(default="cpu")


class RAGConfig(BaseModel):
    """RAG system configuration."""

    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    top_k_results: int = Field(default=5)
    similarity_threshold: float = Field(default=0.7)


class VectorStoreConfig(BaseModel):
    """Vector database configuration."""

    db_path: Path = Field(default_factory=lambda: Path("./data/vector_db"))
    collection_name: str = Field(default="research_papers")


class AgentConfig(BaseModel):
    """Agent configuration."""

    max_iterations: int = Field(default=10)
    verbose: bool = Field(default=True)
    enable_citation_intelligence: bool = Field(default=True)


class PathConfig(BaseModel):
    """Path configuration."""

    papers_dir: Path = Field(default_factory=lambda: Path("./data/papers"))
    vector_db_dir: Path = Field(default_factory=lambda: Path("./data/vector_db"))
    logs_dir: Path = Field(default_factory=lambda: Path("./logs"))

    def ensure_paths_exist(self):
        """Create directories if they don't exist."""
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


class Config(BaseModel):
    """Main configuration object."""

    model: ModelConfig = Field(default_factory=ModelConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    paths: PathConfig = Field(default_factory=PathConfig)

    def __init__(self, **data):
        super().__init__(**data)
        self.paths.ensure_paths_exist()


# Global config instance
config = Config()
