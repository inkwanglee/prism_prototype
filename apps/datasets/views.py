from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.apps import apps
from django import forms
from django.conf import settings
from django.db import connection, transaction
import csv
import io
import json
import os
import re

from apps.core.models import AuditLog

SCHEMA_FILE = os.path.join(settings.BASE_DIR, 'Schema.json')
IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _load_schema():
    if not os.path.exists(SCHEMA_FILE):
        return {}
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _is_safe_identifier(name):
    return bool(IDENTIFIER_RE.match(name))


def _quote_ident(name):
    if not _is_safe_identifier(name):
        raise ValueError(f'Unsafe identifier: {name}')
    return f'"{name}"'


def _table_exists(table_name):
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
        return cur.fetchone()[0]


def _parse_base_type(type_str):
    return type_str.split('(')[0].split()[0].strip().lower()


def _pk_field(fields):
    for field_name, type_str in fields.items():
        if '(pk)' in type_str:
            return field_name
    return None


def _build_input_meta(field_name, type_str):
    base_type = _parse_base_type(type_str)

    meta = {
        'name': field_name,
        'type_str': type_str,
        'base_type': base_type,
        'is_pk': '(pk)' in type_str,
        'is_fk': '(fk)' in type_str,
        'required': '(pk)' in type_str,
        'input_type': 'text',
        'step': None,
    }

    if base_type == 'int':
        meta['input_type'] = 'number'
        meta['step'] = '1'
    elif base_type == 'float':
        meta['input_type'] = 'number'
        meta['step'] = 'any'
    elif base_type == 'date':
        meta['input_type'] = 'date'
    elif base_type == 'bool':
        meta['input_type'] = 'checkbox'

    return meta


def _coerce_value(raw_value, type_str, from_csv=False):
    base_type = _parse_base_type(type_str)

    if base_type == 'bool':
        if from_csv:
            if raw_value in (None, ''):
                return False
            return str(raw_value).strip().lower() in ('1', 'true', 'yes', 'y', 'on')
        return raw_value in ('on', 'true', 'True', '1')

    if raw_value is None or raw_value == '':
        return None

    if base_type == 'int':
        return int(raw_value)
    if base_type == 'float':
        return float(raw_value)
    if base_type == 'date':
        return raw_value

    return raw_value


def _get_table_count(table_name):
    try:
        with connection.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM {_quote_ident(table_name)}')
            return cur.fetchone()[0]
    except Exception:
        return '—'


def _get_table_columns(table_name):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            [table_name],
        )
        return [row[0] for row in cur.fetchall()]


def _insert_row(table_name, table_fields, incoming_data, from_csv=False):
    columns = []
    values = []
    errors = []

    for field_name, type_str in table_fields.items():
        if _parse_base_type(type_str) == 'bool':
            raw_value = incoming_data.get(field_name)
        else:
            raw_value = incoming_data.get(field_name, '')
            if raw_value is not None:
                raw_value = str(raw_value).strip()

        if '(pk)' in type_str and (raw_value is None or raw_value == ''):
            errors.append(f'{field_name} is required.')
            continue

        try:
            coerced = _coerce_value(raw_value, type_str, from_csv=from_csv)
        except (ValueError, TypeError):
            errors.append(f'{field_name} must be a valid {_parse_base_type(type_str)}.')
            continue

        columns.append(field_name)
        values.append(coerced)

    if errors:
        return False, errors

    quoted_table = _quote_ident(table_name)
    quoted_columns = ', '.join(_quote_ident(col) for col in columns)
    placeholders = ', '.join(['%s'] * len(values))

    sql = f'INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({placeholders})'

    with connection.cursor() as cur:
        cur.execute(sql, values)

    return True, []


@login_required
def table_list(request):
    schema = _load_schema()

    table_info = []
    for table_name, fields in schema.items():
        exists = _table_exists(table_name)
        table_info.append({
            'table_name': table_name,
            'db_table': table_name,
            'field_count': len(fields),
            'row_count': _get_table_count(table_name) if exists else 'Not initialized',
            'exists': exists,
        })

    q = request.GET.get('q', '').strip().lower()
    if q:
        table_info = [
            t for t in table_info
            if q in t['table_name'].lower() or q in t['db_table'].lower()
        ]

    context = {
        'page_title': 'Datasets',
        'tables': table_info,
        'search_q': request.GET.get('q', '').strip(),
    }
    return render(request, 'datasets/list.html', context)


@login_required
def table_view(request, table_name):
    schema = _load_schema()

    if table_name not in schema:
        messages.error(request, 'Table not found in Schema.json.')
        return redirect('datasets:list')

    if not _table_exists(table_name):
        messages.error(request, f'Table "{table_name}" has not been initialized yet. Go to Schema Registry and click Initialize Database.')
        return redirect('datasets:list')

    try:
        columns = _get_table_columns(table_name)
        pk_name = _pk_field(schema[table_name])

        order_sql = f' ORDER BY {_quote_ident(pk_name)}' if pk_name else ''
        with connection.cursor() as cur:
            cur.execute(f'SELECT * FROM {_quote_ident(table_name)}{order_sql} LIMIT 500')
            raw_rows = cur.fetchall()

        rows = []
        pk_index = columns.index(pk_name) if pk_name in columns else None
        for row in raw_rows:
            rows.append({
                'cells': row,
                'pk': row[pk_index] if pk_index is not None else None,
            })

        context = {
            'page_title': table_name,
            'table_name': table_name,
            'fields': columns,
            'rows': rows,
            'total_count': _get_table_count(table_name),
            'pk_name': pk_name,
        }
        return render(request, 'datasets/table_view.html', context)

    except Exception as e:
        messages.error(request, f'Could not load table "{table_name}": {e}')
        return redirect('datasets:list')


