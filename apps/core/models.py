from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    """Audit log — record all important changes."""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=64)  # create, update, delete, approve, etc.
    model_name = models.CharField(max_length=128)
    object_id = models.CharField(max_length=128)
    before_value = models.JSONField(null=True, blank=True)
    after_value = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} on {self.model_name} by {self.user} at {self.timestamp}"