class OIDCClaimsMiddleware:
    """
    Injects OIDC claims (prism_roles, project_ids) from session
    into request.user on every request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user.prism_roles = request.session.get('prism_roles', [])
            request.user.project_ids = request.session.get('project_ids', [])
        response = self.get_response(request)
        return response
