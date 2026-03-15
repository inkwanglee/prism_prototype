from django.shortcuts import redirect
from django.urls import reverse


def login_start(request):
    """
    Preserve the originally requested page, then start OIDC login.

    Example flow:
    /datasets/ -> /accounts/login/?next=/datasets/
               -> /oidc/authenticate/
               -> IdP login
               -> back to PRISM
               -> redirect to original page
    """
    next_url = request.GET.get("next", "/")

    # Avoid redirect loops
    if next_url.startswith("/accounts/login") or next_url.startswith("/oidc/"):
        next_url = "/"

    request.session["post_login_redirect"] = next_url

    return redirect(reverse("oidc_auth"))