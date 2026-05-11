# =============================================================================
# URL routes for the accounts app (login, logout, OIDC start).
# =============================================================================

from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # Landing page with the "Sign in with SSO" button.
    path('login/', views.login_view, name='login'),
    # POST-able starter that stashes `next` on the session before kicking
    # off the OIDC redirect (separate from the mozilla_django_oidc default
    # so we can apply our own `prompt=login` handling for forced reauth).
    path('login/start/', views.login_start, name='login_start'),
    # The actual OIDC authorisation redirect (subclasses the mozilla view).
    path('login/oidc-start/', views.PrismOIDCAuthenticationRequestView.as_view(), name='oidc_start'),
    # Logout — clears both Django and Keycloak sessions.
    path('logout/', views.logout_view, name='logout'),
]
