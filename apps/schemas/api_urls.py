from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'', api_views.SchemaViewSet, basename='schema')

urlpatterns = [
    path('', include(router.urls)),
    path('validate/', api_views.validate_payload, name='validate'),
]