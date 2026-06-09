import io
import hashlib
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import trafilatura
import pdfplumber
from django.utils import timezone
from .models import DiscoveredURL, ExtractedContent

# List of keywords for heuristic quality scoring
AGRICULTURE_KEYWORDS = [
    "scheme", "yojana", "subsidy", "loan", "farmer", "agriculture", 
    "kisan", "eligibility", "apply", "benefit", "insurance", "financial"
]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_url(url: str) -> httpx.Response:
    """
    Fetches the URL with async-compatible httpx and exponential backoff retry.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    with httpx.Client(follow_redirects=True, timeout=15.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response

def extract_pdf_content(content_bytes: bytes) -> str:
    """
    Extracts text from PDF binary stream using pdfplumber.
    """
    extracted_text = []
    with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
    return "\n".join(extracted_text)

def extract_html_content(html_text: str) -> tuple[str, str]:
    """
    Uses Trafilatura to extract the main content, stripping boilerplate.
    Returns (raw_text, clean_text)
    """
    # Raw is just basic extraction or the HTML itself. We'll store HTML as raw.
    clean_text = trafilatura.extract(
        html_text, 
        include_links=True, 
        include_images=False, 
        include_tables=True
    )
    return html_text, (clean_text or "")

def calculate_quality_score(text: str) -> float:
    """
    Calculates a basic heuristic keyword density score.
    """
    if not text:
        return 0.0
    
    words = text.lower().split()
    total_words = len(words)
    if total_words < 10:
        return 0.0

    keyword_count = sum(1 for word in words if any(kw in word for kw in AGRICULTURE_KEYWORDS))
    density = (keyword_count / total_words) * 100
    return round(density, 2)

def process_and_store_content(url_obj: DiscoveredURL):
    """
    Orchestrates the fetch, parse, clean, and store process.
    """
    try:
        response = fetch_url(url_obj.url)
        content_type = response.headers.get("Content-Type", "").lower()

        raw_content = ""
        clean_content = ""
        page_title = ""

        if "application/pdf" in content_type or url_obj.url.lower().endswith(".pdf"):
            raw_content = "PDF_BINARY"
            clean_content = extract_pdf_content(response.content)
            page_title = url_obj.url.split("/")[-1]
        else:
            raw_content, clean_content = extract_html_content(response.text)
            # Basic title extraction
            extracted_meta = trafilatura.extract_metadata(response.text)
            if extracted_meta and extracted_meta.title:
                page_title = extracted_meta.title
            else:
                page_title = url_obj.url

        if not clean_content:
            url_obj.status_code = response.status_code
            url_obj.save()
            return

        # Normalize and hash
        clean_content = " ".join(clean_content.split()) # Remove duplicate whitespace
        content_hash = hashlib.sha256(clean_content.encode('utf-8')).hexdigest()

        # Quality Check
        quality_score = calculate_quality_score(clean_content)
        is_valid = len(clean_content.split()) >= 100 and quality_score > 0.5

        # Update or Create
        ExtractedContent.objects.update_or_create(
            url=url_obj,
            defaults={
                'page_title': page_title,
                'raw_content': raw_content,
                'clean_content': clean_content,
                'content_hash': content_hash,
                'quality_score': quality_score,
                'is_valid_scheme_page': is_valid,
                'last_updated_at': timezone.now()
            }
        )

        url_obj.status_code = response.status_code
        url_obj.is_processed = True
        url_obj.save()

    except Exception as e:
        print(f"Failed to process {url_obj.url}: {str(e)}")
