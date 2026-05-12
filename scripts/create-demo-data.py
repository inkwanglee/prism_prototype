#!/usr/bin/env python
# =============================================================================
# Demo data creation script.
# =============================================================================
# Seeds the LEGACY schema registry (Schema + SchemaVersion + Dataset)
# and a couple of QAQC / Lineage rows so the dashboard widgets show
# something on a fresh install.
#
# NOTE: This does NOT populate the dynamic Schema.json-driven tables
# (Collars_test1, Assay, etc.). To populate those, use the in-app
# "Bulk Add" flow on the Datasets page.
#
# Usage:
#     poetry run python scripts/create-demo-data.py
# =============================================================================

import os
import django
import json

# Bootstrap Django before importing any app models.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prism_site.settings')
django.setup()

from django.contrib.auth.models import User
from apps.schemas.models import Schema, SchemaVersion
from apps.datasets.models import Dataset
from apps.qaqc.models import QaqcRun
from apps.lineage.models import Snapshot


def create_demo_data():
    print("Creating demo data...")

    # Demo user. Created with a known password so the script can be
    # re-run as part of a CI smoke test.
    user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={'email': 'demo@example.com'}
    )
    if created:
        user.set_password('demo123')
        user.save()
        print(f"Created user: {user.username}")

    # Legacy Schema registry entry — distinct from Schema.json.
    schema, created = Schema.objects.get_or_create(
        key='drillhole.collar',
        defaults={
            'owner': 'Exploration Team',
            'description': 'Drillhole collar location schema',
            'created_by': user
        }
    )
    if created:
        print(f"Created schema: {schema.key}")

        # Attach a starter JSON Schema version in the "approved" state
        # so the dataset below can reference it via schema_ref.
        json_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "hole_id": {"type": "string", "description": "Unique drillhole identifier"},
                "project_id": {"type": "string", "description": "Project identifier"},
                "x": {"type": "number", "description": "X coordinate"},
                "y": {"type": "number", "description": "Y coordinate"},
                "z": {"type": "number", "description": "Z elevation"},
                "crs_epsg": {"type": "integer", "description": "EPSG code"}
            },
            "required": ["hole_id", "project_id", "x", "y", "z"]
        }

        version = SchemaVersion.objects.create(
            schema=schema,
            version='0.1.0',
            json_schema=json_schema,
            status='approved',
            created_by=user,
            notes='Initial schema version'
        )
        print(f"Created schema version: {version.version}")

    # Demo Dataset that references the schema above via its schema_ref.
    dataset, created = Dataset.objects.get_or_create(
        key='exploration.drillholes',
        defaults={
            'title': 'Exploration Drillholes Dataset',
            'description': 'Main exploration drillhole dataset',
            'schema_ref': 'drillhole.collar@0.1.0',
            'owner': 'Exploration Team',
            'project_id': 'PRJ-001',
            'row_count': 125,
            'created_by': user
        }
    )
    if created:
        print(f"Created dataset: {dataset.key}")

    # Demo QAQC run so the QAQC dashboard isn't empty on a fresh install.
    qaqc, created = QaqcRun.objects.get_or_create(
        batch_id='BATCH-001',
        defaults={
            'dataset_key': 'exploration.drillholes',
            'status': 'pass',
            'checks_passed': 12,
            'checks_failed': 0
        }
    )
    if created:
        print(f"Created QAQC run: {qaqc.batch_id}")

    # Demo lineage snapshot so the Lineage page isn't empty.
    snapshot, created = Snapshot.objects.get_or_create(
        snapshot_id='snap-20250101-001',
        defaults={
            'dataset_key': 'exploration.drillholes',
            'code_commit': 'abc123def456'
        }
    )
    if created:
        print(f"Created snapshot: {snapshot.snapshot_id}")

    print("\n=== Demo data created successfully! ===")
    print("\nYou can now:")
    print("1. Login with: admin / admin123")
    print("2. Browse schemas at: http://localhost:8000/schemas/")
    print("3. View datasets at: http://localhost:8000/datasets/")


if __name__ == '__main__':
    create_demo_data()
