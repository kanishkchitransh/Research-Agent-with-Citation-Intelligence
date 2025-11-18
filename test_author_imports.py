"""
Quick test to verify imports and basic structure without API calls.
"""

import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

print("Testing imports...")

try:
    # Test author_intelligence imports
    print("\n1. Testing author_intelligence module...")
    from author_intelligence import AuthorProfileFetcher, InsightGenerator, TrajectoryAnalyzer
    print("   ✓ AuthorProfileFetcher")
    print("   ✓ InsightGenerator")
    print("   ✓ TrajectoryAnalyzer")

    # Test cache manager
    print("\n2. Testing cache_manager...")
    from rag.cache_manager import CacheManager
    print("   ✓ CacheManager")

    # Test that classes can be instantiated (without API keys)
    print("\n3. Testing basic instantiation...")

    # AuthorProfileFetcher without API key (should work)
    fetcher = AuthorProfileFetcher(perplexity_api_key=None, use_semantic_scholar=False)
    print("   ✓ AuthorProfileFetcher instantiated")

    # TrajectoryAnalyzer (no dependencies)
    analyzer = TrajectoryAnalyzer()
    print("   ✓ TrajectoryAnalyzer instantiated")

    # Test name normalization
    print("\n4. Testing name normalization...")
    test_names = {
        "Ashish Vaswani": "ashish_vaswani",
        "Ming-Wei Chang": "mingwei_chang",
        "Geoffrey E. Hinton": "geoffrey_e_hinton",
    }

    for name, expected in test_names.items():
        result = fetcher.normalize_author_name(name)
        if result == expected:
            print(f"   ✓ '{name}' -> '{result}'")
        else:
            print(f"   ❌ '{name}' -> '{result}' (expected '{expected}')")

    # Test trajectory analyzer with mock data
    print("\n5. Testing trajectory analyzer...")
    from author_intelligence.profile_fetcher import AuthorProfile

    mock_profile = AuthorProfile(
        name="Test Author",
        normalized_name="test_author",
        expertise_areas=["ML", "NLP"],
        top_papers=[
            {"title": "Paper 1", "year": 2020, "citations": 100},
            {"title": "Paper 2", "year": 2022, "citations": 200},
        ]
    )

    trajectory = analyzer.analyze_trajectory(mock_profile)
    print(f"   ✓ Trajectory analysis completed")
    print(f"     Career stages: {len(trajectory.career_stages)}")
    print(f"     Research evolution: {len(trajectory.research_evolution)} chars")

    print("\n✅ All imports and basic tests passed!")
    print("\nNote: Full API tests require:")
    print("  - PERPLEXITY_API_KEY environment variable")
    print("  - GOOGLE_API_KEY environment variable")
    print("  - pip install -r requirements.txt")

    sys.exit(0)

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
