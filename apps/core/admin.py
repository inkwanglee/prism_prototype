# =============================================================================
# Django Admin registration for the AuditLog model.
# =============================================================================
# Audit entries are exposed read-only so operators can investigate
# without being able to fabricate or delete history.
# =============================================================================

from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    # Columns shown in the changelist page.
    list_display = ['user', 'action', 'model_name', 'object_id', 'timestamp']
    # Sidebar filters for narrowing down large audit tables.
    list_filter = ['action', 'model_name', 'timestamp']
    # Free-text search across the most useful identifying fields.
    search_fields = ['user__username', 'model_name', 'object_id']
    # Every field is read-only — audit log entries are never edited by hand.
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'before_value', 'after_value', 'timestamp']
