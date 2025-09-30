from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .models import Schema, SchemaVersion
from .serializers import SchemaSerializer, SchemaVersionSerializer
import jsonschema

class SchemaViewSet(viewsets.ModelViewSet):
    """Schema Registry API"""
    queryset = Schema.objects.all()
    serializer_class = SchemaSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get all versions of a schema"""
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
    """Validate a payload against a schema"""
    schema_ref = request.data.get('schema_ref')
    payload = request.data.get('payload')
    
    if not schema_ref or not payload:
        return Response(
            {'error': 'schema_ref and payload are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Parse schema_ref
    try:
        key, version = schema_ref.split('@')
        schema_version = SchemaVersion.objects.get(schema__key=key, version=version)
    except (ValueError, SchemaVersion.DoesNotExist):
        return Response(
            {'error': f'Schema {schema_ref} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Validate payload
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