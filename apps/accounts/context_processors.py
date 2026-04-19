"""
Template context processors for the accounts app.

Exposes `is_guest` to every template so the UI can conditionally
hide write actions (buttons, links) from read-only users.
"""
from .permissions import user_is_guest


def user_context(request):
    user = getattr(request, 'user', None)
    return {
        'is_guest': user_is_guest(user),
    }
