# =============================================================================
# Core views: home dashboard, health check, and settings page.
# =============================================================================
# The dashboard counts live against the schema-driven tables (rather
# than a hard-coded list) so adding new tables to Schema.json is enough
# to grow the totals automatically.
# =============================================================================

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
import json
import os

from apps.schemas.models import SchemaAuditLog
from apps.core.models import AuditLog


def _load_schema_tables():
    # Read Schema.json from disk and return it as a dict of
    # {table_name: {column_name: type_str}}.
    # Returns an empty dict when the file is missing.
    schema_file = os.path.join(settings.BASE_DIR, 'Schema.json')
    if not os.path.exists(schema_file):
        return {}

    with open(schema_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def _is_safe_identifier(name):
    # Return True if `name` is a safe SQL identifier
    # (alphanumeric / underscore only, must start with a letter or "_").
    return name.replace('_', '').isalnum() and (name[0].isalpha() or name[0] == '_')


def _quote_ident(name):
    # Wrap a SQL identifier in double quotes after checking it is safe.
    # Raises ValueError on unsafe input so we never interpolate
    # attacker-controlled text into raw SQL.
    if not _is_safe_identifier(name):
        raise ValueError(f'Unsafe identifier: {name}')
    return f'"{name}"'


def _table_exists(table_name):
    # Return True if a table with this name exists in the public schema.
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


def _get_table_count(table_name):
    # Return COUNT(*) for the given table, or 0 if the query fails.
    try:
        with connection.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM {_quote_ident(table_name)}')
            return cur.fetchone()[0]
    except Exception:
        return 0


def home(request):
    # Render the home dashboard.
    #
    # - Surfaces a "session expired" banner if the user came back from
    #   an idle-timeout logout.
    # - Honours a stashed `post_login_redirect` so users land back where
    #   they came from after sign-in.
    # - Counts every schema table and the rows inside each one, plus
    #   shows the 10 most recent audit log entries.

    # Show the session-expired banner once if the session was flagged.
    if request.session.pop("session_expired", False):
        messages.warning(request, "Your session has expired. Please sign in again.")

    # If the user just logged in and we saved their intended destination,
    # bounce them there now (but never to "/" or to the current path —
    # that would loop forever).
    redirect_to = request.session.pop("post_login_redirect", None)
    if redirect_to and redirect_to != '/' and redirect_to != request.path:
        return redirect(redirect_to)

    schema_tables = _load_schema_tables()
    schema_table_count = len(schema_tables)

    # Sum row counts across every table that actually exists in the DB.
    # Tables listed in Schema.json but not yet initialised contribute 0.
    total_rows = 0
    for table_name in schema_tables.keys():
        if _table_exists(table_name):
            total_rows += _get_table_count(table_name)

    context = {
        'page_title': 'PRISM Dashboard',
        'recent_activity': AuditLog.objects.select_related('user')[:10],
        'schema_tables_count': schema_table_count,
        'total_rows_count': total_rows,
        'qaqc_status': 'Healthy',
    }
    return render(request, 'core/home.html', context)


def health(request):
    # Liveness / readiness probe.
    #
    # Returns 200 with {"status": "healthy"} when the database responds
    # to a trivial query, 503 with the error message otherwise.
    # Used by container orchestrators and uptime monitors.
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)


@login_required
def settings_view(request):
    # Render the per-user settings page.
    #
    # Shows the username, email, the OIDC-resolved PRISM roles, and the
    # project IDs the user has access to. Useful for debugging IdP claim
    # mapping when something seems off.
    context = {
        'page_title': 'Settings',
        'user_roles': getattr(request.user, 'prism_roles', []),
        'project_ids': getattr(request.user, 'project_ids', []),
    }
    return render(request, 'core/settings.html', context)
