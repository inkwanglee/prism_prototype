from django.urls import path
from . import views

app_name = 'ingestion'

urlpatterns = [
    path('', views.ingestion_list, name='list'),
]