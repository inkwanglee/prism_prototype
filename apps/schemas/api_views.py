# =============================================================================
# REST API endpoints for the legacy schema registry.
# =============================================================================
# Mounted under /api/schemas/.
# =============================================================================

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import Schema, SchemaVersion
from .serializers import SchemaSerializer, SchemaVersionSerializer
import jsonschema


class SchemaViewSet(viewsets.ModelViewSet):
    # CRUD + list for Schema records. Also exposes a `versions` detail
    # action that returns every SchemaVersion attached to a given Schema.
    queryset = Schema.objects.all()
    serializer_class = SchemaSerializer

    def perform_create(self, serializer):
        # Stamp the authenticated user as the creator on POSTed records.
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        # GET /api/schemas/<pk>/versions/
        # Returns every SchemaVersion attached to this Schema.
        schema = self.get_object()
        versions = schema.versions.all()
        serializer = SchemaVersionSerializer(versions, many=True)
        return Response(serializer.data)


@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'schema_ref': {'type': 'string', 'example': 'drillhole.collar@0.1.0'},
                'payload': {'type': 'object'}
            }
        }
    },
    responses={200: {'type': 'object'}}
)
@api_view(['POST'])
def validate_payload(request):
    # POST /api/schemas/validate/
    # Validate a payload against a stored SchemaVersion identified by
    # `schema_ref` ("<key>@<version>"). Returns:
    #   200 {valid: true,  schema_ref}            on success
    #   400 {valid: false, errors: [{message,...}]} on validation failure
    #   404 {error: ...}                          when the schema isn't found
    schema_ref = request.data.get('schema_ref')
    payload = request.data.get('payload')

    if not schema_ref or not payload:
        return Response(
            {'error': 'schema_ref and payload are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Parse the schema_ref into its key and version components.
    try:
        key, version = schema_ref.split('@')
        schema_version = SchemaVersion.objects.get(schema__key=key, version=version)
    except (ValueError, SchemaVersion.DoesNotExist):
        return Response(
            {'error': f'Schema {schema_ref} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Run the payload through jsonschema.validate. On the first error,
    # surface the message, the JSON Pointer path inside the payload,
    # and the path inside the schema so clients can highlight the
    # offending value precisely.
    try:
        jsonschema.validate(payload, schema_version.json_schema)
        return Response({
            'valid': True,
            'schema_ref': schema_ref
        })
    except jsonschema.ValidationError as e:
        return Response({
            'valid': False,
            'errors': [{
                'message': e.message,
                'path': list(e.path),
                'schema_path': list(e.schema_path)
            }]
        }, status=status.HTTP_400_BAD_REQUEST)
