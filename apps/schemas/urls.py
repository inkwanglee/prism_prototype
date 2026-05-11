# =============================================================================
# URL routes for the Schemas app.
# =============================================================================

from django.urls import path
from . import views

app_name = 'schemas'

urlpatterns = [
    # Schema Registry page — editor, revert panel, CSV forms, Keycloak shortcut.
    path('', views.schema_list, name='list'),
    # POST: save the textarea contents to Schema.json + record a snapshot.
    path('save/', views.save_schema, name='save_schema'),
    # GET: stage a snapshot's content in the session so the next render
    # of the Schemas page pre-fills the editor with it.
    path('revert/<int:snapshot_id>/', views.revert_schema, name='revert_schema'),
    # POST: run CREATE TABLE IF NOT EXISTS for every entry in Schema.json.
    path('initialize/', views.initialize_db, name='initialize_db'),
    # Legacy Schema-record CRUD (predates the Schema.json editor).
    path('create/', views.schema_create, name='create'),
    path('<int:pk>/', views.schema_detail, name='detail'),
    path('<int:schema_pk>/version/create/', views.version_create, name='version_create'),
    path('version/<int:pk>/approve/', views.version_approve, name='version_approve'),
    # CSV-driven schema creation (Tappei): infers types from a CSV file
    # and creates both the Schema.json entry and the matching DB table.
    path('create-from-csv/', views.create_schema_from_csv, name='create_from_csv'),
    # Delete a schema entry by table name — also drops the DB table.
    path('delete-table/', views.delete_schema_table, name='delete_schema_table'),
]
