from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect
from django.utils import timezone


class IdleTimeoutMiddleware:
    """
    Expire authenticated sessions after a period of inactivity.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_seconds = getattr(settings, "SESSION_IDLE_TIMEOUT", 30 * 60)

    def __call__(self, request):
        if request.user.is_authenticated:
            now_ts = int(timezone.now().timestamp())
            last_activity_ts = request.session.get("last_activity_ts")

            if last_activity_ts is not None:
                idle_for = now_ts - last_activity_ts
                if idle_for > self.timeout_seconds:
                    auth.logout(request)
                    request.session.flush()

                    request.session["session_expired"] = True

                    login_url = settings.LOGIN_URL
                    return redirect(f"{login_url}?next={request.path}")

            request.session["last_activity_ts"] = now_ts

        response = self.get_response(request)
        return response