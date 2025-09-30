from django.contrib import admin
from .models import Schema, SchemaVersion

@admin.register(Schema)
class SchemaAdmin(admin.ModelAdmin):
    list_display = ['key', 'owner', 'created_at']
    search_fields = ['key', 'owner']
    list_filter = ['created_at']

@admin.register(SchemaVersion)
class SchemaVersionAdmin(admin.ModelAdmin):
    list_display = ['schema', 'version', 'status', 'created_at', 'approved_at']
    list_filter = ['status', 'created_at']
    search_fields = ['schema__key', 'version']