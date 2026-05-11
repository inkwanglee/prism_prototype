#!/bin/sh
# =============================================================================
# Production-style web container entrypoint.
# =============================================================================
# Used as the CMD in Dockerfile.web. Applies migrations, collects static
# files, ensures the admin superuser exists, and finally hands off to
# Gunicorn. --reload is kept on so code changes in mounted volumes pick
# up without a container restart during development.
# =============================================================================
set -e

echo "=== PRISM Web Server Starting ==="

# Apply any pending migrations on container boot. Safe to run repeatedly.
echo "Running migrations..."
python manage.py migrate --noinput

# Build the static bundle so WhiteNoise has something to serve.
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Ensure a superuser exists. Idempotent — only creates the account
# if it isn't already there.
echo "Ensuring admin user exists..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

# Hand off to Gunicorn. exec replaces the shell with Gunicorn so it
# becomes PID 1 and receives signals (SIGTERM on container stop) directly.
echo "=== Starting Gunicorn ==="
exec gunicorn prism_site.wsgi:application --bind 0.0.0.0:8000 --reload
