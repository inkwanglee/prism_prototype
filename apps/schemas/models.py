# =============================================================================
# Schemas app models.
# =============================================================================
# Two systems live side-by-side here:
#
#   1. Legacy "schema registry" models — Schema + SchemaVersion + SchemaAuditLog.
#      These are the original DRF/admin-driven registry from Sprint 1.
#      They predate the Schema.json-based dynamic table system.
#   2. SchemaSnapshot — added in Sprint 2 to support non-destructive
#      revert of the Schema.json editor.
# =============================================================================

from django.db import models
from django.contrib.auth.models import User


class Schema(models.Model):
    # Schema registry entry. Defines a logical data schema (e.g. "drillhole.collar")
    # whose concrete JSON Schema definitions live on SchemaVersion rows.
    key = models.CharField(max_length=200, unique=True, help_text="e.g., drillhole.collar")
    owner = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['key']
        verbose_name_plural = 'Schemas'

    def __str__(self):
        return self.key

    def get_latest_approved_version(self):
        # Return the most recently created SchemaVersion in the
        # "approved" state for this schema, or None if there is none.
        return self.versions.filter(status='approved').order_by('-created_at').first()


class SchemaVersion(models.Model):
    # One concrete JSON Schema definition for a Schema, plus its
    # lifecycle state (draft -> approved -> deprecated).
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('deprecated', 'Deprecated'),
    ]

    schema = models.ForeignKey(Schema, on_delete=models.CASCADE, related_name='versions')
    # Semantic version string (e.g. "0.1.0"). Unique per Schema.
    version = models.CharField(max_length=20, help_text="Semantic version, e.g., 0.1.0")
    # The actual JSON Schema document, stored as a JSONField so it can
    # be queried via PG operators when needed.
    json_schema = models.JSONField(help_text="JSON Schema Draft 2020-12")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_schema_versions'
    )
    notes = models.TextField(blank=True)

    class Meta:
        # (schema, version) is the natural key — you can't have two
        # "0.1.0" rows for the same Schema.
        unique_together = ('schema', 'version')
        ordering = ['-created_at']
        verbose_name_plural = 'Schema Versions'

    def __str__(self):
        return f"{self.schema.key} v{self.version} ({self.status})"

    @property
    def schema_ref(self):
        # Compose the "<key>@<version>" reference string used by datasets
        # and the validate API to bind data to a schema version.
        return f"{self.schema.key}@{self.version}"


class SchemaAuditLog(models.Model):
    # Per-schema audit trail for the legacy registry — distinct from
    # the global apps.core.AuditLog so the schema detail page can show
    # a focused history without filtering the global log.
    schema = models.ForeignKey(Schema, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=100)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        user = self.changed_by.username if self.changed_by else "Unknown"
        return f"{self.schema.key} - {self.action} by {user}"


class SchemaSnapshot(models.Model):
    # A point-in-time snapshot of the entire Schema.json file content.
    #
    # Created every time a user clicks Save in the Schema Registry editor
    # (only when the content actually changes from the previous snapshot).
    #
    # Lets users revert the on-disk Schema.json back to an earlier version
    # by clicking a timestamp in the "Revert to older Schema" panel.
    content = models.TextField(help_text="Raw JSON text of Schema.json at this point in time")
    saved_at = models.DateTimeField(auto_now_add=True)
    saved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        # Newest-first so the revert panel can pull the most recent
        # snapshots without an explicit order_by.
        ordering = ['-saved_at']
        verbose_name = 'Schema Snapshot'
        verbose_name_plural = 'Schema Snapshots'

    def __str__(self):
        who = self.saved_by.username if self.saved_by else "system"
        return f"Schema snapshot at {self.saved_at:%Y-%m-%d %H:%M} by {who}"
