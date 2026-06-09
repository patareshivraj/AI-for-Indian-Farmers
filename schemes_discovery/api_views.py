from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import SchemeMaster, FarmerProfile, SchemeRecommendation
from .serializers import SchemeMasterSerializer, FarmerProfileSerializer, SchemeRecommendationSerializer
from .recommender import generate_recommendations

class SchemeMasterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Publicly accessible endpoint for searching and viewing consolidated Scheme Golden Records.
    """
    queryset = SchemeMaster.objects.filter(is_active=True).order_by('-data_quality_score')
    serializer_class = SchemeMasterSerializer
    permission_classes = [AllowAny] # Public Read-Only
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['scheme_type']
    search_fields = ['canonical_name', 'description']
    ordering_fields = ['data_quality_score', 'updated_at']

class FarmerProfileViewSet(viewsets.ModelViewSet):
    """
    Endpoint for managing Farmer Profiles. Requires authentication in production.
    """
    queryset = FarmerProfile.objects.all()
    serializer_class = FarmerProfileSerializer
    permission_classes = [AllowAny] # Set to AllowAny for local testing. Use IsAuthenticated in production.
    
    def get_queryset(self):
        # In a real app with auth, return self.request.user.farmerprofile
        return super().get_queryset()

class SchemeRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint to view personalized scheme recommendations.
    """
    queryset = SchemeRecommendation.objects.filter(is_dismissed=False).order_by('-total_score')
    serializer_class = SchemeRecommendationSerializer
    permission_classes = [AllowAny] 
    
    def get_queryset(self):
        farmer_id = self.request.query_params.get('farmer_id')
        if farmer_id:
            return self.queryset.filter(farmer__id=farmer_id)
        return self.queryset
        
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Triggers the AI Recommendation Pipeline for a specific farmer.
        """
        farmer_id = request.data.get('farmer_id')
        if not farmer_id:
            return Response({"error": "farmer_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            farmer = FarmerProfile.objects.get(id=farmer_id)
            generate_recommendations(farmer)
            return Response({"message": f"Recommendations generated successfully for {farmer.user_id}."})
        except FarmerProfile.DoesNotExist:
            return Response({"error": "Farmer not found"}, status=status.HTTP_404_NOT_FOUND)
            
    @action(detail=True, methods=['patch'])
    def feedback(self, request, pk=None):
        """
        Submit feedback on a recommendation.
        """
        rec = self.get_object()
        action = request.data.get('action') # 'apply', 'dismiss'
        
        if action == 'apply':
            rec.is_applied = True
        elif action == 'dismiss':
            rec.is_dismissed = True
            
        rec.save()
        return Response({"status": "Feedback recorded."})
