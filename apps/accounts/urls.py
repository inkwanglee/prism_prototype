from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('login/start/', views.login_start, name='login_start'),
    path('logout/', views.logout_view, name='logout'),
]
