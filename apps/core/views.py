from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def home(request):
    """Home page with post-login redirect support."""
    if request.session.pop("session_expired", False):
        messages.warning(request, "Your session has expired. Please sign in again.")

    redirect_to = request.session.pop("post_login_redirect", None)
    if redirect_to and redirect_to != '/' and redirect_to != request.path:
        return redirect(redirect_to)

    context = {
        'page_title': 'PRISM Dashboard',
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
