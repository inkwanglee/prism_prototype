# =============================================================================
# Middleware that re-attaches OIDC claims to request.user.
# =============================================================================
# The OIDC backend (PrismOIDCBackend.authenticate) stores `prism_roles`
# and `project_ids` claims on the session at login time. On every
# subsequent request this middleware copies them back onto request.user
# so view code and permission helpers can read them as plain attributes
# without having to poke the session directly.
# =============================================================================


class OIDCClaimsMiddleware:
    # Injects OIDC claims (prism_roles, project_ids) from the session
    # onto request.user on every request.

    def __init__(self, get_response):
        # Store the next handler in the middleware chain.
        self.get_response = get_response

    def __call__(self, request):
        # Attach session claims to request.user, then defer to the chain.
        if request.user.is_authenticated:
            request.user.prism_roles = request.session.get('prism_roles', [])
            request.user.project_ids = request.session.get('project_ids', [])
        response = self.get_response(request)
        return response
