# =============================================================================
# DRF serializers for the legacy Datasets API at /api/datasets/.
# =============================================================================

from rest_framework import serializers
from .models import Dataset, Collar, Survey


class DatasetSerializer(serializers.ModelSerializer):
    # Catalog-level Dataset record.
    class Meta:
        model = Dataset
        fields = ['id', 'key', 'title', 'description', 'schema_ref', 'owner',
                  'project_id', 'status', 'row_count', 'last_updated', 'created_at']
        # Counts and timestamps are maintained by the server, not the client.
        read_only_fields = ['created_at', 'last_updated', 'row_count']


class CollarSerializer(serializers.ModelSerializer):
    # Single drillhole collar location.
    class Meta:
        model = Collar
        fields = ['id', 'dataset', 'project_id', 'hole_id', 'x', 'y', 'z',
                  'crs_epsg', 'depth_m', 'created_at']
        read_only_fields = ['created_at']


class SurveySerializer(serializers.ModelSerializer):
    # Single downhole survey reading.
    class Meta:
        model = Survey
        fields = ['id', 'collar', 'depth_m', 'dip_deg', 'azimuth_deg', 'created_at']
        read_only_fields = ['created_at']
