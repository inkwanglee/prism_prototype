# =============================================================================
# Schemas views for PRISM.
# =============================================================================
# The Schemas app is the control surface for Schema.json — the file that
# declares every dataset table the system knows about. Users can edit the
# JSON directly, save snapshots, revert to earlier versions, initialise
# the database from the current schema, and create or delete schema
# tables from CSV files.
#
# Most write actions also touch the database (e.g. CREATE TABLE, DROP TABLE)
# so they are protected by @non_guest_required and audited via the
# AuditLog model.
# =============================================================================

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

# Path to the on-disk Schema.json — the source of truth for every
# dataset table in PRISM. Edited via the textarea on the Schemas page.
SCHEMA_FILE = os.path.join(settings.BASE_DIR, 'Schema.json')

# How many recent snapshots to surface in the "Revert" panel on the
# Schemas page. Older snapshots stay in the database but are only
# accessible through Django Admin.
REVERT_PANEL_LIMIT = 3

# Maps Schema.json base type names to PostgreSQL column types.
# Used by `parse_type` when generating CREATE TABLE statements.
TYPE_MAP = {
    "int": "INTEGER",
    "float": "REAL",
    "string": "TEXT",
    "bool": "BOOLEAN",
    "date": "DATE",
}


# -----------------------------------------------------------------------------
# Type inference helpers (used by Create-schema-from-CSV)
# -----------------------------------------------------------------------------

def _looks_like_int(value):
    # Return True if `value` parses as a Python int. Used to decide
    # whether a CSV column should be inferred as type "int".
    try:
        int(str(value).strip())
        return True
    except (ValueError, TypeError):
        return False


def _looks_like_float(value):
    # Return True if `value` parses as a Python float. Used to decide
    # whether a CSV column should be inferred as type "float".
    try:
        float(str(value).strip())
        return True
    except (ValueError, TypeError):
        return False


def infer_type(value):
    # Best-effort inference of a single CSV cell's type.
    # Returns one of "int", "float", or "string".
    #
    # NOTE: the live import path (`create_schema_from_csv`) uses the
    # `_looks_like_*` helpers over a sample of rows instead of this
    # function. Kept here for ad-hoc use in shells or scripts.
    try:
        int(value)
        return "int"
    except:
        try:
            float(value)
            return "float"
        except:
            return "string"


# -----------------------------------------------------------------------------
# DDL generation helpers
# -----------------------------------------------------------------------------

def _autoincrement_pk_sql():
    # Return the correct auto-increment PRIMARY KEY DDL for the active
    # database vendor.
    #
    # Postgres  -> SERIAL PRIMARY KEY
    # SQLite    -> INTEGER PRIMARY KEY AUTOINCREMENT
    # (fallback -> INTEGER PRIMARY KEY)
    vendor = connection.vendor
    if vendor == 'postgresql':
        return "SERIAL PRIMARY KEY"
    if vendor == 'sqlite':
        return "INTEGER PRIMARY KEY AUTOINCREMENT"
    return "INTEGER PRIMARY KEY"


def parse_type(type_str):
    # Parse a Schema.json type string into a SQL column definition.
    #
    # Special handling:
    #   - `int (pk)`  -> auto-increment PK (SERIAL on Postgres)
    #   - `string(N)` -> VARCHAR(N)
    base = type_str.split('(')[0].split()[0].strip().lower()

    # Auto-increment integer primary key.
    if base == "int" and "(pk)" in type_str:
        return _autoincrement_pk_sql()

    sql_type = TYPE_MAP.get(base, "TEXT")

    # string(N) -> VARCHAR(N). We detect the "(N)" *inside* the first
    # whitespace-delimited token to avoid matching the "(pk)" / "(fk to ...)"
    # marker that follows the base type.
    if base == "string" and '(' in type_str.split()[0]:
        try:
            length = type_str.split('(')[1].split(')')[0]
            sql_type = f"VARCHAR({length})"
        except (IndexError, ValueError):
            pass

    # Non-int PK (e.g. a string PK) stays manual — the user must supply
    # the value because the DB has no way to auto-generate it.
    if "(pk)" in type_str:
        return f"{sql_type} PRIMARY KEY"
    return sql_type


