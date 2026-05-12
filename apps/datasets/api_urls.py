# =============================================================================
# REST API URL routes for the Datasets app.
# Mounted at /api/datasets/ from the project urls.py.
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# DRF router auto-generates CRUD endpoints for DatasetViewSet.
router = DefaultRouter()
router.register(r'', api_views.DatasetViewSet, basename='dataset')

urlpatterns = [
    path('', include(router.urls)),
]
