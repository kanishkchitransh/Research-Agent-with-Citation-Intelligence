"""Debug web scraper to see what's being extracted."""

from citation.web_scraper import PaperWebScraper

# Test scraping the first ArXiv link from Perplexity results
test_url = "https://arxiv.org/abs/2306.10062"

print("="*70)
print(f"Testing Web Scraper on: {test_url}")
print("="*70)

scraper = PaperWebScraper()
result = scraper.scrape_paper(test_url)

if result:
    print("\n[SUCCESS] Scraping successful!")
    print(f"\nTitle: {result.title}")
    print(f"Authors: {result.authors}")
    print(f"Year: {result.year}")
    print(f"Source URL: {result.source_url}")
    print(f"PDF URL: {result.pdf_url}")
    print(f"\nAbstract (first 500 chars):")
    if result.abstract:
        print(result.abstract[:500])
    else:
        print("[NO ABSTRACT EXTRACTED]")
else:
    print("\n[FAILED] Scraping failed!")