def extract_foreign_keys(fields):
    # Extract foreign key definitions from a table's field dict.
    #
    # Returns a list of (column, ref_table, ref_column) tuples for any
    # field whose type string contains "(fk to <Table>.<Column>)".
    # Used to append FOREIGN KEY constraints to CREATE TABLE statements.
    #
    # NOTE: we deliberately use a regex match here instead of naive
    # string splitting on "to" / ".", because table names can contain
    # the substring "to" in the middle of a word (e.g. "Laboratory",
    # "Histology") and a plain .split("to") would chop those names
    # apart and trigger "not enough values to unpack" later on.
    fks = []
    for col, type_str in fields.items():
        match = re.search(r'\(fk\s+to\s+(\w+)\.(\w+)\)', type_str)
        if match:
            ref_table = match.group(1)
            ref_col = match.group(2)
            fks.append((col, ref_table, ref_col))
    return fks


# -----------------------------------------------------------------------------
# Helper: build the Keycloak admin console URL from OIDC settings.
# Browser-facing — uses the issuer the user's browser can reach.
# -----------------------------------------------------------------------------
def _keycloak_admin_url():
    # Return the Keycloak admin console URL the browser should open.
    #
    # Derived from OIDC_ISSUER in settings — for example
    # "http://localhost:8080/realms/prism" -> "http://localhost:8080/admin/".
    # Returns None if OIDC is disabled or the issuer cannot be parsed.
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


# -----------------------------------------------------------------------------
# View functions
# -----------------------------------------------------------------------------

