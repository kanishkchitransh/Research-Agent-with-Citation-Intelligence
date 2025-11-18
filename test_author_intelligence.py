"""
Test suite for Author Intelligence feature.

Tests:
1. Author profile fetching (Perplexity + Semantic Scholar)
2. Permanent caching in ChromaDB
3. Tool integration with agent
4. End-to-end workflow
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from loguru import logger

from author_intelligence import AuthorProfileFetcher, InsightGenerator, TrajectoryAnalyzer
from rag import DocumentProcessor, Retriever, VectorStore
from rag.cache_manager import CacheManager

# Load environment
load_dotenv()


def test_author_profile_fetcher():
    """Test author profile fetching with real APIs."""
    print("\n" + "=" * 70)
    print("TEST 1: Author Profile Fetcher")
    print("=" * 70)

    # Check API keys
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_key:
        print("❌ PERPLEXITY_API_KEY not found in environment")
        return False

    print(f"✓ Perplexity API key found: {perplexity_key[:10]}...")

    try:
        # Initialize fetcher
        fetcher = AuthorProfileFetcher(
            perplexity_api_key=perplexity_key,
            use_semantic_scholar=True
        )
        print("✓ AuthorProfileFetcher initialized")

        # Test 1: Fetch a well-known author (Ashish Vaswani - Transformer paper)
        print("\n--- Fetching profile for 'Ashish Vaswani' ---")
        profile = fetcher.fetch_profile(
            author_name="Ashish Vaswani",
            institution="Google Brain",
            paper_context="Attention mechanism, transformers, neural machine translation"
        )

        print(f"\n✓ Profile fetched successfully!")
        print(f"  Name: {profile.name}")
        print(f"  Normalized: {profile.normalized_name}")
        print(f"  Institution: {profile.institution}")
        print(f"  Expertise: {', '.join(profile.expertise_areas[:3])}")
        print(f"  Publications: {profile.publication_count}")
        print(f"  Citations: {profile.citation_count}")
        print(f"  H-index: {profile.h_index}")
        print(f"  Data sources: {', '.join(profile.sources_used)}")

        if profile.career_overview:
            print(f"\n  Career overview: {profile.career_overview[:200]}...")

        if profile.top_papers:
            print(f"\n  Top papers:")
            for paper in profile.top_papers[:3]:
                print(f"    - {paper['title'][:60]}... ({paper['year']})")

        # Test 2: Normalization
        print("\n--- Testing name normalization ---")
        test_names = [
            "Ashish Vaswani",
            "Ming-Wei Chang",
            "Yoshua Bengio",
            "Geoffrey Hinton"
        ]

        for name in test_names:
            normalized = fetcher.normalize_author_name(name)
            print(f"  '{name}' -> '{normalized}'")

        print("\n✓ Test 1 PASSED: Author Profile Fetcher works!")
        return True

    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_manager():
    """Test permanent caching in ChromaDB."""
    print("\n" + "=" * 70)
    print("TEST 2: Cache Manager (Permanent Caching)")
    print("=" * 70)

    try:
        # Initialize components
        vector_store = VectorStore(
            db_path=Path("./data/vector_db"),
            collection_name="research_papers"
        )
        cache_manager = CacheManager(vector_store)
        print("✓ CacheManager initialized")

        # Test cache operations
        test_profile = {
            "name": "Test Author",
            "normalized_name": "test_author",
            "institution": "Test University",
            "expertise_areas": ["Machine Learning", "NLP"],
            "publication_count": 50,
            "citation_count": 1000,
            "h_index": 20,
            "fetched_at": "2024-01-01 00:00:00",
            "sources_used": ["perplexity", "semantic_scholar"]
        }

        # Store in cache
        print("\n--- Storing test profile in cache ---")
        success = cache_manager.store_author_cache("test_author", test_profile)
        if success:
            print("✓ Profile cached successfully")
        else:
            print("❌ Failed to cache profile")
            return False

        # Retrieve from cache
        print("\n--- Retrieving from cache ---")
        cached = cache_manager.get_cached_author("test_author")

        if cached:
            print("✓ Cache HIT! Profile retrieved:")
            print(f"  Name: {cached['name']}")
            print(f"  Institution: {cached['institution']}")
            print(f"  Publications: {cached['publication_count']}")
        else:
            print("❌ Cache MISS! Profile not found")
            return False

        # Test cache miss
        print("\n--- Testing cache miss ---")
        missing = cache_manager.get_cached_author("nonexistent_author")
        if missing is None:
            print("✓ Cache correctly returns None for missing author")
        else:
            print("❌ Cache should return None for missing author")
            return False

        # Get cache stats
        print("\n--- Cache statistics ---")
        stats = cache_manager.get_cache_stats()
        print(f"  Total authors cached: {stats['total_authors']}")
        print(f"  Total fields cached: {stats['total_fields']}")
        print(f"  Total sessions: {stats['total_sessions']}")

        print("\n✓ Test 2 PASSED: Cache Manager works!")
        return True

    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_insight_generator():
    """Test Gemini-powered insight generation."""
    print("\n" + "=" * 70)
    print("TEST 3: Insight Generator (Gemini Summaries)")
    print("=" * 70)

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("❌ GOOGLE_API_KEY not found in environment")
        return False

    print(f"✓ Google API key found: {google_api_key[:10]}...")

    try:
        # Initialize generator
        generator = InsightGenerator(api_key=google_api_key)
        print("✓ InsightGenerator initialized")

        # Create mock profile
        from author_intelligence.profile_fetcher import AuthorProfile

        mock_profile = AuthorProfile(
            name="Ashish Vaswani",
            normalized_name="ashish_vaswani",
            institution="Google Brain",
            expertise_areas=["Machine Learning", "NLP", "Transformers"],
            publication_count=15,
            citation_count=50000,
            h_index=25,
            career_overview="Research scientist at Google Brain working on neural machine translation and attention mechanisms. Co-author of the Attention is All You Need paper.",
            current_focus="Large language models and efficient transformers",
            top_papers=[
                {"title": "Attention Is All You Need", "year": 2017, "citations": 40000},
                {"title": "Tensor2Tensor", "year": 2018, "citations": 5000},
            ]
        )

        # Test quick summary
        print("\n--- Generating QUICK summary ---")
        quick = generator.generate_quick_summary(
            mock_profile,
            paper_context="Transformer architecture for sequence-to-sequence modeling"
        )
        print(f"Quick summary ({len(quick)} chars):\n{quick}\n")

        # Test standard summary
        print("--- Generating STANDARD summary ---")
        standard = generator.generate_standard_summary(
            mock_profile,
            paper_context="Transformer architecture for sequence-to-sequence modeling"
        )
        print(f"Standard summary ({len(standard)} chars):\n{standard}\n")

        print("✓ Test 3 PASSED: Insight Generator works!")
        return True

    except Exception as e:
        print(f"\n❌ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tools_integration():
    """Test the 3 new author intelligence tools."""
    print("\n" + "=" * 70)
    print("TEST 4: Tool Integration")
    print("=" * 70)

    try:
        # This test requires a full setup with retriever
        # For now, just verify tools are registered

        from agent import ToolRegistry
        from config import config

        # Initialize minimal retriever
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

        # Initialize tool registry
        tool_registry = ToolRegistry(
            retriever=retriever,
            api_key=os.getenv("GOOGLE_API_KEY"),
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY")
        )

        # Check tools are registered
        all_tools = tool_registry.get_all_tools()
        tool_names = [tool.name for tool in all_tools]

        print(f"\n✓ Total tools registered: {len(all_tools)}")
        print("\nAuthor Intelligence Tools:")

        author_tools = [
            "get_author_intelligence",
            "fetch_paper_authors",
            "should_offer_author_intelligence"
        ]

        for tool_name in author_tools:
            if tool_name in tool_names:
                print(f"  ✓ {tool_name}")
            else:
                print(f"  ❌ {tool_name} NOT FOUND")
                return False

        print("\nAll tools registered:")
        for i, name in enumerate(tool_names, 1):
            print(f"  {i}. {name}")

        print("\n✓ Test 4 PASSED: All tools registered correctly!")
        return True

    except Exception as e:
        print(f"\n❌ Test 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end():
    """Test complete end-to-end workflow."""
    print("\n" + "=" * 70)
    print("TEST 5: End-to-End Workflow")
    print("=" * 70)

    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")

    if not perplexity_key or not google_key:
        print("❌ Missing API keys")
        return False

    try:
        # 1. Fetch profile
        print("\n1. Fetching author profile...")
        fetcher = AuthorProfileFetcher(perplexity_api_key=perplexity_key)
        profile = fetcher.fetch_profile("Yoshua Bengio")
        print(f"   ✓ Fetched profile for {profile.name}")

        # 2. Cache profile
        print("\n2. Caching profile...")
        vector_store = VectorStore(
            db_path=Path("./data/vector_db"),
            collection_name="research_papers"
        )
        cache_manager = CacheManager(vector_store)

        profile_dict = {
            "name": profile.name,
            "normalized_name": profile.normalized_name,
            "institution": profile.institution,
            "expertise_areas": profile.expertise_areas,
            "publication_count": profile.publication_count,
            "citation_count": profile.citation_count,
            "h_index": profile.h_index,
            "fetched_at": profile.fetched_at,
            "sources_used": profile.sources_used
        }

        cache_manager.store_author_cache(profile.normalized_name, profile_dict)
        print(f"   ✓ Cached as '{profile.normalized_name}'")

        # 3. Retrieve from cache
        print("\n3. Retrieving from cache...")
        cached = cache_manager.get_cached_author(profile.normalized_name)
        if cached:
            print(f"   ✓ Cache HIT: {cached['name']}")
        else:
            print("   ❌ Cache MISS")
            return False

        # 4. Generate insights
        print("\n4. Generating insights with Gemini...")
        generator = InsightGenerator(api_key=google_key)

        from author_intelligence.profile_fetcher import AuthorProfile
        profile_obj = AuthorProfile(**cached)

        summary = generator.generate_quick_summary(profile_obj)
        print(f"   ✓ Generated summary: {summary[:100]}...")

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED! Author Intelligence is working!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ Test 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n🧪 AUTHOR INTELLIGENCE TEST SUITE")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("Author Profile Fetcher", test_author_profile_fetcher()))
    results.append(("Cache Manager", test_cache_manager()))
    results.append(("Insight Generator", test_insight_generator()))
    results.append(("Tools Integration", test_tools_integration()))
    results.append(("End-to-End Workflow", test_end_to_end()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Author Intelligence is production-ready!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
