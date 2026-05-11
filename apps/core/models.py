# =============================================================================
# AuditLog model — records every important write action across the site.
# =============================================================================
# Whenever a view performs a write that operators may need to investigate
# later (schema saves, DB initialisation, row inserts/updates/deletes,
# CSV imports, etc.) it creates an AuditLog row pointing at the actor,
# the action, and the affected model/object.
# =============================================================================

from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    # User who performed the action (nullable so we don't lose history
    # when an account is later deleted).
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Short verb-style code identifying what happened.
    # Examples used in this codebase: create, update, delete, approve,
    # save_schema, initialize_db, add_entry, add_bulk, edit_entry,
    # stage_revert, create_schema_from_csv, delete_schema_table.
    action = models.CharField(max_length=64)

    # Which model / table was affected. For dynamic Schema.json tables
    # this is the table name; for schema metadata it's "Schema.json".
    model_name = models.CharField(max_length=128)

    # Which record was affected (PK as a string, or a free-form label
    # like "single" / "12 rows" for bulk operations).
    object_id = models.CharField(max_length=128)

    # Optional snapshot of the row before/after the change.
    # Currently unused by most write paths but kept for future "diff
    # this change" UI.
    before_value = models.JSONField(null=True, blank=True)
    after_value = models.JSONField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    # Captured opportunistically for forensics; not always populated.
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        # Newest-first by default so the dashboard's "Recent Activity"
        # widget can show entries without an explicit order_by.
        ordering = ['-timestamp']
        indexes = [
            # Fast lookup of "show me all changes to row X of model Y".
            models.Index(fields=['model_name', 'object_id']),
            # Fast lookup of "show me everything user U did this week".
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.action} on {self.model_name} by {self.user} at {self.timestamp}"
