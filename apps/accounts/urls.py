from django.urls import path
from .views import login_start

app_name = "accounts"

urlpatterns = [
    path("login/", login_start, name="login"),
]