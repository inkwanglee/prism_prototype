# =============================================================================
# Account views: login landing page, login initiator, and logout.
# =============================================================================
# Most of the heavy lifting (token exchange, claim mapping) is done by
# mozilla_django_oidc; the views here just decide which page to show,
# build the right URLs, and clean up sessions on logout.
# =============================================================================

from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode

from mozilla_django_oidc.views import OIDCAuthenticationRequestView


def login_view(request):
    # Render the PRISM login landing page (the "Sign in with SSO" button).
    #
    # - Already-authenticated users are bounced to home.
    # - When OIDC is disabled (DISABLE_OIDC=True) we redirect to Django's
    #   built-in admin login so dev environments still work without Keycloak.
    # - Surfaces the `expired=1` flag from the URL as a banner so users
    #   know why they were logged out.
    if request.user.is_authenticated:
        return redirect('/')

    next_url = request.GET.get('next', '/')

    # Debug prints kept from the original implementation to aid local
    # troubleshooting of the expired-session banner flow.
    print("LOGIN PAGE URL:", request.get_full_path())
    print("expired param:", request.GET.get('expired'))
    print("session_expired:", request.GET.get('expired') == '1')

    session_expired = request.GET.get('expired') == '1'

    if getattr(settings, 'DISABLE_OIDC', True):
        return redirect(f'/admin/login/?next={next_url}')

    return render(request, 'accounts/login.html', {
        'next': next_url,
        'page_title': 'Sign In',
        'debug': settings.DEBUG,
        'session_expired': session_expired,
    })


def login_start(request):
    # Begin the OIDC authorisation flow.
    #
    # - Stores the original `next` URL on the session so the user lands
    #   back where they came from after the callback.
    # - When `reauth=1` is set we also flag the session so the OIDC start
    #   view appends `prompt=login` and forces the IdP to re-authenticate
    #   even if a Keycloak session already exists.
    next_url = request.GET.get('next', request.POST.get('next', '/'))
    reauth = request.GET.get('reauth') == '1'

    # Guard against redirect loops: never come back to a login URL.
    if next_url.startswith('/accounts/') or next_url.startswith('/oidc/'):
        next_url = '/'

    request.session['post_login_redirect'] = next_url
    request.session['force_reauth'] = reauth

    return redirect(reverse('accounts:oidc_start'))


class PrismOIDCAuthenticationRequestView(OIDCAuthenticationRequestView):
    # Custom OIDC start view.
    # Adds prompt=login when timeout-based re-authentication is required.

    def get(self, request, *args, **kwargs):
        # Defer to the parent, then append `prompt=login` when forced.
        response = super().get(request, *args, **kwargs)

        # Pop the flag so it only applies to this one redirect.
        force_reauth = request.session.pop('force_reauth', False)

        if force_reauth and response.status_code in (301, 302):
            location = response['Location']
            sep = '&' if '?' in location else '?'
            response['Location'] = f'{location}{sep}{urlencode({"prompt": "login"})}'

        return response


def logout_view(request):
    # Log the user out of both Django and Keycloak.
    #
    # When OIDC is enabled we first build the RP-initiated logout URL
    # via provider_logout_url, then end the Django session, then redirect
    # to Keycloak so it can also clear its own session and bounce the
    # browser back to our login page.
    #
    # When OIDC is disabled this just ends the Django session and
    # surfaces an "expired" or "logged out" flash message.
    next_url = request.GET.get('next', '/')
    expired = request.GET.get('expired') == '1'

    # Debug prints kept from the original implementation.
    print("LOGOUT VIEW URL:", request.get_full_path())
    print("LOGOUT VIEW expired raw:", request.GET.get('expired'))
    print("LOGOUT VIEW expired bool:", expired)

    if not getattr(settings, 'DISABLE_OIDC', True):
        # Imported here to avoid a circular import at module load time.
        from apps.accounts.backends import provider_logout_url
        logout_url = provider_logout_url(request)
        auth_logout(request)
        return redirect(logout_url)

    auth_logout(request)
    if expired:
        messages.warning(request, 'Your session expired due to inactivity.')
        return redirect(f'/accounts/login/?next={next_url}&expired=1')

    messages.success(request, 'You have been logged out.')
    return redirect(f'/accounts/login/?next={next_url}')
