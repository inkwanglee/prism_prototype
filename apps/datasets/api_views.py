# =============================================================================
# REST API endpoints for the legacy Datasets catalog.
# Mounted under /api/datasets/.
# =============================================================================

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Dataset, Collar, Survey
from .serializers import DatasetSerializer, CollarSerializer, SurveySerializer


class DatasetViewSet(viewsets.ModelViewSet):
    # CRUD endpoint for Dataset records.
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer

    def get_queryset(self):
        # By default only "active" datasets are returned — retired
        # records stay in the DB but are excluded from API responses.
        # Optional `?schema_ref=` and `?owner=` query params apply a
        # case-insensitive substring filter on top.
        queryset = Dataset.objects.filter(status='active')
        schema_ref = self.request.query_params.get('schema_ref', None)
        owner = self.request.query_params.get('owner', None)

        if schema_ref:
            queryset = queryset.filter(schema_ref__icontains=schema_ref)
        if owner:
            queryset = queryset.filter(owner__icontains=owner)

        return queryset

    def perform_create(self, serializer):
        # Stamp the authenticated user as the creator on POSTed records.
        serializer.save(created_by=self.request.user)
