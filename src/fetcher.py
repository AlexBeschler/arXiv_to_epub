"""
Module for fetching content from arXiv.
"""
import requests
import re


def extract_arxiv_id(url: str) -> str | None:
    """
    Extract arXiv ID from URL.
    
    Args:
        url: arXiv URL (e.g., "https://arxiv.org/html/2510.26721v1")
    
    Returns:
        arXiv ID (e.g., "2510.26721") or None if not found
    """
    match = re.search(r'(\d{4}\.\d{5})', url)
    return match.group(1) if match else None


def fetch_html(url: str) -> str:
    """
    Fetch HTML content from arXiv.
    
    Args:
        url: Full URL to arXiv HTML page
    
    Returns:
        HTML content as string
    
    Raises:
        requests.HTTPError: If request fails
    """
    response = requests.get(url)
    response.raise_for_status()
    print(f"Fetched {len(response.text):,} HTML characters")
    return response.text
