from django.urls import path
from . import views

app_name = 'datasets'

urlpatterns = [
    path('', views.table_list, name='list'),
    path('<str:app_label>/<str:model_name>/', views.table_view, name='table_view'),
    path('<str:app_label>/<str:model_name>/add/', views.table_add_entry, name='table_add'),
    path('<str:app_label>/<str:model_name>/bulk/', views.table_add_bulk, name='table_bulk'),
    path('<str:app_label>/<str:model_name>/delete/<int:pk>/', views.table_delete_entry, name='table_delete'),
]
