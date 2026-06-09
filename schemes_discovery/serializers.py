from rest_framework import serializers
from .models import SchemeMaster, FarmerProfile, SchemeRecommendation

class SchemeMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemeMaster
        fields = [
            'id', 'canonical_name', 'scheme_type', 'description',
            'eligibility', 'benefits', 'documents_required', 'apply_url',
            'current_version', 'data_quality_score', 'updated_at'
        ]

class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = '__all__'

class SchemeRecommendationSerializer(serializers.ModelSerializer):
    scheme = SchemeMasterSerializer(read_only=True)
    
    class Meta:
        model = SchemeRecommendation
        fields = [
            'id', 'scheme', 'total_score', 'ai_reasoning',
            'matched_conditions', 'unclear_conditions',
            'is_dismissed', 'is_applied', 'created_at'
        ]
