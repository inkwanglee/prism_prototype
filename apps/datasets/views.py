from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import connection, transaction
import json
import os
import re

from apps.core.models import AuditLog
from apps.accounts.permissions import non_guest_required

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


def _is_auto_pk(type_str):
    """
    True if this column is a PK
    Primary keys are managed by the database
    This is a remanant of previous code removing may break something elsewhere
    """
    return '(pk)' in type_str

def _parse_fk_reference(type_str):
    """
    Parse FK reference from type string.
    e.g. 'int (fk to Company.CompanyID)' -> ('Company', 'CompanyID')
         'string (fk)' -> None  (unresolved FK, no dropdown)
    """
    match = re.search(r'\(fk\s+to\s+(\w+)\.(\w+)\)', type_str)
    if match:
        return match.group(1), match.group(2)
    return None

def _get_fk_options(ref_table, ref_column, schema):
    """
    Fetch available FK values from the referenced table.
    Returns a list of dicts: {'value': <pk_value>, 'label': '<display_text>'}.
    The label combines the PK with the first non-PK string column for readability.
    """
    if not _table_exists(ref_table):
        return []

    ref_fields = schema.get(ref_table, {})
    if not ref_fields:
        return []

    # Find a good display column: first non-PK string column in the ref table
    display_col = None
    found_pk = False
    for fname, ftype in ref_fields.items():
        if '(pk)' in ftype:
            found_pk = True
            continue
        if found_pk:
            display_col = fname
            break

    try:
        with connection.cursor() as cur:
            if display_col and _is_safe_identifier(display_col):
                cur.execute(
                    f'SELECT {_quote_ident(ref_column)}, {_quote_ident(display_col)} '
                    f'FROM {_quote_ident(ref_table)} '
                    f'ORDER BY {_quote_ident(display_col)} LIMIT 1000'
                )
                return [
                    {'value': row[0], 'label': f'{row[1]}' if row[1] else str(row[0])}
                    for row in cur.fetchall()
                ]
            else:
                cur.execute(
                    f'SELECT {_quote_ident(ref_column)} '
                    f'FROM {_quote_ident(ref_table)} '
                    f'ORDER BY {_quote_ident(ref_column)} LIMIT 1000'
                )
                return [
                    {'value': row[0], 'label': str(row[0])}
                    for row in cur.fetchall()
                ]
    except Exception:
        return []


def _build_input_meta(field_name, type_str, schema=None):
    base_type = _parse_base_type(type_str)
    is_pk = '(pk)' in type_str
    is_fk = '(fk' in type_str
    auto_generated = _is_auto_pk(type_str)

    fk_ref = _parse_fk_reference(type_str) if is_fk else None

    meta = {
        'name': field_name,
        'type_str': type_str,
        'base_type': base_type,
        'is_pk': is_pk,
        'is_fk': is_fk,
        'auto_generated': auto_generated,
        
        # Auto-generated PKs are NOT required on input (DB fills them)
        'required': not is_pk,
        'input_type': 'text',
        'step': None,
        'fk_options': [],
    }
    if fk_ref and schema:
        ref_table, ref_column = fk_ref
        meta['fk_options'] = _get_fk_options(ref_table, ref_column, schema)
        meta['fk_ref_table'] = ref_table
        meta['fk_ref_column'] = ref_column
        if meta['fk_options']:
            meta['input_type'] = 'select'
    if meta['input_type'] != 'select':
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
    """
    Insert one row into the given table.

    PK automation:
    - For auto-generated PK columns (int + pk), if no value was supplied
      we OMIT the column from the INSERT list so the DB sequence fills it.
    - If the caller *did* supply a value, we honour it (useful for CSV imports
      that carry pre-existing IDs).
    """
    columns = []
    values = []
    errors = []

    for field_name, type_str in table_fields.items():

        if _is_auto_pk(type_str): 
            continue

        if _parse_base_type(type_str) == 'bool':
            raw_value = incoming_data.get(field_name)
        else:
            raw_value = incoming_data.get(field_name, '')
            if raw_value is not None:
                raw_value = str(raw_value).strip()

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

    # Edge case: all columns were auto-generated / skipped. Use DEFAULT VALUES.
    if not columns:
        sql = f'INSERT INTO {quoted_table} DEFAULT VALUES'
        with connection.cursor() as cur:
            cur.execute(sql)
        return True, []

    sql = f'INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({placeholders})'
    with connection.cursor() as cur:
        cur.execute(sql, values)

    return True, []


# Update logic is similar to insert, but we always require the PK to identify the row,
def _get_row_by_pk(table_name, pk_name, pk):
    """
    Fetch one row from a schema-created database table by its primary key.

    Returns:
    - dict of column_name -> value if found
    - None if no matching row exists
    """
    columns = _get_table_columns(table_name)
    quoted_columns = ', '.join(_quote_ident(col) for col in columns)

    with connection.cursor() as cur:
        cur.execute(
            f'''
            SELECT {quoted_columns}
            FROM {_quote_ident(table_name)}
            WHERE {_quote_ident(pk_name)} = %s
            LIMIT 1
            ''',
            [pk],
        )
        row = cur.fetchone()

    if row is None:
        return None

    return dict(zip(columns, row))


