#!/bin/bash
# =============================================================================
# Convenience wrapper to bring up the dev server.
# =============================================================================
# Applies any pending migrations, then runs Django's auto-reloading
# dev server on all interfaces so it's reachable from a Docker network.
# Not for production — use scripts/start-web.sh (Gunicorn) for that.
# =============================================================================
set -e

echo "Starting development server..."
poetry run python manage.py migrate
poetry run python manage.py runserver 0.0.0.0:8000
