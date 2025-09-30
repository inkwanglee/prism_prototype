from django.contrib import admin
from .models import Snapshot, LineageEdge

@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ['snapshot_id', 'dataset_key', 'code_commit', 'created_at']
    search_fields = ['snapshot_id', 'dataset_key']
    list_filter = ['created_at']

@admin.register(LineageEdge)
class LineageEdgeAdmin(admin.ModelAdmin):
    list_display = ['parent_key', 'child_key', 'snapshot_id', 'created_at']
    search_fields = ['parent_key', 'child_key', 'snapshot_id']