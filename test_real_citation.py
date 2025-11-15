"""Test with a real, well-known citation that definitely exists."""

import os
from dotenv import load_dotenv
from citation.resolver import CitationResolver

load_dotenv()

perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")

print("="*70)
print("Testing with REAL Citation: Devlin et al. (2019) - BERT")
print("="*70)

resolver = CitationResolver(
    max_results=3,
    google_api_key=google_api_key,
    perplexity_api_key=perplexity_api_key
)

# Test with BERT - this definitely exists
citation = "Devlin et al. (2019)"
context = "pre-training deep bidirectional transformers language understanding"

print(f"\nCitation: {citation}")
print(f"Context: {context}")
print("\nResolving...\n")

result = resolver.resolve(citation, context)

if result:
    print("\n" + "="*70)
    print("[SUCCESS] RESOLUTION SUCCESSFUL!")
    print("="*70)
    print(f"\nTitle: {result.title}")
    print(f"Authors: {', '.join(result.authors[:3])}...")
    print(f"Year: {result.published}")
    print(f"Method: {result.match_method}")
    print(f"Match Score: {result.match_score}")
    print(f"ArXiv ID: {result.arxiv_id or 'N/A'}")
    print(f"PDF URL: {result.pdf_url}")
    print(f"\nAbstract (first 300 chars):")
    print(result.abstract[:300] + "...")
else:
    print("\n[FAILED] Could not resolve")
