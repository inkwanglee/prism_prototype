from django.db import models
from django.contrib.auth.models import User

class Dataset(models.Model):
    """데이터셋 카탈로그"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('retired', 'Retired'),
    ]
    
    key = models.CharField(max_length=128, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    schema_ref = models.CharField(
        max_length=255, 
        help_text="Schema reference, e.g., drillhole.collar@0.1.0"
    )
    owner = models.CharField(max_length=200)
    project_id = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    row_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.key} - {self.title}"

class Collar(models.Model):
    """드릴홀 Collar 데이터"""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='collars')
    project_id = models.CharField(max_length=64)
    hole_id = models.CharField(max_length=64)
    x = models.FloatField(help_text="X coordinate")
    y = models.FloatField(help_text="Y coordinate")
    z = models.FloatField(help_text="Z elevation")
    crs_epsg = models.IntegerField(default=4326, help_text="EPSG code for CRS")
    depth_m = models.FloatField(null=True, blank=True, help_text="Total depth in meters")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('project_id', 'hole_id')
        ordering = ['project_id', 'hole_id']
        indexes = [
            models.Index(fields=['project_id', 'hole_id']),
        ]
    
    def __str__(self):
        return f"{self.project_id}/{self.hole_id}"

class Survey(models.Model):
    """드릴홀 Survey 데이터"""
    collar = models.ForeignKey(Collar, on_delete=models.CASCADE, related_name='surveys')
    depth_m = models.FloatField(help_text="Depth in meters")
    dip_deg = models.FloatField(help_text="Dip in degrees (-90 to 90)")
    azimuth_deg = models.FloatField(help_text="Azimuth in degrees (0 to 360)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['collar', 'depth_m']
        indexes = [
            models.Index(fields=['collar', 'depth_m']),
        ]
    
    def __str__(self):
        return f"{self.collar.hole_id} @ {self.depth_m}m"