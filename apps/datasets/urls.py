# =============================================================================
# URL routes for the Datasets app.
# =============================================================================
# NOTE: the per-table routes ("<str:table_name>/...") must come BEFORE
# the catch-all `<str:table_name>/` so Django doesn't match e.g. "/add/"
# as a table name.
# =============================================================================

from django.urls import path
from . import views

app_name = 'datasets'

urlpatterns = [
    # Datasets index — lists every table declared in Schema.json.
    path('', views.table_list, name='list'),
    # Single-row add form.
    path('<str:table_name>/add/', views.table_add_entry, name='table_add'),
    # CSV upload + in-browser editor + bulk insert.
    path('<str:table_name>/bulk/', views.table_add_bulk, name='table_bulk'),
    # Edit one row by primary key.
    path('<str:table_name>/edit/<str:pk>/', views.table_edit_entry, name='table_edit'),
    # Delete one row by primary key (POST).
    path('<str:table_name>/delete/<str:pk>/', views.table_delete_entry, name='table_delete'),
    # Read-only table view — keep last so /add/ etc. match first.
    path('<str:table_name>/', views.table_view, name='table_view'),
]
