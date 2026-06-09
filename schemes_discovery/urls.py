from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .api_views import SchemeMasterViewSet, FarmerProfileViewSet, SchemeRecommendationViewSet

router = DefaultRouter()
router.register(r'schemes', SchemeMasterViewSet, basename='scheme')
router.register(r'farmers', FarmerProfileViewSet, basename='farmer')
router.register(r'recommendations', SchemeRecommendationViewSet, basename='recommendation')

urlpatterns = [
    # JWT Auth Endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API Routes
    path('v1/', include(router.urls)),
]
