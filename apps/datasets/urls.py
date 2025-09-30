from django.urls import path
from . import views

app_name = 'datasets'

urlpatterns = [
    path('', views.dataset_list, name='list'),
    path('create/', views.dataset_create, name='create'),
    path('<int:pk>/', views.dataset_detail, name='detail'),
]