@login_required
def schema_list(request):
    # Render the Schema Registry page.
    #
    # The page shows the Schema.json editor textarea, the Initialize
    # Database button, the CSV-based create / delete forms, the recent
    # snapshot list ("Revert to older Schema"), and the Keycloak admin
    # portal shortcut.
    #
    # If the user just clicked a "Revert" link, the staged content is
    # in the session; we pop it here so the editor pre-fills with that
    # snapshot instead of the on-disk file. The pop ensures that a page
    # refresh restores the on-disk content (the user's escape hatch).
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
    # Save edited Schema.json content to disk AND record a snapshot
    # so the user can revert to this point later.
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
        # most recent one — saving the same content twice is just noise
        # in the revert panel.
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
    # Stage an older snapshot for review.
    #
    # We DO NOT overwrite Schema.json here. Instead the snapshot content
    # is placed in the session, and the next render of the Schema Registry
    # page pre-fills the editor with that content. The user must then click
    # Save to actually apply it. This makes revert a non-destructive action
    # and gives the user a chance to discard the change by simply refreshing.
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
    # Create database tables from Schema.json.
    #
    # Uses CREATE TABLE IF NOT EXISTS so existing tables are left
    # untouched. To pick up auto-increment changes on an already-created
    # table the operator must drop and re-create that table manually
    # (or wipe Docker volumes with `docker compose down -v`).
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

                    # Build the column list first.
                    for col_name, type_str in fields.items():
                        column_defs.append(f'"{col_name}" {parse_type(type_str)}')

                    # Append FOREIGN KEY constraints at the end so they
                    # come after every column they might reference.
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
    # Render the legacy Schema-model detail page with its version history.
    # (The Schema/SchemaVersion models predate the Schema.json editor and
    # are kept around for the legacy API at /api/schemas/.)
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
    # Create a legacy Schema record (key, owner, description) via SchemaForm.
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
    # Create a new SchemaVersion attached to a Schema.
    #
    # The submitted JSON Schema is validated against Draft 2020-12 before
    # the version row is saved, so malformed schemas never make it into
    # the registry.
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
    # Mark a SchemaVersion as approved and stamp the approving user / time.
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
    # Create a new schema table from an uploaded CSV file.
    #
    # Workflow:
    #   1. Read the uploaded CSV with UTF-8 BOM tolerance.
    #   2. Derive a SQL-safe table name from the file name (lowercased,
    #      non-word characters collapsed to underscores).
    #   3. Refuse if a table with that name already exists in either
    #      Schema.json or the database.
    #   4. Infer each column's type from the first 20 non-empty values:
    #      all-int -> "int", all-float -> "float", otherwise "string".
    #   5. Prepend an auto-increment primary key column named
    #      "<table>_id" so rows are addressable later.
    #   6. Update Schema.json and CREATE the table in the database.
    #
    # The whole operation is best-effort: any exception aborts and the
    # error is surfaced to the user via a flash message.
    if request.method != "POST":
        return redirect('schemas:list')

    csv_file = request.FILES.get("csv_file")
    if not csv_file:
        messages.error(request, "No CSV file uploaded.")
        return redirect('schemas:list')

    try:
        # `utf-8-sig` strips the optional byte-order mark some Windows
        # tools (Excel especially) prefix to UTF-8 exports.
        decoded = csv_file.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        rows = list(reader)

        if not reader.fieldnames:
            messages.error(request, "CSV has no header row.")
            return redirect('schemas:list')

        if not rows:
            messages.error(request, "CSV is empty.")
            return redirect('schemas:list')

        # Derive a SQL-safe table name from the uploaded file name.
        table_name = re.sub(r'\W+', '_', os.path.splitext(csv_file.name)[0]).lower()

        # Refuse if the DB table already exists — we don't want to
        # silently merge into an existing table that may have a
        # different shape.
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

        # Load Schema.json (or start with an empty schema if missing).
        if os.path.exists(SCHEMA_FILE):
            with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
                schema = json.load(f)
        else:
            schema = {}

        # Also refuse if Schema.json already has an entry with this name.
        if table_name in schema:
            messages.error(
                request,
                f'Schema "{table_name}" already exists in Schema.json.'
            )
            return redirect('schemas:list')

        # Infer a type for each CSV column from the first 20 non-empty values.
        columns = {}

        for col in reader.fieldnames:
            safe_col = re.sub(r'\W+', '_', col).strip('_')
            if not safe_col:
                # Skip empty / non-alphanumeric-only headers.
                continue

            sample_values = [
                row.get(col, "")
                for row in rows[:20]
                if row.get(col, "") not in ("", None)
            ]

            # Order matters: "int" must be tested before "float" because
            # every int also parses as a float. Empty samples default to
            # "string" since we have no evidence to constrain the type.
            if not sample_values:
                inferred = "string"
            elif all(_looks_like_int(v) for v in sample_values):
                inferred = "int"
            elif all(_looks_like_float(v) for v in sample_values):
                inferred = "float"
            else:
                inferred = "string"

            columns[safe_col] = inferred

        # Prepend an auto-increment integer primary key so every row is
        # addressable later (CSV imports rarely come with a stable ID).
        pk_name = f"{table_name}_id"
        columns = {pk_name: "int (pk)", **columns}

        # Persist the new entry in Schema.json.
        schema[table_name] = columns

        with open(SCHEMA_FILE, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2)

        # Create the actual DB table to match.
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


@login_required
@non_guest_required
def delete_schema_table(request):
    # Delete a schema table by name.
    #
    # Removes the entry from Schema.json AND drops the corresponding
    # database table (DROP TABLE IF EXISTS). Operates only on tables
    # that are present in Schema.json — unknown names are rejected with
    # an error so this view cannot be abused to drop arbitrary Postgres
    # tables.
    if request.method == "POST":
        table_name = request.POST.get("table_name", "").strip()

        if not table_name:
            messages.error(request, "Please enter a table name.")
            return redirect("schemas:list")

        try:
            with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
                schema = json.load(f)

            if table_name not in schema:
                messages.error(request, f'"{table_name}" was not found in Schema.json.')
                return redirect("schemas:list")

            # Remove the entry from Schema.json first.
            del schema[table_name]

            with open(SCHEMA_FILE, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2)

            # Then drop the matching DB table if it exists.
            with connection.cursor() as cur:
                cur.execute(f'DROP TABLE IF EXISTS "{table_name}"')

            AuditLog.objects.create(
                user=request.user,
                action="delete_schema_table",
                model_name=table_name,
                object_id=table_name,
            )

            messages.success(request, f'Table "{table_name}" deleted from Schema.json and database.')

        except Exception as e:
            messages.error(request, f"Failed to delete schema table: {e}")

    return redirect("schemas:list")
