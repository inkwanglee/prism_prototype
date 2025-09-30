from django.urls import path
from . import views

app_name = 'schemas'

urlpatterns = [
    path('', views.schema_list, name='list'),
    path('create/', views.schema_create, name='create'),
    path('<int:pk>/', views.schema_detail, name='detail'),
    path('<int:schema_pk>/version/create/', views.version_create, name='version_create'),
    path('version/<int:pk>/approve/', views.version_approve, name='version_approve'),
]