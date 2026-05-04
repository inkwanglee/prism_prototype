import json
import os
import jsonschema
import csv
import io
import re

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import connection
from django.urls import reverse

from .models import Schema, SchemaVersion, SchemaAuditLog, SchemaSnapshot
from .forms import SchemaForm, SchemaVersionForm

from apps.core.models import AuditLog
from apps.accounts.permissions import non_guest_required, user_is_guest

SCHEMA_FILE = os.path.join(settings.BASE_DIR, 'Schema.json')

# How many recent snapshots to surface in the "Revert" panel
REVERT_PANEL_LIMIT = 3

# Type mapping from Schema.json types to PostgreSQL types
TYPE_MAP = {
    "int": "INTEGER",
    "float": "REAL",
    "string": "TEXT",
    "bool": "BOOLEAN",
    "date": "DATE",
}

def _looks_like_int(value):
    try:
        int(str(value).strip())
        return True
    except (ValueError, TypeError):
        return False


def _looks_like_float(value):
    try:
        float(str(value).strip())
        return True
    except (ValueError, TypeError):
        return False

def infer_type(value):
    try:
        int(value)
        return "int"
    except:
        try:
            float(value)
            return "float"
        except:
            return "string"

def _autoincrement_pk_sql():
    """
    Return the correct auto-increment PRIMARY KEY DDL for the active DB vendor.

    Postgres  -> SERIAL PRIMARY KEY
    SQLite    -> INTEGER PRIMARY KEY AUTOINCREMENT
    (fallback -> INTEGER PRIMARY KEY)
    """
    vendor = connection.vendor
    if vendor == 'postgresql':
        return "SERIAL PRIMARY KEY"
    if vendor == 'sqlite':
        return "INTEGER PRIMARY KEY AUTOINCREMENT"
    return "INTEGER PRIMARY KEY"


def parse_type(type_str):
    """
    Parse a Schema.json type string into a SQL column definition.

    Special handling:
    - `int (pk)`  -> auto-increment PK (SERIAL on Postgres)
    - `string(N)` -> VARCHAR(N)
    """
    base = type_str.split('(')[0].split()[0].strip().lower()

    # Auto-increment integer primary key
    if base == "int" and "(pk)" in type_str:
        return _autoincrement_pk_sql()

    sql_type = TYPE_MAP.get(base, "TEXT")

    # string(N) -> VARCHAR(N)
    if base == "string" and '(' in type_str.split()[0]:
        try:
            length = type_str.split('(')[1].split(')')[0]
            sql_type = f"VARCHAR({length})"
        except (IndexError, ValueError):
            pass

    # Non-int PK (e.g. string PK) stays manual
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


# ────────────────────────────────────────────────────────────
# Helper: build the Keycloak admin console URL from OIDC settings.
# Browser-facing — uses the issuer the user's browser can reach.
# ────────────────────────────────────────────────────────────
def _keycloak_admin_url():
    """
    Return the Keycloak admin console URL the browser should open.

    Derived from OIDC_ISSUER in settings — for example
    "http://localhost:8080/realms/prism" -> "http://localhost:8080/admin/".
    Returns None if OIDC is disabled or the issuer cannot be parsed.
    """
    if getattr(settings, 'DISABLE_OIDC', True):
        return None

    issuer = os.environ.get('OIDC_ISSUER', '')
    if not issuer:
        return None

    # Strip "/realms/<name>" suffix to get the base Keycloak host.
    base = issuer.split('/realms/')[0].rstrip('/')
    if not base:
        return None

    return f"{base}/admin/"


@login_required
def schema_list(request):
    """Schema page — edit Schema.json and initialize database."""
    schema_content = ''
    if os.path.exists(SCHEMA_FILE):
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            schema_content = f.read()

    # If the user just clicked a "Revert" link, the staged content
    # for that snapshot is in the session — load it into the editor
    # instead of the on-disk file. The session is then cleared so a
    # page refresh shows the on-disk content again.
    staged_revert = request.session.pop('schema_staged_revert', None)
    if staged_revert:
        schema_content = staged_revert.get('content', schema_content)
        messages.info(
            request,
            f"Loaded snapshot from {staged_revert.get('saved_at_label', 'earlier')}. "
            f"Click Save to apply, or refresh to discard."
        )

    snapshots = SchemaSnapshot.objects.all()[:REVERT_PANEL_LIMIT]

    context = {
        'page_title': 'Schema Registry',
        'schema_content': schema_content,
        'snapshots': snapshots,
        'keycloak_admin_url': _keycloak_admin_url(),
    }
    return render(request, 'schemas/list.html', context)


