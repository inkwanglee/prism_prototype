from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode

from mozilla_django_oidc.views import OIDCAuthenticationRequestView


def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')

    next_url = request.GET.get('next', '/')

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
    """Initiates OIDC auth flow, preserving the original URL."""
    next_url = request.GET.get('next', request.POST.get('next', '/'))
    reauth = request.GET.get('reauth') == '1'

    if next_url.startswith('/accounts/') or next_url.startswith('/oidc/'):
        next_url = '/'

    request.session['post_login_redirect'] = next_url
    request.session['force_reauth'] = reauth

    return redirect(reverse('accounts:oidc_start'))


class PrismOIDCAuthenticationRequestView(OIDCAuthenticationRequestView):
    """
    Custom OIDC start view.
    Adds prompt=login when timeout-based re-authentication is required.
    """
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        force_reauth = request.session.pop('force_reauth', False)

        if force_reauth and response.status_code in (301, 302):
            location = response['Location']
            sep = '&' if '?' in location else '?'
            response['Location'] = f'{location}{sep}{urlencode({"prompt": "login"})}'

        return response


def logout_view(request):
    """Logout — clears Django session and Keycloak session."""
    next_url = request.GET.get('next', '/')
    expired = request.GET.get('expired') == '1'

    print("LOGOUT VIEW URL:", request.get_full_path())
    print("LOGOUT VIEW expired raw:", request.GET.get('expired'))
    print("LOGOUT VIEW expired bool:", expired)

    if not getattr(settings, 'DISABLE_OIDC', True):
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