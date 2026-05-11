# =============================================================================
# Idle-timeout middleware.
# =============================================================================
# If an authenticated user goes more than SESSION_IDLE_TIMEOUT seconds
# (default 30 minutes) between requests, their next request is redirected
# to the logout view with `expired=1` so the UI can surface
# "your session expired" instead of silently kicking them out.
# =============================================================================

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


class IdleTimeoutMiddleware:
    # Expire authenticated sessions after a period of inactivity.

    def __init__(self, get_response):
        # Cache the configured timeout (in seconds).
        self.get_response = get_response
        self.timeout_seconds = getattr(settings, "SESSION_IDLE_TIMEOUT", 30 * 60)

    def __call__(self, request):
        # Check elapsed time since last activity and redirect to logout
        # when the limit is exceeded; otherwise refresh the activity
        # timestamp on the session and continue normally.
        print("IDLE MIDDLEWARE HIT:", request.path, request.user.is_authenticated)

        path = request.path

        # Skip auth-related paths so the logout / re-login round-trip
        # itself is never treated as idle activity.
        if path.startswith('/accounts/') or path.startswith('/oidc/'):
            return self.get_response(request)

        if request.user.is_authenticated:
            now_ts = int(timezone.now().timestamp())
            last_activity_ts = request.session.get("last_activity_ts")

            if last_activity_ts is not None:
                idle_for = now_ts - last_activity_ts

                # Debug print kept from the original implementation.
                print("IDLE CHECK:",
                      "path=", request.path,
                      "idle_for=", idle_for,
                      "timeout=", self.timeout_seconds)

                # If they have been inactive too long, send them through
                # logout with `expired=1` so the login page can explain
                # what happened, and `next=...` so they return to the
                # same URL after re-authenticating.
                if idle_for > self.timeout_seconds:
                    logout_url = reverse("accounts:logout")
                    target = f"{logout_url}?expired=1&next={request.path}"
                    print("IDLE TIMEOUT redirecting to:", target)
                    return redirect(f"{logout_url}?expired=1&next={request.path}")

            # Record this request as the latest activity timestamp.
            request.session["last_activity_ts"] = now_ts

        response = self.get_response(request)
        return response
