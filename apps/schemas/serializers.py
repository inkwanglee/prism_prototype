from rest_framework import serializers
from .models import Schema, SchemaVersion

class SchemaVersionSerializer(serializers.ModelSerializer):
    schema_ref = serializers.ReadOnlyField()
    
    class Meta:
        model = SchemaVersion
        fields = ['id', 'version', 'json_schema', 'status', 'created_at', 
                  'approved_at', 'notes', 'schema_ref']
        read_only_fields = ['created_at', 'approved_at', 'status']

class SchemaSerializer(serializers.ModelSerializer):
    versions = SchemaVersionSerializer(many=True, read_only=True)
    latest_version = serializers.SerializerMethodField()
    
    class Meta:
        model = Schema
        fields = ['id', 'key', 'owner', 'description', 'created_at', 
                  'versions', 'latest_version']
        read_only_fields = ['created_at']
    
    def get_latest_version(self, obj):
        version = obj.get_latest_approved_version()
        if version:
            return SchemaVersionSerializer(version).data
        return None