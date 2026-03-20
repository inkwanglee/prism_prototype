from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.urls import reverse


def login_view(request):
    """Login page — shows SSO button or redirects to admin login."""
    if request.user.is_authenticated:
        return redirect('/')

    next_url = request.GET.get('next', '/')

    if getattr(settings, 'DISABLE_OIDC', True):
        return redirect(f'/admin/login/?next={next_url}')

    return render(request, 'accounts/login.html', {
        'next': next_url,
        'page_title': 'Sign In',
        'debug': settings.DEBUG,
    })


def login_start(request):
    """Initiates OIDC auth flow, preserving the original URL."""
    next_url = request.GET.get('next', request.POST.get('next', '/'))

    if next_url.startswith('/accounts/') or next_url.startswith('/oidc/'):
        next_url = '/'

    request.session['post_login_redirect'] = next_url
    return redirect(reverse('oidc_authentication_init'))


def logout_view(request):
    """Logout — clears Django session and Keycloak session."""
    if not getattr(settings, 'DISABLE_OIDC', True):
        from apps.accounts.backends import provider_logout_url
        logout_url = provider_logout_url(request)
        auth_logout(request)
        return redirect(logout_url)
    else:
        auth_logout(request)
        messages.success(request, 'You have been logged out.')
        return redirect('/')
