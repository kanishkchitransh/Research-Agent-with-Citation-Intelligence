"""Vector store implementation using ChromaDB with sentence-transformers."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from loguru import logger
from sentence_transformers import SentenceTransformer

from .document_processor import DocumentChunk, Paper


class VectorStore:
    """
    Vector store for research papers using ChromaDB.
    Handles embedding generation and similarity search.
    """

    def __init__(
        self,
        db_path: Path,
        collection_name: str = "research_papers",
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """
        Initialize the vector store.

        Args:
            db_path: Path to store the ChromaDB database
            collection_name: Name of the collection
            embedding_model_name: Name of the sentence-transformers model
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name

        # Ensure db_path exists
        self.db_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Initialize embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model_name
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Research papers for citation intelligence"},
        )

        logger.info(
            f"VectorStore initialized: {collection_name} at {db_path} "
            f"(model: {embedding_model_name})"
        )

    def add_paper(self, paper: Paper, chunks: List[DocumentChunk]) -> None:
        """
        Add a paper and its chunks to the vector store.

        Args:
            paper: Paper object with metadata
            chunks: List of DocumentChunk objects
        """
        if not chunks:
            logger.warning(f"No chunks provided for paper {paper.paper_id}")
            return

        # Prepare data for ChromaDB
        documents = [chunk.text for chunk in chunks]
        ids = [chunk.chunk_id for chunk in chunks]
        metadatas = []

        for chunk in chunks:
            metadata = {
                "paper_id": chunk.paper_id,
                "chunk_id": chunk.chunk_id,
                "title": paper.title,
                "section": chunk.section or "unknown",
            }
            # Add any additional metadata from the chunk
            if chunk.metadata:
                metadata.update(chunk.metadata)
            metadatas.append(metadata)

        # Add to collection
        try:
            self.collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas,
            )
            logger.info(
                f"Added paper {paper.paper_id} with {len(chunks)} chunks to vector store"
            )
        except Exception as e:
            logger.error(f"Error adding paper {paper.paper_id} to vector store: {e}")
            raise

    def add_papers(self, papers_with_chunks: List[Tuple[Paper, List[DocumentChunk]]]) -> None:
        """
        Add multiple papers to the vector store.

        Args:
            papers_with_chunks: List of (Paper, List[DocumentChunk]) tuples
        """
        for paper, chunks in papers_with_chunks:
            self.add_paper(paper, chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks using semantic similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"paper_id": "paper123"})

        Returns:
            List of search results with text, metadata, and similarity scores
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_metadata,
            )

            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    result = {
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None,
                        "id": results["ids"][0][i],
                    }
                    formatted_results.append(result)

            logger.info(f"Search returned {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []

    def search_by_paper(
        self,
        query: str,
        paper_id: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search within a specific paper.

        Args:
            query: Search query
            paper_id: ID of the paper to search within
            top_k: Number of results to return

        Returns:
            List of search results
        """
        return self.search(query, top_k=top_k, filter_metadata={"paper_id": paper_id})

    def get_paper_chunks(self, paper_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific paper.

        Args:
            paper_id: ID of the paper

        Returns:
            List of all chunks for the paper
        """
        try:
            results = self.collection.get(
                where={"paper_id": paper_id},
            )

            formatted_results = []
            if results["documents"]:
                for i in range(len(results["documents"])):
                    result = {
                        "text": results["documents"][i],
                        "metadata": results["metadatas"][i],
                        "id": results["ids"][i],
                    }
                    formatted_results.append(result)

            return formatted_results

        except Exception as e:
            logger.error(f"Error getting chunks for paper {paper_id}: {e}")
            return []

    def get_all_papers(self) -> List[str]:
        """
        Get list of all paper IDs in the vector store.

        Returns:
            List of paper IDs
        """
        try:
            # Get all items and extract unique paper IDs
            all_items = self.collection.get()
            paper_ids = set()

            if all_items["metadatas"]:
                for metadata in all_items["metadatas"]:
                    if "paper_id" in metadata:
                        paper_ids.add(metadata["paper_id"])

            return sorted(list(paper_ids))

        except Exception as e:
            logger.error(f"Error getting all papers: {e}")
            return []

    def delete_paper(self, paper_id: str) -> None:
        """
        Delete all chunks of a paper from the vector store.

        Args:
            paper_id: ID of the paper to delete
        """
        try:
            self.collection.delete(
                where={"paper_id": paper_id},
            )
            logger.info(f"Deleted paper {paper_id} from vector store")
        except Exception as e:
            logger.error(f"Error deleting paper {paper_id}: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with statistics
        """
        try:
            count = self.collection.count()
            papers = self.get_all_papers()

            return {
                "total_chunks": count,
                "total_papers": len(papers),
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model_name,
                "papers": papers,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def reset(self) -> None:
        """Reset the vector store (delete all data)."""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "Research papers for citation intelligence"},
            )
            logger.warning(f"Vector store {self.collection_name} has been reset")
        except Exception as e:
            logger.error(f"Error resetting vector store: {e}")
            raise
