import os
from duckduckgo_search import DDGS
from .models import DiscoveredURL
from .extraction import process_and_store_content

def search_for_new_schemes(query="new agriculture scheme site:gov.in"):
    """
    Step 1: Uses DDG to find scheme pages.
    """
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=10):
            url = r.get('href')
            if url:
                obj, created = DiscoveredURL.objects.get_or_create(url=url)
                if not obj.is_processed:
                    results.append(obj)
    return results

def discover_and_process_schemes():
    """
    Main pipeline function to run the discovery process.
    Phase 2: Discovery -> ExtractedContent.
    Phase 3 will handle the ExtractedContent -> Groq API -> Scheme models.
    """
    print("Starting scheme discovery...")
    url_objs = search_for_new_schemes()
    print(f"Found {len(url_objs)} new URLs to process.")
    
    for url_obj in url_objs:
        print(f"Processing URL: {url_obj.url}")
        process_and_store_content(url_obj)
        print(f"Completed extraction for: {url_obj.url}")
