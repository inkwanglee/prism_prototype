from django.urls import path
from . import views

app_name = 'lineage'

urlpatterns = [
    path('', views.lineage_view, name='view'),
]