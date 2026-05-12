# =============================================================================
# Lineage skeleton models.
# =============================================================================
# Sprint-1-era scaffold. Tracks reproducibility snapshots and the
# parent/child relationships between datasets so the system can answer
# "what produced this row?". The actual capture logic — emitting Snapshot
# and LineageEdge rows from the ingestion / transform paths — is a
# future-team task.
# =============================================================================

from django.db import models


class Snapshot(models.Model):
    # A point-in-time snapshot of a dataset, identified by an external
    # `snapshot_id` and (optionally) the code commit that produced it.
    dataset_key = models.CharField(max_length=128)
    snapshot_id = models.CharField(max_length=64, unique=True)
    code_commit = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.dataset_key}@{self.snapshot_id}"


class LineageEdge(models.Model):
    # A directed parent->child relationship between two dataset keys,
    # tied to a specific snapshot so the lineage graph is reproducible.
    parent_key = models.CharField(max_length=128)
    child_key = models.CharField(max_length=128)
    snapshot_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
