import os
import json
import hashlib
from typing import List, Optional
import groq
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_text_splitters import RecursiveCharacterTextSplitter
from django.db import transaction
from .models import ExtractedContent, Scheme

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class SchemeSchema(BaseModel):
    scheme_name: str = Field(..., min_length=5)
    scheme_type: str = Field(..., pattern="^(LOAN|INSURANCE|SUBSIDY|ASSISTANCE|OTHER)$")
    description: str
    eligibility: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    documents_required: List[str] = Field(default_factory=list)
    official_url: Optional[str] = None
    apply_url: Optional[str] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class ExtractedSchemesList(BaseModel):
    schemes: List[SchemeSchema]

def get_groq_client():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set.")
    return groq.Client(api_key=GROQ_API_KEY)

def chunk_text(text: str, chunk_size=10000, chunk_overlap=1000) -> List[str]:
    """Splits large text into chunks to fit Groq context windows safely."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)

SYSTEM_PROMPT = """You are an expert Government Policy Analyst and Data Engineer. 
Your task is to extract agricultural schemes from the provided text into a strictly formatted JSON object.

CRITICAL RULES:
1. ONLY extract factual information present in the text.
2. DO NOT hallucinate, invent, or assume any benefits, eligibility criteria, or URLs.
3. If a field's information is completely missing, return an empty array [] or null.
4. The text may contain MULTIPLE schemes. Extract ALL of them into the `schemes` array.
5. Provide a "confidence_score" (0.0 to 1.0) indicating how complete and explicitly stated the extracted data is.

OUTPUT FORMAT:
You must return valid JSON matching this exact structure:
{
  "schemes": [
    {
      "scheme_name": "Exact name of the scheme",
      "scheme_type": "One of: LOAN, INSURANCE, SUBSIDY, ASSISTANCE, OTHER",
      "description": "2-3 sentence summary of the core purpose",
      "eligibility": ["Criteria 1", "Criteria 2"],
      "benefits": ["Benefit 1", "Benefit 2"],
      "documents_required": ["Doc 1", "Doc 2"],
      "official_url": "URL if explicitly mentioned in the text, else null",
      "apply_url": "Application portal URL if explicitly mentioned, else null",
      "confidence_score": 0.85
    }
  ]
}
"""

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_groq_extraction(text_chunk: str) -> ExtractedSchemesList:
    client = get_groq_client()
    
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract scheme details from this text:\n\n{text_chunk}"}
        ],
        model="llama3-70b-8192",
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    
    raw_json = chat_completion.choices[0].message.content
    
    try:
        data = json.loads(raw_json)
        validated_data = ExtractedSchemesList(**data)
        return validated_data
    except ValidationError as e:
        print(f"Pydantic Validation Error: {e}")
        # In a full production system, we could send the error back to Groq to fix.
        # For now, we raise to trigger the retry decorator.
        raise e
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        raise e

def adjust_confidence_score(scheme: SchemeSchema, source_domain: str) -> tuple[float, bool]:
    """Adjusts the LLM's confidence score based on deterministic rules."""
    score = scheme.confidence_score
    needs_review = False
    
    if not scheme.benefits:
        score -= 0.2
    if not scheme.eligibility:
        score -= 0.2
        
    if source_domain in ['myscheme.gov.in', 'india.gov.in', 'api.data.gov.in']:
        score += 0.1
        
    # Cap score
    score = max(0.0, min(1.0, score))
    
    if score < 0.4:
        needs_review = True
        
    return round(score, 2), needs_review

def process_extracted_content(content_id: int):
    """
    Main entry point for Celery worker. 
    Processes a single ExtractedContent row via AI.
    """
    try:
        content_obj = ExtractedContent.objects.get(id=content_id)
    except ExtractedContent.DoesNotExist:
        return
        
    text_chunks = chunk_text(content_obj.clean_content)
    all_schemes = []
    
    for chunk in text_chunks:
        try:
            extracted_list = call_groq_extraction(chunk)
            all_schemes.extend(extracted_list.schemes)
        except Exception as e:
            print(f"Failed to process chunk for content {content_id}: {e}")
            continue

    if not all_schemes:
        print(f"No schemes detected in content {content_id}.")
        return

    # Database integration with Transaction
    with transaction.atomic():
        for scheme_data in all_schemes:
            # Hash dedup
            hash_string = f"{scheme_data.scheme_name}{scheme_data.description}"
            content_hash = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
            
            source_domain = content_obj.url.source_domain
            final_score, needs_review = adjust_confidence_score(scheme_data, source_domain)
            
            Scheme.objects.update_or_create(
                source_hash=content_hash,
                defaults={
                    'scheme_name': scheme_data.scheme_name,
                    'scheme_type': scheme_data.scheme_type,
                    'description': scheme_data.description,
                    'eligibility': scheme_data.eligibility,
                    'benefits': scheme_data.benefits,
                    'documents_required': scheme_data.documents_required,
                    'official_url': scheme_data.official_url or content_obj.url.url,
                    'apply_url': scheme_data.apply_url,
                    'confidence_score': final_score,
                    'needs_review': needs_review,
                    'extracted_from': content_obj
                }
            )
            
    print(f"Successfully saved {len(all_schemes)} schemes from content {content_id}")
