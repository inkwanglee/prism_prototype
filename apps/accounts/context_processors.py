# =============================================================================
# Template context processors for the accounts app.
# =============================================================================
# Exposes `is_guest` to every template so the UI can conditionally
# hide write actions (buttons, links) from read-only users.
# =============================================================================

from .permissions import user_is_guest


def user_context(request):
    # Inject `is_guest` into every template context.
    #
    # Registered in TEMPLATES.OPTIONS.context_processors so templates
    # can use `{% if not is_guest %}...{% endif %}` without each view
    # having to pass the flag through manually.
    user = getattr(request, 'user', None)
    return {
        'is_guest': user_is_guest(user),
    }
