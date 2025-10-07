from django.db import models
from django.contrib.auth.models import User

class Schema(models.Model):
    """Schema registry - defines data schemas"""
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
        """Return the latest approved version"""
        return self.versions.filter(status='approved').order_by('-created_at').first()

class SchemaVersion(models.Model):
    """Schema version - definition of each version of a schema"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('deprecated', 'Deprecated'),
    ]
    
    schema = models.ForeignKey(Schema, on_delete=models.CASCADE, related_name='versions')
    version = models.CharField(max_length=20, help_text="Semantic version, e.g., 0.1.0")
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
        unique_together = ('schema', 'version')
        ordering = ['-created_at']
        verbose_name_plural = 'Schema Versions'
    
    def __str__(self):
        return f"{self.schema.key} v{self.version} ({self.status})"
    
    @property
    def schema_ref(self):
        """Schema reference string"""
        return f"{self.schema.key}@{self.version}"