import json
import os
import traceback
import jsonschema

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import connection

from .models import Schema, SchemaVersion, SchemaAuditLog
from .forms import SchemaForm, SchemaVersionForm

from apps.core.models import AuditLog

SCHEMA_FILE = os.path.join(settings.BASE_DIR, 'Schema.json')

# Type mapping from Schema.json types to PostgreSQL types
TYPE_MAP = {
    "int": "INTEGER",
    "float": "REAL",
    "string": "TEXT",
    "bool": "BOOLEAN",
    "date": "DATE",
}


def parse_type(type_str):
    """Parse a Schema.json type string into a SQL column definition."""
    # Handle string(N) pattern
    base = type_str.split('(')[0].split()[0].strip().lower()
    sql_type = TYPE_MAP.get(base, "TEXT")

    # Check for string with length like string(10)
    if base == "string" and '(' in type_str.split()[0]:
        try:
            length = type_str.split('(')[1].split(')')[0]
            sql_type = f"VARCHAR({length})"
        except (IndexError, ValueError):
            pass

    if "(pk)" in type_str:
        return f"{sql_type} PRIMARY KEY"
    return sql_type


def extract_foreign_keys(fields):
    """Extract foreign key definitions from field type strings."""
    fks = []
    for col, type_str in fields.items():
        if "(fk to" in type_str:
            ref = type_str.split("to")[1].strip(" )")
            ref_table, ref_col = ref.split(".")
            fks.append((col, ref_table, ref_col))
    return fks


@login_required
def schema_list(request):
    """Schema page — edit Schema.json and initialize database."""
    schema_content = ''
    if os.path.exists(SCHEMA_FILE):
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            schema_content = f.read()

    context = {
        'page_title': 'Schema Registry',
        'schema_content': schema_content,
    }
    return render(request, 'schemas/list.html', context)


@login_required
def save_schema(request):
    """Save edited Schema.json content to disk."""
    if request.method == 'POST':
        content = request.POST.get('schema_content', '')
        # Validate it's valid JSON before saving
        try:
            json.loads(content)
            with open(SCHEMA_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
            messages.success(request, 'Schema.json saved successfully.')

            AuditLog.objects.create(
                user=request.user,
                action='save_schema',
                model_name='Schema.json',
                object_id='Schema.json',
            )
        except json.JSONDecodeError as e:
            messages.error(request, f'Invalid JSON — not saved. Error: {e}')
    return redirect('schemas:list')


@login_required
def initialize_db(request):
    """Create database tables from Schema.json."""
    if request.method == 'POST':
        if not os.path.exists(SCHEMA_FILE):
            messages.error(request, 'Schema.json not found. Save a schema first.')
            return redirect('schemas:list')

        try:
            with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
                schema = json.load(f)

            with connection.cursor() as cur:
                created_tables = []
                for table_name, fields in schema.items():
                    column_defs = []
                    foreign_keys = extract_foreign_keys(fields)

                    for col_name, type_str in fields.items():
                        column_defs.append(f'"{col_name}" {parse_type(type_str)}')

                    for fk_col, ref_table, ref_col in foreign_keys:
                        column_defs.append(
                            f'FOREIGN KEY ("{fk_col}") REFERENCES "{ref_table}"("{ref_col}")'
                        )

                    create_stmt = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  ' + ',\n  '.join(column_defs) + '\n);'
                    cur.execute(create_stmt)
                    created_tables.append(table_name)

            messages.success(
                request,
                f'Database initialized. Tables created/verified: {", ".join(created_tables)}'
            )

            AuditLog.objects.create(
                user=request.user,
                action='initialize_db',
                model_name='Schema.json',
                object_id='Schema.json',
            )
        except json.JSONDecodeError as e:
            messages.error(request, f'Invalid JSON in Schema.json: {e}')
        except Exception as e:
            messages.error(request, f'Database initialization failed: {e}')

    return redirect('schemas:list')


@login_required
def schema_detail(request, pk):
    """Schema detail view."""
    schema = get_object_or_404(Schema, pk=pk)
    versions = schema.versions.all()
    context = {
        'page_title': f'Schema: {schema.key}',
        'schema': schema,
        'versions': versions,
    }
    return render(request, 'schemas/detail.html', context)


@login_required
def schema_create(request):
    """Create a new schema."""
    if request.method == 'POST':
        form = SchemaForm(request.POST)
        if form.is_valid():
            schema = form.save(commit=False)
            schema.created_by = request.user
            schema.save()

            SchemaAuditLog.objects.create(
                schema = schema,
                action = 'created',
                changed_by=request.user,
            )
            messages.success(request, f'Schema "{schema.key}" created successfully.')
            return redirect('schemas:detail', pk=schema.pk)
    else:
        form = SchemaForm()

    context = {
        'page_title': 'Create Schema',
        'form': form,
    }
    return render(request, 'schemas/form.html', context)


@login_required
def version_create(request, schema_pk):
    """Create a schema version."""
    schema = get_object_or_404(Schema, pk=schema_pk)

    if request.method == 'POST':
        form = SchemaVersionForm(request.POST)
        if form.is_valid():
            version = form.save(commit=False)
            version.schema = schema
            version.created_by = request.user

            try:
                import jsonschema
                jsonschema.Draft202012Validator.check_schema(version.json_schema)
                version.save()

                SchemaAuditLog.objects.create(
                    schema=schema,
                    action='version_created',
                    changed_by=request.user,
                )

                messages.success(request, f'Version {version.version} created successfully.')
                return redirect('schemas:detail', pk=schema.pk)
            except jsonschema.SchemaError as e:
                messages.error(request, f'Invalid JSON Schema: {str(e)}')
    else:
        form = SchemaVersionForm()

    context = {
        'page_title': f'Add Version to {schema.key}',
        'schema': schema,
        'form': form,
    }
    return render(request, 'schemas/version_form.html', context)


@login_required
def version_approve(request, pk):
    """Approve a schema version."""
    version = get_object_or_404(SchemaVersion, pk=pk)

    if request.method == 'POST':
        version.status = 'approved'
        version.approved_by = request.user
        version.approved_at = timezone.now()
        version.save()

        SchemaAuditLog.objects.create(
            schema=version.schema,
            action='approved',
            changed_by=request.user,
        )

        messages.success(request, f'Version {version.version} approved.')
        return redirect('schemas:detail', pk=version.schema.pk)

    return redirect('schemas:detail', pk=version.schema.pk)
