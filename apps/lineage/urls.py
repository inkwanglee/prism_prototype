# =============================================================================
# URL routes for the Lineage app.
# =============================================================================

from django.urls import path
from . import views

app_name = 'lineage'

urlpatterns = [
    # Lineage page — list of recent snapshots.
    path('', views.lineage_view, name='view'),
]
