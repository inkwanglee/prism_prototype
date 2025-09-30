from rest_framework import serializers
from .models import Dataset, Collar, Survey

class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = ['id', 'key', 'title', 'description', 'schema_ref', 'owner', 
                  'project_id', 'status', 'row_count', 'last_updated', 'created_at']
        read_only_fields = ['created_at', 'last_updated', 'row_count']

class CollarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collar
        fields = ['id', 'dataset', 'project_id', 'hole_id', 'x', 'y', 'z', 
                  'crs_epsg', 'depth_m', 'created_at']
        read_only_fields = ['created_at']

class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ['id', 'collar', 'depth_m', 'dip_deg', 'azimuth_deg', 'created_at']
        read_only_fields = ['created_at']