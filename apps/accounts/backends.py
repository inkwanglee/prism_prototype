import logging
from django.conf import settings
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


class PrismOIDCBackend(OIDCAuthenticationBackend):
    """
    Custom OIDC backend for PRISM.
    Maps Keycloak claims to Django User model.
    """

    def filter_users_by_claims(self, claims):
        email = claims.get('email')
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(email__iexact=email)

    def create_user(self, claims):
        email = claims.get('email', '')
        username = claims.get('preferred_username', email)

        user = self.UserModel.objects.create_user(
            username=username,
            email=email,
            first_name=claims.get('given_name', ''),
            last_name=claims.get('family_name', ''),
        )
        logger.info(f"Created new OIDC user: {username} ({email})")
        self._sync_roles(user, claims)
        return user

    def update_user(self, user, claims):
        user.first_name = claims.get('given_name', user.first_name)
        user.last_name = claims.get('family_name', user.last_name)
        user.email = claims.get('email', user.email)
        user.save()
        self._sync_roles(user, claims)
        logger.info(f"Updated OIDC user: {user.username}")
        return user

    def authenticate(self, request, **kwargs):
        user = super().authenticate(request, **kwargs)
        if user and request:
            request.session['prism_roles'] = getattr(user, 'prism_roles', [])
            request.session['project_ids'] = getattr(user, 'project_ids', [])
        return user

    def _sync_roles(self, user, claims):
        prism_roles = claims.get('prism_roles', [])
        if not prism_roles:
            realm_access = claims.get('realm_access', {})
            prism_roles = realm_access.get('roles', [])
            prism_roles = [
                r for r in prism_roles
                if r not in ('offline_access', 'uma_authorization', 'default-roles-prism')
            ]
        project_ids = claims.get('project_ids', [])
        user.prism_roles = prism_roles
        user.project_ids = project_ids


def provider_logout_url(request):
    """Build Keycloak RP-Initiated Logout URL."""
    logout_endpoint = getattr(settings, 'OIDC_OP_LOGOUT_ENDPOINT', '')
    redirect_url = request.build_absolute_uri(settings.LOGOUT_REDIRECT_URL)
    if logout_endpoint:
        return (
            f"{logout_endpoint}"
            f"?client_id={settings.OIDC_RP_CLIENT_ID}"
            f"&post_logout_redirect_uri={redirect_url}"
        )
    return redirect_url
