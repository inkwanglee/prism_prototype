from django.urls import path
from . import views

app_name = 'schemas'

urlpatterns = [
    path('', views.schema_list, name='list'),
    path('save/', views.save_schema, name='save_schema'),
    path('revert/<int:snapshot_id>/', views.revert_schema, name='revert_schema'),
    path('initialize/', views.initialize_db, name='initialize_db'),
    path('create/', views.schema_create, name='create'),
    path('<int:pk>/', views.schema_detail, name='detail'),
    path('<int:schema_pk>/version/create/', views.version_create, name='version_create'),
    path('version/<int:pk>/approve/', views.version_approve, name='version_approve'),
    path('create-from-csv/', views.create_schema_from_csv, name='create_from_csv'),
]
