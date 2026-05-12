# =============================================================================
# OIDC authentication backend for PRISM
# =============================================================================
# Wraps mozilla_django_oidc.OIDCAuthenticationBackend so that:
#   - Keycloak claims are mapped onto Django's User model,
#   - PRISM-specific role and project claims are stashed on the user and
#     session so middleware can re-attach them on later requests, and
#   - the "guest" realm role is mirrored into a local Django Group so
#     permission checks still work when session claims are absent.
#
# Also exposes provider_logout_url, which constructs a Keycloak
# RP-initiated logout URL and is wired up via OIDC_OP_LOGOUT_URL_METHOD
# in settings.
# =============================================================================

import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from apps.accounts.permissions import GUEST_ROLE_NAME, GUEST_GROUP_NAME

logger = logging.getLogger(__name__)


class PrismOIDCBackend(OIDCAuthenticationBackend):
    # Custom OIDC backend for PRISM.
    # Maps Keycloak claims to the Django User model.

    def filter_users_by_claims(self, claims):
        # Find existing Django users that match the OIDC claims.
        # We match on email (case-insensitive). If there is no email
        # claim we refuse to guess and return an empty queryset so the
        # base class creates a fresh user.
        email = claims.get('email')
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(email__iexact=email)

    def create_user(self, claims):
        # Create a new Django user from OIDC claims and sync their roles.
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
        # Refresh name/email on an existing Django user and re-sync roles.
        user.first_name = claims.get('given_name', user.first_name)
        user.last_name = claims.get('family_name', user.last_name)
        user.email = claims.get('email', user.email)
        user.save()
        self._sync_roles(user, claims)
        logger.info(f"Updated OIDC user: {user.username}")
        return user

    def authenticate(self, request, **kwargs):
        # Defer to the parent OIDC flow and then stash PRISM-specific
        # claims (prism_roles, project_ids) on the session so subsequent
        # requests can re-attach them via OIDCClaimsMiddleware.
        user = super().authenticate(request, **kwargs)
        if user and request:
            request.session['prism_roles'] = getattr(user, 'prism_roles', [])
            request.session['project_ids'] = getattr(user, 'project_ids', [])
        return user

    def _sync_roles(self, user, claims):
        # Pull PRISM roles out of the OIDC claims and attach them to
        # the user object. Falls back to the standard realm_access.roles
        # list when the custom prism_roles claim mapper is not in use.
        prism_roles = claims.get('prism_roles', [])
        if not prism_roles:
            realm_access = claims.get('realm_access', {})
            prism_roles = realm_access.get('roles', [])
            # Drop Keycloak's built-in roles that we never care about
            # so downstream code only sees PRISM-specific roles.
            prism_roles = [
                r for r in prism_roles
                if r not in ('offline_access', 'uma_authorization', 'default-roles-prism')
            ]
        project_ids = claims.get('project_ids', [])
        user.prism_roles = prism_roles
        user.project_ids = project_ids

        # Mirror the "guest" role into a local Django Group so that
        # permissions checks still work even if session claims are missing
        # (e.g. after a server restart with sticky sessions).
        try:
            guest_group, _ = Group.objects.get_or_create(name=GUEST_GROUP_NAME)
            if GUEST_ROLE_NAME in prism_roles:
                user.groups.add(guest_group)
            else:
                user.groups.remove(guest_group)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Could not sync guest group for {user.username}: {exc}")


def provider_logout_url(request):
    # Build the Keycloak RP-Initiated Logout URL.
    #
    # - Carries the original `next` URL so the IdP bounces the user
    #   back to where they were after logout.
    # - Propagates an `expired=1` flag when the logout was triggered
    #   by idle timeout so the login page can show the right banner.
    # - Attaches the stored ID token as `id_token_hint` when available
    #   (required for silent logout by recent Keycloak versions).
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

    # If logout endpoint is missing from settings, just redirect
    # back to the login page (Django session has already been cleared
    # by the caller in views.logout_view).
    return redirect_url
