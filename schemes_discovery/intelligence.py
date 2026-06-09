import json
import difflib
from typing import List, Dict, Optional
from django.db import transaction
from .models import Scheme as ExtractedScheme, SchemeMaster, SchemeVersion, SourceMapping, AuditHistory
from .ai_processor import get_groq_client

def calculate_string_similarity(a: str, b: str) -> float:
    """Fallback for pg_trgm using Python's SequenceMatcher"""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

def ask_groq_arbiter(name_a: str, name_b: str, desc_a: str, desc_b: str) -> bool:
    """Uses LLM to verify if two fuzzy-matched schemes are identical."""
    client = get_groq_client()
    prompt = f"""
    You are an expert Government Policy Data Analyst.
    Determine if Scheme A and Scheme B are the exact same government program.
    Sometimes acronyms are used (e.g. PMFBY = Pradhan Mantri Fasal Bima Yojana).
    
    Scheme A: {name_a}
    Description A: {desc_a}
    
    Scheme B: {name_b}
    Description B: {desc_b}
    
    Return ONLY a valid JSON object with a single boolean key 'is_same_scheme'.
    {{"is_same_scheme": true}} or {{"is_same_scheme": false}}
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        result = json.loads(completion.choices[0].message.content)
        return result.get('is_same_scheme', False)
    except Exception as e:
        print(f"Arbiter failed: {e}")
        return False

def merge_arrays(master_array: List[str], new_array: List[str]) -> List[str]:
    """Simple union of two lists without duplicates."""
    merged = set(master_array)
    merged.update(new_array)
    return list(merged)

def bump_version(current_version: str) -> str:
    """Bumps version from v1.0 to v2.0"""
    num = float(current_version.replace("v", ""))
    return f"v{round(num + 1.0, 1)}"

def create_snapshot(master: SchemeMaster) -> dict:
    return {
        "canonical_name": master.canonical_name,
        "scheme_type": master.scheme_type,
        "description": master.description,
        "eligibility": master.eligibility,
        "benefits": master.benefits,
        "documents_required": master.documents_required,
        "apply_url": master.apply_url
    }

def process_extracted_scheme(ext_scheme: ExtractedScheme):
    """
    Deduplication and Consolidation Pipeline.
    """
    # 1. Check if already mapped
    if SourceMapping.objects.filter(extracted_scheme=ext_scheme).exists():
        return

    # 2. Identity Resolution
    masters = SchemeMaster.objects.all()
    best_match = None
    highest_sim = 0.0
    
    for master in masters:
        sim = calculate_string_similarity(ext_scheme.scheme_name, master.canonical_name)
        if sim > highest_sim:
            highest_sim = sim
            best_match = master
            
    is_match = False
    if highest_sim >= 0.85:
        is_match = True
    elif highest_sim >= 0.5:
        # Ask LLM Arbiter for verification of acronyms/translations
        is_match = ask_groq_arbiter(
            ext_scheme.scheme_name, best_match.canonical_name,
            ext_scheme.description, best_match.description
        )

    with transaction.atomic():
        if is_match and best_match:
            # 3. Change Detection & Consolidation
            new_eligibility = merge_arrays(best_match.eligibility, ext_scheme.eligibility)
            new_benefits = merge_arrays(best_match.benefits, ext_scheme.benefits)
            
            changes = []
            if len(new_eligibility) > len(best_match.eligibility):
                changes.append("ELIGIBILITY_EXPANDED")
            if len(new_benefits) > len(best_match.benefits):
                changes.append("BENEFITS_EXPANDED")
                
            if changes:
                # 4. Version Management
                # Save historical snapshot
                SchemeVersion.objects.create(
                    scheme_master=best_match,
                    version_number=best_match.current_version,
                    snapshot=create_snapshot(best_match)
                )
                
                # Apply changes and bump version
                best_match.eligibility = new_eligibility
                best_match.benefits = new_benefits
                best_match.current_version = bump_version(best_match.current_version)
                best_match.save()
                
                AuditHistory.objects.create(
                    scheme_master=best_match,
                    change_type="UPDATE_VERSION",
                    details=f"Bumped to {best_match.current_version} due to {', '.join(changes)}"
                )
            
            # Map Source
            SourceMapping.objects.create(
                scheme_master=best_match,
                extracted_scheme=ext_scheme,
                contribution_type="UPDATE" if changes else "CORROBORATING"
            )
            
        else:
            # 5. New Entity Creation
            new_master = SchemeMaster.objects.create(
                canonical_name=ext_scheme.scheme_name,
                scheme_type=ext_scheme.scheme_type,
                description=ext_scheme.description,
                eligibility=ext_scheme.eligibility,
                benefits=ext_scheme.benefits,
                documents_required=ext_scheme.documents_required,
                apply_url=ext_scheme.apply_url,
                data_quality_score=int(ext_scheme.confidence_score * 100)
            )
            
            SourceMapping.objects.create(
                scheme_master=new_master,
                extracted_scheme=ext_scheme,
                contribution_type="INITIAL"
            )
            
            AuditHistory.objects.create(
                scheme_master=new_master,
                change_type="NEW_ENTITY",
                details=f"Created Master Record v1.0 from {ext_scheme.source_hash}"
            )
