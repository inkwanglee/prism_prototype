# =============================================================================
# QAQC (Quality Assurance / Quality Control) skeleton models.
# =============================================================================
# Sprint-1-era scaffold. Tracks one row per QAQC run against a batch of
# data. The actual validation logic (negative-value checks, interval
# sanity, standards z-scores, etc.) is a future-team task — this app
# currently only stores summary rows.
# =============================================================================

from django.db import models


class QaqcRun(models.Model):
    # One run of the QAQC pipeline against a specific batch.
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ]

    # Which dataset (by Schema.json key) this run validated.
    dataset_key = models.CharField(max_length=128)
    # Operator-supplied batch identifier (e.g. a lab report number).
    batch_id = models.CharField(max_length=128)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    checks_passed = models.IntegerField(default=0)
    checks_failed = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"QAQC {self.batch_id} - {self.status}"
