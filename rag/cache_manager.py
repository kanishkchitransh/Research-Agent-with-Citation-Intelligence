"""
Cache Manager for ChromaDB Metadata.

Manages caching of:
1. Author profiles (PERMANENT - authors don't change)
2. Field intelligence (30-day TTL - fields evolve)
3. Session preferences (session-scoped)

All caching uses ChromaDB's metadata field - no new databases needed.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger


class CacheManager:
    """
    Manages caching in ChromaDB metadata fields.

    Storage strategy:
    - Uses existing ChromaDB collection
    - Stores as metadata on a special "cache" document
    - Separate keys for: authors, fields, sessions
    """

    def __init__(self, vector_store):
        """
        Initialize cache manager.

        Args:
            vector_store: VectorStore instance (ChromaDB wrapper)
        """
        self.vector_store = vector_store
        self.collection = vector_store.collection

        logger.info("CacheManager initialized")

    # ==================== AUTHOR CACHING (PERMANENT) ====================

    def get_cached_author(self, normalized_name: str) -> Optional[Dict]:
        """
        Get cached author profile.

        Args:
            normalized_name: Normalized author name (e.g., "ashish_vaswani")

        Returns:
            Author profile dict or None if not found
        """
        cache_id = f"author_cache_{normalized_name}"

        try:
            result = self.collection.get(
                ids=[cache_id],
                include=["metadatas"]
            )

            if result["ids"]:
                metadata = result["metadatas"][0]
                author_data = metadata.get("author_profile")

                if author_data:
                    # Parse JSON string back to dict
                    if isinstance(author_data, str):
                        author_data = json.loads(author_data)

                    logger.info(f"✓ Cache HIT: Author '{normalized_name}'")
                    return author_data

            logger.info(f"✗ Cache MISS: Author '{normalized_name}'")
            return None

        except Exception as e:
            logger.warning(f"Error reading author cache: {e}")
            return None

    def store_author_cache(self, normalized_name: str, author_data: Dict) -> bool:
        """
        Store author profile in cache (PERMANENT).

        Args:
            normalized_name: Normalized author name
            author_data: Author profile dict (from AuthorProfile.to_dict())

        Returns:
            True if stored successfully
        """
        cache_id = f"author_cache_{normalized_name}"

        try:
            # Serialize author data to JSON
            author_json = json.dumps(author_data)

            # Store in ChromaDB metadata
            self.collection.add(
                ids=[cache_id],
                documents=[f"Author cache: {author_data.get('name', normalized_name)}"],
                metadatas=[{
                    "cache_type": "author",
                    "normalized_name": normalized_name,
                    "author_profile": author_json,
                    "cached_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "permanent": True,  # Never expires
                }]
            )

            logger.info(f"✓ Cached author '{normalized_name}' PERMANENTLY")
            return True

        except Exception as e:
            logger.error(f"Error storing author cache: {e}")
            return False

    # ==================== FIELD CACHING (30-DAY TTL) ====================

    def get_cached_field(self, domain_hash: str) -> Optional[Dict]:
        """
        Get cached field intelligence.

        Args:
            domain_hash: Hashed domain keywords (e.g., "transformers_nlp_attention")

        Returns:
            Field data dict or None if not found/stale
        """
        cache_id = f"field_cache_{domain_hash}"

        try:
            result = self.collection.get(
                ids=[cache_id],
                include=["metadatas"]
            )

            if result["ids"]:
                metadata = result["metadatas"][0]
                field_data = metadata.get("field_intelligence")
                cached_at = metadata.get("cached_at")
                ttl_days = metadata.get("ttl_days", 30)

                if field_data and cached_at:
                    # Check if cache is fresh
                    if self.is_cache_fresh(cached_at, ttl_days):
                        # Parse JSON
                        if isinstance(field_data, str):
                            field_data = json.loads(field_data)

                        logger.info(f"✓ Cache HIT: Field '{domain_hash}' (fresh)")
                        return field_data
                    else:
                        logger.info(f"✗ Cache STALE: Field '{domain_hash}' (> {ttl_days} days)")
                        return None

            logger.info(f"✗ Cache MISS: Field '{domain_hash}'")
            return None

        except Exception as e:
            logger.warning(f"Error reading field cache: {e}")
            return None

    def store_field_cache(self, domain_hash: str, field_data: Dict, ttl_days: int = 30) -> bool:
        """
        Store field intelligence in cache (30-day TTL).

        Args:
            domain_hash: Hashed domain keywords
            field_data: Field intelligence dict
            ttl_days: Time-to-live in days (default: 30)

        Returns:
            True if stored successfully
        """
        cache_id = f"field_cache_{domain_hash}"

        try:
            # Serialize field data
            field_json = json.dumps(field_data)

            # Store in ChromaDB
            self.collection.add(
                ids=[cache_id],
                documents=[f"Field cache: {domain_hash}"],
                metadatas=[{
                    "cache_type": "field",
                    "domain_hash": domain_hash,
                    "field_intelligence": field_json,
                    "cached_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "ttl_days": ttl_days,
                }]
            )

            logger.info(f"✓ Cached field '{domain_hash}' (TTL: {ttl_days} days)")
            return True

        except Exception as e:
            logger.error(f"Error storing field cache: {e}")
            return False

    def is_cache_fresh(self, cached_at: str, ttl_days: int) -> bool:
        """
        Check if cache is still fresh.

        Args:
            cached_at: Timestamp string "YYYY-MM-DD HH:MM:SS"
            ttl_days: Time-to-live in days

        Returns:
            True if cache is fresh (within TTL)
        """
        try:
            cached_time = datetime.strptime(cached_at, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            age = now - cached_time

            is_fresh = age < timedelta(days=ttl_days)

            if is_fresh:
                logger.debug(f"Cache is fresh (age: {age.days} days < {ttl_days} days)")
            else:
                logger.debug(f"Cache is stale (age: {age.days} days >= {ttl_days} days)")

            return is_fresh

        except Exception as e:
            logger.error(f"Error checking cache freshness: {e}")
            return False

    # ==================== SESSION PREFERENCES ====================

    def get_session_preference(self, session_id: str, key: str) -> Optional[Any]:
        """
        Get session preference.

        Args:
            session_id: Session ID
            key: Preference key (e.g., "author_intelligence_declined")

        Returns:
            Preference value or None
        """
        cache_id = f"session_{session_id}"

        try:
            result = self.collection.get(
                ids=[cache_id],
                include=["metadatas"]
            )

            if result["ids"]:
                metadata = result["metadatas"][0]
                preferences = metadata.get("preferences", {})

                if isinstance(preferences, str):
                    preferences = json.loads(preferences)

                return preferences.get(key)

            return None

        except Exception as e:
            logger.warning(f"Error reading session preference: {e}")
            return None

    def store_session_preference(self, session_id: str, key: str, value: Any) -> bool:
        """
        Store session preference.

        Args:
            session_id: Session ID
            key: Preference key
            value: Preference value

        Returns:
            True if stored successfully
        """
        cache_id = f"session_{session_id}"

        try:
            # Get existing preferences
            result = self.collection.get(
                ids=[cache_id],
                include=["metadatas"]
            )

            preferences = {}
            if result["ids"]:
                metadata = result["metadatas"][0]
                preferences = metadata.get("preferences", {})
                if isinstance(preferences, str):
                    preferences = json.loads(preferences)

            # Update preference
            preferences[key] = value

            # Store back
            self.collection.upsert(
                ids=[cache_id],
                documents=[f"Session: {session_id}"],
                metadatas=[{
                    "cache_type": "session",
                    "session_id": session_id,
                    "preferences": json.dumps(preferences),
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }]
            )

            logger.info(f"✓ Stored session preference: {key} = {value}")
            return True

        except Exception as e:
            logger.error(f"Error storing session preference: {e}")
            return False

    # ==================== CACHE CLEANUP ====================

    def cleanup_stale_cache(self) -> int:
        """
        Clean up stale field caches (> 30 days).
        Authors are NEVER cleaned up (permanent).

        Returns:
            Number of entries cleaned up
        """
        cleaned_count = 0

        try:
            # Get all field caches
            result = self.collection.get(
                where={"cache_type": "field"},
                include=["ids", "metadatas"]
            )

            if result["ids"]:
                for i, cache_id in enumerate(result["ids"]):
                    metadata = result["metadatas"][i]
                    cached_at = metadata.get("cached_at")
                    ttl_days = metadata.get("ttl_days", 30)

                    if cached_at and not self.is_cache_fresh(cached_at, ttl_days):
                        # Delete stale cache
                        self.collection.delete(ids=[cache_id])
                        cleaned_count += 1
                        logger.info(f"Cleaned up stale field cache: {cache_id}")

            logger.info(f"Cache cleanup complete: {cleaned_count} entries removed")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        stats = {
            "total_authors": 0,
            "total_fields": 0,
            "total_sessions": 0,
            "stale_fields": 0,
        }

        try:
            # Count by cache type
            for cache_type in ["author", "field", "session"]:
                result = self.collection.get(
                    where={"cache_type": cache_type},
                    include=["ids", "metadatas"]
                )

                count = len(result["ids"]) if result["ids"] else 0

                if cache_type == "author":
                    stats["total_authors"] = count
                elif cache_type == "field":
                    stats["total_fields"] = count

                    # Count stale fields
                    if result["ids"]:
                        for metadata in result["metadatas"]:
                            cached_at = metadata.get("cached_at")
                            ttl_days = metadata.get("ttl_days", 30)
                            if cached_at and not self.is_cache_fresh(cached_at, ttl_days):
                                stats["stale_fields"] += 1

                elif cache_type == "session":
                    stats["total_sessions"] = count

            logger.info(f"Cache stats: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return stats
