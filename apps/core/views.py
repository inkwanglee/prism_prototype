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
    schema_file = os.path.join(settings.BASE_DIR, 'Schema.json')
    if not os.path.exists(schema_file):
        return {}

    with open(schema_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def _is_safe_identifier(name):
    return name.replace('_', '').isalnum() and (name[0].isalpha() or name[0] == '_')


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


def _get_table_count(table_name):
    try:
        with connection.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM {_quote_ident(table_name)}')
            return cur.fetchone()[0]
    except Exception:
        return 0


def home(request):
    """Home page with post-login redirect support."""
    if request.session.pop("session_expired", False):
        messages.warning(request, "Your session has expired. Please sign in again.")

    redirect_to = request.session.pop("post_login_redirect", None)
    if redirect_to and redirect_to != '/' and redirect_to != request.path:
        return redirect(redirect_to)

    schema_tables = _load_schema_tables()
    schema_table_count = len(schema_tables)

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
    """Health check endpoint."""
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
    """Settings page — shows user info, roles, and project scopes from IdP."""
    context = {
        'page_title': 'Settings',
        'user_roles': getattr(request.user, 'prism_roles', []),
        'project_ids': getattr(request.user, 'project_ids', []),
    }
    return render(request, 'core/settings.html', context)
