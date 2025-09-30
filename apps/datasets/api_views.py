from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Dataset, Collar, Survey
from .serializers import DatasetSerializer, CollarSerializer, SurveySerializer

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    
    def get_queryset(self):
        queryset = Dataset.objects.filter(status='active')
        schema_ref = self.request.query_params.get('schema_ref', None)
        owner = self.request.query_params.get('owner', None)
        
        if schema_ref:
            queryset = queryset.filter(schema_ref__icontains=schema_ref)
        if owner:
            queryset = queryset.filter(owner__icontains=owner)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)