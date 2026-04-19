import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from apps.accounts.permissions import GUEST_ROLE_NAME, GUEST_GROUP_NAME

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

        # Mirror the "guest" role into a local Django Group so that
        # permissions checks still work even if session claims are missing.
        try:
            guest_group, _ = Group.objects.get_or_create(name=GUEST_GROUP_NAME)
            if GUEST_ROLE_NAME in prism_roles:
                user.groups.add(guest_group)
            else:
                user.groups.remove(guest_group)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning(f"Could not sync guest group for {user.username}: {exc}")


def provider_logout_url(request):
    """Build Keycloak RP-Initiated Logout URL."""
    logout_endpoint = getattr(settings, 'OIDC_OP_LOGOUT_ENDPOINT', '')
    next_url = request.GET.get('next', '/')
    expired = request.GET.get('expired') == '1'

    login_redirect_path = f"/accounts/login/?next={quote(next_url, safe='/')}"
    if expired:
        login_redirect_path += "&expired=1"

    redirect_url = request.build_absolute_uri(login_redirect_path)
    id_token = request.session.get('oidc_id_token')

    if logout_endpoint:
        url = (
            f"{logout_endpoint}"
            f"?client_id={settings.OIDC_RP_CLIENT_ID}"
            f"&post_logout_redirect_uri={quote(redirect_url, safe=':/?=')}"
        )
        if id_token:
            url += f"&id_token_hint={quote(id_token, safe='._-')}"
        return url

    return redirect_url
