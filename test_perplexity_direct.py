"""Test Perplexity search directly to debug."""

import os
from dotenv import load_dotenv
from citation.perplexity_search import PaperPerplexitySearch

load_dotenv()

api_key = os.getenv("PERPLEXITY_API_KEY")
print(f"API Key loaded: {api_key[:20]}..." if api_key else "No API key")

# Test the search
searcher = PaperPerplexitySearch(api_key=api_key)

print("\n" + "="*70)
print("Testing Perplexity Search for: Tucker et al. (2021)")
print("="*70)

results = searcher.search_paper_by_citation(
    citation_marker="Tucker et al. (2021)",
    context="capabilities language"
)

print(f"\nNumber of results: {len(results)}")

if results:
    for i, result in enumerate(results, 1):
        print(f"\n[Result {i}]")
        print(f"Title: {result.title}")
        print(f"Link: {result.link}")
        print(f"Snippet: {result.snippet[:200]}...")
else:
    print("\n[WARNING] No results found")
    print("\nLet's try a direct search:")

    direct_results = searcher.search_paper("Tucker et al. 2021 academic paper")
    print(f"Direct search results: {len(direct_results)}")

    if direct_results:
        for i, result in enumerate(direct_results, 1):
            print(f"\n[Direct Result {i}]")
            print(f"Title: {result.title}")
            print(f"Link: {result.link}")
