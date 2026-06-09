import os
import random
import urllib.parse
from datetime import datetime
from duckduckgo_search import DDGS
from .models import DiscoveredURL
from .extraction import process_and_store_content

# Discovery Parameters
BASE_QUERIES = [
    "agriculture scheme", 
    "farmer subsidy", 
    "crop insurance", 
    "agricultural loan", 
    "kisan yojana"
]
DOMAINS = ["site:gov.in", "site:nic.in", "site:nabard.org"]

def generate_dynamic_queries():
    current_year = datetime.now().year
    queries = []
    for bq in BASE_QUERIES:
        for domain in DOMAINS:
            queries.append(f"new {bq} {current_year} {domain}")
            queries.append(f"{bq} apply online {domain}")
    return queries

def canonicalize_url(url: str) -> str:
    """Strips tracking parameters and trailing slashes."""
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    clean_url = urllib.parse.urlunparse((scheme, netloc, path, parsed.params, parsed.query, ''))
    return clean_url

def get_source_domain(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc.lower()

def calculate_discovery_score(url: str, title: str, domain: str) -> int:
    score = 0
    # Tier ranking
    if domain in ['myscheme.gov.in', 'india.gov.in', 'api.data.gov.in']:
        score += 50
    elif domain in ['pmkisan.gov.in', 'pmfby.gov.in', 'nabard.org']:
        score += 40
    elif domain in ['agricoop.nic.in', 'moafw.gov.in']:
        score += 30
    elif 'nic.in' in domain or 'gov.in' in domain:
        score += 20
    
    # Title / URL relevance
    keywords = ['scheme', 'yojana', 'subsidy', 'insurance', 'loan', 'kisan']
    lower_title = (title or '').lower()
    lower_url = url.lower()
    
    if any(kw in lower_title for kw in keywords):
        score += 30
    if any(kw in lower_url for kw in ['/schemes/', '/guidelines/', '/apply/']):
        score += 20
        
    return score

def search_for_new_schemes():
    """
    Executes multiple dynamic queries and scores results.
    """
    results_to_process = []
    queries = generate_dynamic_queries()
    
    # Shuffle and pick a few to avoid spamming DDG in a single run
    random.shuffle(queries)
    target_queries = queries[:3]
    
    with DDGS() as ddgs:
        for query in target_queries:
            print(f"Running query: {query}")
            for r in ddgs.text(query, max_results=10):
                raw_url = r.get('href')
                if not raw_url:
                    continue
                    
                url = canonicalize_url(raw_url)
                title = r.get('title', '')
                domain = get_source_domain(url)
                
                score = calculate_discovery_score(url, title, domain)
                is_relevant = score >= 60
                
                obj, created = DiscoveredURL.objects.get_or_create(
                    url=url,
                    defaults={
                        'title': title,
                        'source_domain': domain,
                        'discovery_query': query,
                        'discovery_score': score,
                        'is_relevant': is_relevant
                    }
                )
                
                if not obj.is_processed and obj.is_relevant:
                    if obj not in results_to_process:
                        results_to_process.append(obj)
                
                if not created:
                    obj.save() # Updates last_checked_at
                    
    return results_to_process

def discover_and_process_schemes():
    """
    Main pipeline function to run the discovery process.
    Phase 1: Dynamic Discovery Engine -> Score -> ExtractedContent (Phase 2).
    """
    print("Starting dynamic scheme discovery...")
    url_objs = search_for_new_schemes()
    print(f"Found {len(url_objs)} highly relevant new URLs to process.")
    
    for url_obj in url_objs:
        print(f"Processing URL: {url_obj.url} (Score: {url_obj.discovery_score})")
        process_and_store_content(url_obj)
        print(f"Completed extraction for: {url_obj.url}")
