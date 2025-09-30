from django.db import models

class Snapshot(models.Model):
    dataset_key = models.CharField(max_length=128)
    snapshot_id = models.CharField(max_length=64, unique=True)
    code_commit = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.dataset_key}@{self.snapshot_id}"

class LineageEdge(models.Model):
    parent_key = models.CharField(max_length=128)
    child_key = models.CharField(max_length=128)
    snapshot_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']