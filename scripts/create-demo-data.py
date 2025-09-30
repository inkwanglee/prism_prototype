#!/usr/bin/env python
"""
데모 데이터 생성 스크립트
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prism_site.settings')
django.setup()

from django.contrib.auth.models import User
from apps.schemas.models import Schema, SchemaVersion
from apps.datasets.models import Dataset
from apps.ingestion.models import IngestionRun
from apps.qaqc.models import QaqcRun
from apps.lineage.models import Snapshot

def create_demo_data():
    print("Creating demo data...")
    
    # 사용자 생성
    user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={'email': 'demo@example.com'}
    )
    if created:
        user.set_password('demo123')
        user.save()
        print(f"Created user: {user.username}")
    
    # 스키마 생성
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
        
        # 스키마 버전 생성
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
    
    # 데이터셋 생성
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
    
    # Ingestion Run 생성
    run, created = IngestionRun.objects.get_or_create(
        source='ALS_Lab',
        defaults={
            'status': 'completed',
            'total_rows': 150,
            'success_rows': 145,
            'failed_rows': 5,
            'created_by': user,
            'notes': 'Initial data import from ALS laboratory'
        }
    )
    if created:
        print(f"Created ingestion run: {run.id}")
    
    # QAQC Run 생성
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
    
    # Snapshot 생성
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