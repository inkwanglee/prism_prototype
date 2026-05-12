# =============================================================================
# URL routes for the QAQC app.
# =============================================================================

from django.urls import path
from . import views

app_name = 'qaqc'

urlpatterns = [
    # QAQC dashboard — list of recent runs.
    path('', views.qaqc_dashboard, name='dashboard'),
]
