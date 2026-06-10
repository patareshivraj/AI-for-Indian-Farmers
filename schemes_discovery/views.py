from rest_framework import viewsets, filters
from .models import Scheme
from .serializers import SchemeSerializer

class SchemeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows schemes to be viewed or searched.
    """
    queryset = Scheme.objects.filter(is_active=True).order_by('-discovered_at')
    serializer_class = SchemeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['scheme_name', 'description', 'benefits']
