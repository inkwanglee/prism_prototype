from django.urls import path
from . import views

app_name = 'datasets'

urlpatterns = [
    path('', views.table_list, name='list'),
    path('<str:table_name>/add/', views.table_add_entry, name='table_add'),
    path('<str:table_name>/bulk/', views.table_add_bulk, name='table_bulk'),
    path('<str:table_name>/edit/<str:pk>/', views.table_edit_entry, name='table_edit'),
    path('<str:table_name>/delete/<str:pk>/', views.table_delete_entry, name='table_delete'),
    path('<str:table_name>/', views.table_view, name='table_view'),
]