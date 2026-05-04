from django.contrib import admin
from .models import Schema, SchemaVersion, SchemaSnapshot


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


@admin.register(SchemaSnapshot)
class SchemaSnapshotAdmin(admin.ModelAdmin):
    list_display = ['saved_at', 'saved_by', 'short_preview']
    list_filter = ['saved_at']
    search_fields = ['saved_by__username']
    readonly_fields = ['content', 'saved_at', 'saved_by']

    def short_preview(self, obj):
        text = (obj.content or '').strip().replace('\n', ' ')
        return (text[:80] + '…') if len(text) > 80 else text
    short_preview.short_description = 'Preview'