def _update_row(table_name, table_fields, pk_name, pk, incoming_data):
    """
    Update one existing row in a schema-created database table.

    Important:
    - The PK is skipped so users cannot accidentally change the row identity.
    - Values are coerced using the same _coerce_value helper as Add Entry.
    - Table/column names still go through _quote_ident for safety.
    """
    set_columns = []
    values = []
    errors = []

    for field_name, type_str in table_fields.items():
        # Never edit the primary key.
        if field_name == pk_name:
            continue

        if _parse_base_type(type_str) == 'bool':
            raw_value = incoming_data.get(field_name)
        else:
            raw_value = incoming_data.get(field_name, '')
            if raw_value is not None:
                raw_value = str(raw_value).strip()

        try:
            coerced = _coerce_value(raw_value, type_str, from_csv=False)
        except (ValueError, TypeError):
            errors.append(f'{field_name} must be a valid {_parse_base_type(type_str)}.')
            continue

        set_columns.append(field_name)
        values.append(coerced)

    if errors:
        return False, errors

    if not set_columns:
        return False, ['There are no editable columns for this table.']

    assignments = ', '.join(
        f'{_quote_ident(col)} = %s'
        for col in set_columns
    )

    values.append(pk)

    with connection.cursor() as cur:
        cur.execute(
            f'''
            UPDATE {_quote_ident(table_name)}
            SET {assignments}
            WHERE {_quote_ident(pk_name)} = %s
            ''',
            values,
        )

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
@non_guest_required
def table_add_entry(request, table_name):
    schema = _load_schema()

    if table_name not in schema:
        messages.error(request, 'Table not found in Schema.json.')
        return redirect('datasets:list')

    if not _table_exists(table_name):
        messages.error(request, f'Table "{table_name}" has not been initialized yet. Go to Schema Registry and click Initialize Database.')
        return redirect('datasets:list')

    table_fields = schema[table_name]
    all_fields_meta = [_build_input_meta(n, t, schema=schema) for n, t in table_fields.items()]
    
    # Hide auto-generated PKs from the form entirely.
    visible_fields = [f for f in all_fields_meta if not f['auto_generated']]
    auto_pk_fields = [f['name'] for f in all_fields_meta if f['auto_generated']]

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
        'fields': visible_fields,
        'auto_pk_fields': auto_pk_fields,
    }
    return render(request, 'datasets/table_add.html', context)


@login_required
@non_guest_required
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

    fields_meta = [_build_input_meta(n, t, schema=schema)  for n, t in table_fields.items()]

    if request.method == 'POST':
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
@non_guest_required
def table_edit_entry(request, table_name, pk):
    schema = _load_schema()

    if table_name not in schema:
        messages.error(request, 'Table not found in Schema.json.')
        return redirect('datasets:list')

    if not _table_exists(table_name):
        messages.error(request, f'Table "{table_name}" has not been initialized yet.')
        return redirect('datasets:list')

    table_fields = schema[table_name]
    pk_name = _pk_field(table_fields)

    if not pk_name:
        messages.error(request, f'No primary key found for {table_name}.')
        return redirect('datasets:table_view', table_name=table_name)

    current_row = _get_row_by_pk(table_name, pk_name, pk)

    if current_row is None:
        messages.error(request, f'Entry {pk} was not found in {table_name}.')
        return redirect('datasets:table_view', table_name=table_name)

    all_fields_meta = [
        _build_input_meta(field_name, type_str, schema=schema)
        for field_name, type_str in table_fields.items()
    ]

    visible_fields = []

    for field in all_fields_meta:
        # Do not let users edit the primary key.
        if field['name'] == pk_name:
            continue

        field = field.copy()
        field['value'] = current_row.get(field['name'])
        visible_fields.append(field)

    if request.method == 'POST':
        try:
            success, errors = _update_row(
                table_name,
                table_fields,
                pk_name,
                pk,
                request.POST,
            )

            if success:
                messages.success(request, f'Entry updated in {table_name}.')
                AuditLog.objects.create(
                    user=request.user,
                    action='edit_entry',
                    model_name=table_name,
                    object_id=str(pk),
                )
                return redirect('datasets:table_view', table_name=table_name)

            for error in errors:
                messages.error(request, error)

        except Exception as e:
            messages.error(request, f'Update failed: {e}')

    context = {
        'page_title': f'Edit Entry — {table_name}',
        'table_name': table_name,
        'pk_name': pk_name,
        'pk_value': pk,
        'fields': visible_fields,
        'current_row': current_row,
    }

    return render(request, 'datasets/table_edit.html', context)

@login_required
@non_guest_required
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
