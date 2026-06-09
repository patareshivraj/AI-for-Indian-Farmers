import json
from typing import List
from pydantic import BaseModel, Field
from django.forms.models import model_to_dict
from .models import SchemeMaster, FarmerProfile, SchemeRecommendation
from .ai_processor import get_groq_client

class AIRecommendationSchema(BaseModel):
    is_eligible: bool
    base_match_score: int = Field(..., ge=0, le=100)
    reasoning_summary: str
    matched_conditions: List[str]
    unclear_conditions: List[str]

def evaluate_scheme_eligibility(farmer: FarmerProfile, scheme: SchemeMaster) -> AIRecommendationSchema:
    """Uses Groq LLM to dynamically evaluate unstructured eligibility criteria against structured profile."""
    client = get_groq_client()
    
    farmer_data = model_to_dict(farmer)
    del farmer_data['id']
    del farmer_data['user_id']
    
    scheme_data = {
        "name": scheme.canonical_name,
        "type": scheme.scheme_type,
        "eligibility": scheme.eligibility,
        "benefits": scheme.benefits
    }
    
    system_prompt = """You are an expert Agricultural Scheme Advisor for Indian Farmers.
    Your job is to determine if a specific farmer qualifies for a government scheme.
    
    1. Compare the Farmer Profile against the Scheme Eligibility Criteria.
    2. If there is a direct disqualification (e.g., scheme is for SC, farmer is General), return is_eligible: false and score 0.
    3. If the profile matches all criteria, score highly (80-100).
    4. If criteria are mentioned but the farmer profile doesn't specify, list it in 'unclear_conditions'.
    5. Return valid JSON only containing EXACTLY these keys:
       - "is_eligible" (boolean)
       - "base_match_score" (integer 0-100)
       - "reasoning_summary" (string explanation)
       - "matched_conditions" (array of strings)
       - "unclear_conditions" (array of strings)
    """
    
    user_prompt = f"""
    Farmer Profile:
    {json.dumps(farmer_data, indent=2)}
    
    Scheme Details:
    {json.dumps(scheme_data, indent=2)}
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(completion.choices[0].message.content)
        return AIRecommendationSchema(**result)
    except Exception as e:
        print(f"Recommendation LLM failed for Scheme {scheme.id}: {e}")
        return None

def generate_recommendations(farmer: FarmerProfile):
    """
    Main Recommendation Pipeline.
    """
    print(f"Generating recommendations for {farmer}...")
    
    # 1. DB-Level Pre-Filtering (Geographic optimization)
    # Exclude schemes explicitly meant for other states.
    # Note: A real implementation would use a more complex vector or trigram filter here.
    schemes = SchemeMaster.objects.filter(is_active=True)[:50] 
    
    recommendations_created = 0
    
    for scheme in schemes:
        # Check if recommendation already exists
        if SchemeRecommendation.objects.filter(farmer=farmer, scheme=scheme).exists():
            continue
            
        ai_eval = evaluate_scheme_eligibility(farmer, scheme)
        print(f"DEBUG: {ai_eval}")
        if not ai_eval or not ai_eval.is_eligible:
            continue
            
        # 2. Scoring Mechanism
        # Base match score from AI (0-100) + Quality Data Score from DB (0-100)
        # We normalize to 0-100
        quality_weight = scheme.data_quality_score / 100.0
        final_score = int((ai_eval.base_match_score * 0.8) + (quality_weight * 20))
        
        if final_score >= 40:
            SchemeRecommendation.objects.create(
                farmer=farmer,
                scheme=scheme,
                total_score=final_score,
                ai_reasoning=ai_eval.reasoning_summary,
                matched_conditions=ai_eval.matched_conditions,
                unclear_conditions=ai_eval.unclear_conditions
            )
            recommendations_created += 1
            print(f"Recommended: {scheme.canonical_name} (Score: {final_score})")
            
    print(f"Created {recommendations_created} recommendations for {farmer.user_id}")
