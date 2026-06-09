from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SchemeViewSet

router = DefaultRouter()
router.register(r'schemes', SchemeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
