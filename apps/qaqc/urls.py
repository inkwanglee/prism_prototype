from django.urls import path
from . import views

app_name = 'qaqc'

urlpatterns = [
    path('', views.qaqc_dashboard, name='dashboard'),
]