@login_required
@non_guest_required
def save_schema(request):
    """
    Save edited Schema.json content to disk AND record a snapshot
    so the user can revert to this point later.
    """
    if request.method == 'POST':
        content = request.POST.get('schema_content', '')

        # Validate JSON before doing anything destructive.
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            messages.error(request, f'Invalid JSON — not saved. Error: {e}')
            return redirect('schemas:list')

        # Write to disk.
        with open(SCHEMA_FILE, 'w', encoding='utf-8') as f:
            f.write(content)

        # Record a snapshot, but only if it actually differs from the
        # most recent one — saving the same content twice is just noise.
        latest = SchemaSnapshot.objects.first()
        if latest is None or latest.content != content:
            SchemaSnapshot.objects.create(
                content=content,
                saved_by=request.user,
            )

        messages.success(request, 'Schema.json saved successfully.')

        AuditLog.objects.create(
            user=request.user,
            action='save_schema',
            model_name='Schema.json',
            object_id='Schema.json',
        )

    return redirect('schemas:list')


@login_required
@non_guest_required
def revert_schema(request, snapshot_id):
    """
    Stage an older snapshot for review.

    We DO NOT overwrite Schema.json here. Instead the snapshot content is
    placed in the session, and the next render of the Schema Registry page
    pre-fills the editor with that content. The user must then click Save
    to actually apply it. This makes revert a non-destructive action.
    """
    snapshot = get_object_or_404(SchemaSnapshot, pk=snapshot_id)

    request.session['schema_staged_revert'] = {
        'content': snapshot.content,
        'saved_at_label': snapshot.saved_at.strftime('%d/%m/%Y %I:%M %p'),
        'snapshot_id': snapshot.pk,
    }

    AuditLog.objects.create(
        user=request.user,
        action='stage_revert',
        model_name='Schema.json',
        object_id=str(snapshot.pk),
    )

    return redirect('schemas:list')


@login_required
@non_guest_required
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
                f'Database initialized. Tables created/verified: {", ".join(created_tables)}. '
                f'Note: existing tables are not modified — drop and re-create to pick up PK auto-increment.'
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
@non_guest_required
def schema_create(request):
    """Create a new schema."""
    if request.method == 'POST':
        form = SchemaForm(request.POST)
        if form.is_valid():
            schema = form.save(commit=False)
            schema.created_by = request.user
            schema.save()

            SchemaAuditLog.objects.create(
                schema=schema,
                action='created',
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
@non_guest_required
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
@non_guest_required
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


@login_required
@non_guest_required
def create_schema_from_csv(request):
    if request.method != "POST":
        return redirect('schemas:list')

    csv_file = request.FILES.get("csv_file")
    if not csv_file:
        messages.error(request, "No CSV file uploaded.")
        return redirect('schemas:list')

    try:
        decoded = csv_file.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        rows = list(reader)

        if not reader.fieldnames:
            messages.error(request, "CSV has no header row.")
            return redirect('schemas:list')

        if not rows:
            messages.error(request, "CSV is empty.")
            return redirect('schemas:list')

        table_name = re.sub(r'\W+', '_', os.path.splitext(csv_file.name)[0]).lower()

        # Check DB table already exists
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                )
                """,
                [table_name],
            )
            table_exists = cur.fetchone()[0]

        if table_exists:
            messages.error(
                request,
                f'Table "{table_name}" already exists. Please use a different CSV name or remove the existing table first.'
            )
            return redirect('schemas:list')

        # Load Schema.json
        if os.path.exists(SCHEMA_FILE):
            with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
                schema = json.load(f)
        else:
            schema = {}

        if table_name in schema:
            messages.error(
                request,
                f'Schema "{table_name}" already exists in Schema.json.'
            )
            return redirect('schemas:list')

        # Infer columns
        columns = {}

        for col in reader.fieldnames:
            safe_col = re.sub(r'\W+', '_', col).strip('_')
            if not safe_col:
                continue

            sample_values = [
                row.get(col, "")
                for row in rows[:20]
                if row.get(col, "") not in ("", None)
            ]

            if not sample_values:
                inferred = "string"
            elif all(_looks_like_int(v) for v in sample_values):
                inferred = "int"
            elif all(_looks_like_float(v) for v in sample_values):
                inferred = "float"
            else:
                inferred = "string"

            columns[safe_col] = inferred

        # Add auto primary key
        pk_name = f"{table_name}_id"
        columns = {pk_name: "int (pk)", **columns}

        # Update Schema.json
        schema[table_name] = columns

        with open(SCHEMA_FILE, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2)

        # Create DB table
        with connection.cursor() as cur:
            column_defs = []
            for col_name, type_str in columns.items():
                column_defs.append(f'"{col_name}" {parse_type(type_str)}')

            create_stmt = (
                f'CREATE TABLE "{table_name}" (\n  '
                + ',\n  '.join(column_defs)
                + '\n);'
            )
            cur.execute(create_stmt)

        messages.success(
            request,
            f'Table "{table_name}" created from CSV and added to Schema.json.'
        )

        AuditLog.objects.create(
            user=request.user,
            action="create_schema_from_csv",
            model_name=table_name,
            object_id=table_name,
        )

    except UnicodeDecodeError:
        messages.error(request, "Could not read CSV file. Please check the file encoding.")
    except json.JSONDecodeError as e:
        messages.error(request, f"Schema.json is invalid JSON: {e}")
    except Exception as e:
        messages.error(request, f"Failed to create schema from CSV: {e}")

    return redirect('schemas:list')