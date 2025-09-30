from django.db import models

class QaqcRun(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ]
    
    dataset_key = models.CharField(max_length=128)
    batch_id = models.CharField(max_length=128)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    checks_passed = models.IntegerField(default=0)
    checks_failed = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"QAQC {self.batch_id} - {self.status}"