# =============================================================================
# URL routes for the core app (dashboard, health check, settings).
# =============================================================================

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Home dashboard — schema table count, total row count, recent activity.
    path('', views.home, name='home'),
    # Liveness/readiness probe used by container orchestrators.
    path('healthz/', views.health, name='health'),
    # Per-user settings (roles, project scopes, links to API docs/admin).
    path('settings/', views.settings_view, name='settings'),
]
