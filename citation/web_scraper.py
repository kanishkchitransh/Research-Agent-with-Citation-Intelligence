"""Web scraper for extracting paper content from various sources.

This module can extract abstracts and metadata from:
- ArXiv
- Google Scholar
- IEEE Xplore
- ACM Digital Library
- ResearchGate
- Generic web pages
"""

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from loguru import logger


@dataclass
class ScrapedPaper:
    """Paper content extracted from a web page."""

    title: str
    authors: list[str]
    abstract: str
    source_url: str
    year: Optional[str] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None


class PaperWebScraper:
    """Scrapes paper content from various academic sources."""

    def __init__(self, timeout: int = 10):
        """
        Initialize the web scraper.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        logger.info(f"PaperWebScraper initialized (timeout={timeout}s)")

    def scrape_paper(self, url: str) -> Optional[ScrapedPaper]:
        """
        Scrape paper content from a URL.

        Args:
            url: URL to scrape

        Returns:
            ScrapedPaper if successful, None otherwise
        """
        try:
            domain = urlparse(url).netloc.lower()

            # Route to specialized scraper based on domain
            if "arxiv.org" in domain:
                return self._scrape_arxiv(url)
            elif "scholar.google" in domain:
                return self._scrape_google_scholar(url)
            elif "ieee" in domain or "ieeexplore" in domain:
                return self._scrape_ieee(url)
            elif "acm.org" in domain or "dl.acm.org" in domain:
                return self._scrape_acm(url)
            elif "researchgate.net" in domain:
                return self._scrape_researchgate(url)
            else:
                # Generic scraper for other sources
                return self._scrape_generic(url)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None

    def _scrape_arxiv(self, url: str) -> Optional[ScrapedPaper]:
        """Scrape ArXiv paper page."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")

            # Extract title
            title_elem = soup.find("h1", class_="title mathjax")
            title = title_elem.get_text(strip=True).replace("Title:", "").strip() if title_elem else "Unknown"

            # Extract authors
            authors_elem = soup.find("div", class_="authors")
            authors = []
            if authors_elem:
                for author in authors_elem.find_all("a"):
                    authors.append(author.get_text(strip=True))

            # Extract abstract
            abstract_elem = soup.find("blockquote", class_="abstract mathjax")
            abstract = ""
            if abstract_elem:
                abstract = abstract_elem.get_text(strip=True).replace("Abstract:", "").strip()

            # Extract year
            date_elem = soup.find("div", class_="dateline")
            year = None
            if date_elem:
                date_text = date_elem.get_text()
                year_match = re.search(r"20\d{2}", date_text)
                if year_match:
                    year = year_match.group()

            # Extract PDF URL
            pdf_url = None
            pdf_link = soup.find("a", string=re.compile("PDF"))
            if pdf_link:
                pdf_url = "https://arxiv.org" + pdf_link.get("href")

            logger.info(f"Successfully scraped ArXiv: {title[:50]}...")

            return ScrapedPaper(
                title=title,
                authors=authors,
                abstract=abstract,
                source_url=url,
                year=year,
                pdf_url=pdf_url,
            )

        except Exception as e:
            logger.error(f"Error scraping ArXiv page {url}: {e}")
            return None

    def _scrape_google_scholar(self, url: str) -> Optional[ScrapedPaper]:
        """Scrape Google Scholar paper page."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")

            # Extract title
            title_elem = soup.find("h3", class_="gs_rt")
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            # Extract authors
            authors_elem = soup.find("div", class_="gs_a")
            authors = []
            if authors_elem:
                author_text = authors_elem.get_text()
                # Parse authors (usually format: "Author1, Author2 - Source, Year")
                author_part = author_text.split("-")[0].strip()
                authors = [a.strip() for a in author_part.split(",")]

            # Extract snippet (usually includes abstract snippet)
            abstract_elem = soup.find("div", class_="gs_rs")
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""

            logger.info(f"Successfully scraped Google Scholar: {title[:50]}...")

            return ScrapedPaper(
                title=title,
                authors=authors,
                abstract=abstract,
                source_url=url,
            )

        except Exception as e:
            logger.error(f"Error scraping Google Scholar page {url}: {e}")
            return None

    def _scrape_ieee(self, url: str) -> Optional[ScrapedPaper]:
        """Scrape IEEE Xplore paper page."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")

            # Extract title
            title_elem = soup.find("h1", class_="document-title")
            if not title_elem:
                title_elem = soup.find("meta", property="og:title")
                title = title_elem.get("content") if title_elem else "Unknown"
            else:
                title = title_elem.get_text(strip=True)

            # Extract authors
            authors = []
            author_elems = soup.find_all("span", class_="authors-name")
            for elem in author_elems:
                authors.append(elem.get_text(strip=True))

            # Extract abstract
            abstract_elem = soup.find("div", class_="abstract-text")
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""

            # Extract year
            year_elem = soup.find("meta", property="article:published_time")
            year = year_elem.get("content")[:4] if year_elem else None

            # Extract DOI
            doi_elem = soup.find("a", class_="stats-document-doi-link")
            doi = doi_elem.get_text(strip=True) if doi_elem else None

            logger.info(f"Successfully scraped IEEE: {title[:50]}...")

            return ScrapedPaper(
                title=title,
                authors=authors,
                abstract=abstract,
                source_url=url,
                year=year,
                doi=doi,
            )

        except Exception as e:
            logger.error(f"Error scraping IEEE page {url}: {e}")
            return None

    def _scrape_acm(self, url: str) -> Optional[ScrapedPaper]:
        """Scrape ACM Digital Library paper page."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")

            # Extract title
            title_elem = soup.find("h1", class_="citation__title")
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            # Extract authors
            authors = []
            author_elems = soup.find_all("span", class_="loa__author-name")
            for elem in author_elems:
                authors.append(elem.get_text(strip=True))

            # Extract abstract
            abstract_elem = soup.find("div", class_="abstractSection")
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""

            # Extract DOI
            doi_elem = soup.find("a", class_="issue-item__doi")
            doi = doi_elem.get_text(strip=True).replace("https://doi.org/", "") if doi_elem else None

            logger.info(f"Successfully scraped ACM: {title[:50]}...")

            return ScrapedPaper(
                title=title,
                authors=authors,
                abstract=abstract,
                source_url=url,
                doi=doi,
            )

        except Exception as e:
            logger.error(f"Error scraping ACM page {url}: {e}")
            return None

    def _scrape_researchgate(self, url: str) -> Optional[ScrapedPaper]:
        """Scrape ResearchGate paper page."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")

            # Extract title
            title_elem = soup.find("h1", class_="research-detail-header-section__title")
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"

            # Extract authors
            authors = []
            author_elems = soup.find_all("span", class_="nova-legacy-e-text--size-m")
            for elem in author_elems:
                author_text = elem.get_text(strip=True)
                if author_text and len(author_text) > 2:
                    authors.append(author_text)

            # Extract abstract
            abstract_elem = soup.find("div", class_="research-detail-middle-section__abstract")
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""

            logger.info(f"Successfully scraped ResearchGate: {title[:50]}...")

            return ScrapedPaper(
                title=title,
                authors=authors,
                abstract=abstract,
                source_url=url,
            )

        except Exception as e:
            logger.error(f"Error scraping ResearchGate page {url}: {e}")
            return None

    def _scrape_generic(self, url: str) -> Optional[ScrapedPaper]:
        """Generic scraper for unknown sources using trafilatura."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Use trafilatura to extract main content
            extracted = trafilatura.extract(
                response.content,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
            )

            if not extracted:
                logger.warning(f"No content extracted from {url}")
                return None

            soup = BeautifulSoup(response.content, "lxml")

            # Try to find title from meta tags or h1
            title = "Unknown"
            title_meta = soup.find("meta", property="og:title")
            if title_meta:
                title = title_meta.get("content")
            else:
                h1 = soup.find("h1")
                if h1:
                    title = h1.get_text(strip=True)

            # Extract abstract from first few sentences
            sentences = extracted.split(". ")
            abstract = ". ".join(sentences[:3]) + "." if sentences else extracted[:500]

            logger.info(f"Successfully scraped generic page: {title[:50]}...")

            return ScrapedPaper(
                title=title,
                authors=[],  # Generic scraper can't reliably extract authors
                abstract=abstract,
                source_url=url,
            )

        except Exception as e:
            logger.error(f"Error scraping generic page {url}: {e}")
            return None
