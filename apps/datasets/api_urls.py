from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'', api_views.DatasetViewSet, basename='dataset')

urlpatterns = [
    path('', include(router.urls)),
]