@login_required
def table_add_entry(request, table_name):
    schema = _load_schema()

    if table_name not in schema:
        messages.error(request, 'Table not found in Schema.json.')
        return redirect('datasets:list')

    if not _table_exists(table_name):
        messages.error(request, f'Table "{table_name}" has not been initialized yet. Go to Schema Registry and click Initialize Database.')
        return redirect('datasets:list')

    table_fields = schema[table_name]
    field_meta = [_build_input_meta(field_name, type_str) for field_name, type_str in table_fields.items()]

    if request.method == 'POST':
        try:
            success, errors = _insert_row(table_name, table_fields, request.POST, from_csv=False)
            if success:
                messages.success(request, f'Entry added to {table_name}.')

                AuditLog.objects.create(
                    user=request.user,
                    action='add_entry',
                    model_name=table_name,
                    object_id='single',
                )
                return redirect('datasets:table_view', table_name=table_name)
            for error in errors:
                messages.error(request, error)
        except Exception as e:
            messages.error(request, f'Insert failed: {e}')

    context = {
        'page_title': f'Add Entry — {table_name}',
        'table_name': table_name,
        'fields': field_meta,
    }
    return render(request, 'datasets/table_add.html', context)


@login_required
def table_add_bulk(request, table_name):
    schema = _load_schema()

    if table_name not in schema:
        messages.error(request, 'Table not found in Schema.json.')
        return redirect('datasets:list')

    if not _table_exists(table_name):
        messages.error(request, f'Table "{table_name}" has not been initialized yet. Go to Schema Registry and click Initialize Database.')
        return redirect('datasets:list')

    table_fields = schema[table_name]
    expected_headers = list(table_fields.keys())

    # Build field metadata for the JS-driven editable table
    fields_meta = []
    for field_name, type_str in table_fields.items():
        fields_meta.append(_build_input_meta(field_name, type_str))

    if request.method == 'POST':
        # Handle JSON submission from the editable table
        bulk_data_raw = request.POST.get('bulk_data')
        if bulk_data_raw:
            try:
                rows_data = json.loads(bulk_data_raw)
                if not isinstance(rows_data, list):
                    messages.error(request, 'Invalid data format.')
                    return redirect('datasets:table_bulk', table_name=table_name)

                created = 0
                skipped = 0

                with transaction.atomic():
                    for idx, row in enumerate(rows_data, start=1):
                        # Only include known fields
                        normalized = {}
                        for field_name in table_fields:
                            if field_name in row:
                                normalized[field_name] = row[field_name]
                        try:
                            success, errors = _insert_row(table_name, table_fields, normalized, from_csv=True)
                            if success:
                                created += 1
                            else:
                                skipped += 1
                                messages.warning(request, f'Row {idx} skipped: {"; ".join(errors)}')
                        except Exception as e:
                            skipped += 1
                            messages.warning(request, f'Row {idx} skipped: {e}')

                if created:
                    messages.success(request, f'{created} row(s) added to {table_name}.')

                    AuditLog.objects.create(
                        user=request.user,
                        action='add_bulk',
                        model_name=table_name,
                        object_id=f'{created} rows',
                    )

                if skipped:
                    messages.warning(request, f'{skipped} row(s) were skipped.')

                return redirect('datasets:table_view', table_name=table_name)

            except json.JSONDecodeError:
                messages.error(request, 'Invalid JSON data.')
        else:
            messages.error(request, 'No data submitted.')

    context = {
        'page_title': f'Bulk Add — {table_name}',
        'table_name': table_name,
        'model_verbose': table_name,
        'expected_headers': expected_headers,
        'fields_meta_json': json.dumps(fields_meta),
    }
    return render(request, 'datasets/table_bulk.html', context)


@login_required
def table_delete_entry(request, table_name, pk):
    schema = _load_schema()

    if table_name not in schema:
        messages.error(request, 'Table not found in Schema.json.')
        return redirect('datasets:list')

    if not _table_exists(table_name):
        messages.error(request, f'Table "{table_name}" has not been initialized yet.')
        return redirect('datasets:list')

    pk_name = _pk_field(schema[table_name])
    if not pk_name:
        messages.error(request, f'No primary key found for {table_name}.')
        return redirect('datasets:table_view', table_name=table_name)

    try:
        with connection.cursor() as cur:
            cur.execute(
                f'DELETE FROM {_quote_ident(table_name)} WHERE {_quote_ident(pk_name)} = %s',
                [pk],
            )
        messages.success(request, f'Entry deleted from {table_name}.')

        AuditLog.objects.create(
            user=request.user,
            action='delete',
            model_name=table_name,
            object_id=str(pk),
        )
    except Exception as e:
        messages.error(request, f'Delete failed: {e}')

    return redirect('datasets:table_view', table_name=table_name)