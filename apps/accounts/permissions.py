# =============================================================================
# Permission helpers for role-based access control.
# =============================================================================
# A "guest" is a read-only user. Guests can view any page but cannot
# perform any write action (create, edit, delete, approve, initialize DB,
# CSV import, etc.).
#
# Guest membership is determined by either of two sources:
#   1. OIDC claim: "guest" appears in prism_roles (populated from Keycloak).
#   2. Django Group: user belongs to the local "guest" Group
#      (used when DISABLE_OIDC=True for local development).
# =============================================================================

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


# The role name we look for inside the OIDC `prism_roles` claim.
GUEST_ROLE_NAME = 'guest'

# The matching local Django Group name. Kept the same so the two
# sources of truth do not drift apart.
GUEST_GROUP_NAME = 'guest'


def user_is_guest(user) -> bool:
    # Return True if `user` is a read-only guest.
    #
    # Resolution order:
    #   1. Reject anonymous / unauthenticated users immediately.
    #   2. Treat Django superusers as full-access regardless of role
    #      claims, so an admin locked out of normal accounts can still
    #      operate the system.
    #   3. Check the OIDC `prism_roles` attribute (set on the user by
    #      OIDCClaimsMiddleware from the session).
    #   4. Fall back to local Django Group membership for non-OIDC
    #      dev setups (DISABLE_OIDC=True).
    if user is None or not getattr(user, 'is_authenticated', False):
        return False

    # Superusers are never treated as guests — admin always has full access.
    if getattr(user, 'is_superuser', False):
        return False

    # 1. Check OIDC-provided roles (set by OIDCClaimsMiddleware)
    roles = getattr(user, 'prism_roles', None) or []
    if GUEST_ROLE_NAME in roles:
        return True

    # 2. Fall back to Django Group (useful for local dev / non-OIDC)
    try:
        if user.groups.filter(name=GUEST_GROUP_NAME).exists():
            return True
    except Exception:
        # Anonymous users have no `.groups` manager — treat as non-guest here;
        # the outer @login_required handles the unauthenticated case.
        pass

    return False


def non_guest_required(view_func):
    # View decorator — blocks guest users from accessing write endpoints.
    #
    # If a guest hits a protected view, they are shown a message and
    # redirected back to the referring page (or home).
    #
    # Compose with @login_required like so:
    #
    #     @login_required
    #     @non_guest_required
    #     def my_write_view(request):
    #         ...
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if user_is_guest(request.user):
            messages.error(
                request,
                "Your account is read-only — this action requires a full user account.",
            )
            # Bounce back to where they came from, or home if there is no referer.
            fallback = request.META.get('HTTP_REFERER') or '/'
            return redirect(fallback)
        return view_func(request, *args, **kwargs)
    return _wrapped
