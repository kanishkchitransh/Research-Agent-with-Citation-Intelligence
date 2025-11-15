"""Test full citation resolution pipeline."""

import os
from dotenv import load_dotenv
from citation.resolver import CitationResolver

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")
perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

print("="*70)
print("Testing Full Citation Resolution Pipeline")
print("="*70)
print(f"Google API Key: {'[SET]' if google_api_key else '[NOT SET]'}")
print(f"Perplexity API Key: {'[SET]' if perplexity_api_key else '[NOT SET]'}")

# Initialize resolver
resolver = CitationResolver(
    max_results=3,
    google_api_key=google_api_key,
    perplexity_api_key=perplexity_api_key
)

# Test citation
citation = "Tucker et al. (2021)"
context = "capabilities language models interventions"

print(f"\nCitation: {citation}")
print(f"Context: {context}")
print("\n" + "-"*70)
print("Resolving...")
print("-"*70)

result = resolver.resolve(citation, context)

if result:
    print("\n[SUCCESS] RESOLUTION SUCCESSFUL!")
    print(f"\nCitation Marker: {result.citation_marker}")
    print(f"Title: {result.title}")
    print(f"Authors: {', '.join(result.authors)}")
    print(f"Published: {result.published}")
    print(f"ArXiv ID: {result.arxiv_id or 'N/A'}")
    print(f"PDF URL: {result.pdf_url}")
    print(f"Match Score: {result.match_score}")
    print(f"Match Method: {result.match_method}")
    print(f"\nAbstract (first 300 chars):")
    print(result.abstract[:300] + "...")
else:
    print("\n[FAILED] RESOLUTION FAILED")
    print("Citation could not be resolved")
