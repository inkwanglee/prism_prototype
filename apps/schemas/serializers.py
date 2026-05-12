# =============================================================================
# DRF serializers for the legacy schema registry.
# =============================================================================
# Used by the REST API mounted at /api/schemas/.
# =============================================================================

from rest_framework import serializers
from .models import Schema, SchemaVersion


class SchemaVersionSerializer(serializers.ModelSerializer):
    # Single SchemaVersion record. Adds the computed `schema_ref` field
    # ("<key>@<version>") so API clients don't have to assemble it themselves.
    schema_ref = serializers.ReadOnlyField()

    class Meta:
        model = SchemaVersion
        fields = ['id', 'version', 'json_schema', 'status', 'created_at',
                  'approved_at', 'notes', 'schema_ref']
        read_only_fields = ['created_at', 'approved_at', 'status']


class SchemaSerializer(serializers.ModelSerializer):
    # Schema with nested versions and a convenience `latest_version`
    # field pointing at the most recent approved version, if any.
    versions = SchemaVersionSerializer(many=True, read_only=True)
    latest_version = serializers.SerializerMethodField()

    class Meta:
        model = Schema
        fields = ['id', 'key', 'owner', 'description', 'created_at',
                  'versions', 'latest_version']
        read_only_fields = ['created_at']

    def get_latest_version(self, obj):
        # Return the latest approved version as a nested serialized
        # object, or None if no version has been approved yet.
        version = obj.get_latest_approved_version()
        if version:
            return SchemaVersionSerializer(version).data
        return None
