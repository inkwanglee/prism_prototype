# =============================================================================
# REST API URL routes for the Schemas app.
# Mounted at /api/schemas/ from the project urls.py.
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# DRF router auto-generates CRUD endpoints for SchemaViewSet.
router = DefaultRouter()
router.register(r'', api_views.SchemaViewSet, basename='schema')

urlpatterns = [
    # Router-generated CRUD: GET/POST /, GET/PUT/PATCH/DELETE /<pk>/, GET /<pk>/versions/
    path('', include(router.urls)),
    # Standalone payload validation endpoint.
    path('validate/', api_views.validate_payload, name='validate'),
]
