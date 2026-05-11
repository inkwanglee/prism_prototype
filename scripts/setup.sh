#!/bin/bash
# =============================================================================
# PRISM one-shot local setup.
# =============================================================================
# Installs Python dependencies, brings up the support containers
# (Postgres, Redis, MinIO, Keycloak), applies migrations, ensures the
# admin superuser exists, and collects static files.
#
# Run once on a fresh checkout, or any time you want to reset the local
# environment. After running, start the web server with either:
#     poetry run python manage.py runserver
#     docker compose up
# =============================================================================
set -e

echo "=== PRISM Setup Script ==="

# Install Poetry if it's missing — the rest of this script assumes it.
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install Python dependencies from pyproject.toml / poetry.lock.
echo "Installing dependencies..."
poetry install

# Bring up the support services in the background. Note: we deliberately
# do NOT start `web` here — the developer chooses whether to run it
# inside Docker (`docker compose up`) or directly via `runserver`.
echo "Starting Docker services..."
docker compose up -d db redis minio keycloak

# Give the containers a moment to finish their first-boot work
# (Postgres init, Keycloak realm import, etc.).
echo "Waiting for services to be ready..."
sleep 10

# Apply Django migrations against the freshly-started Postgres.
echo "Running migrations..."
poetry run python manage.py makemigrations
poetry run python manage.py migrate

# Ensure a superuser exists so the operator can reach /admin/.
# This is idempotent — re-running won't create duplicates.
echo "Creating superuser..."
poetry run python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Pre-build the static bundle so WhiteNoise has something to serve.
echo "Collecting static files..."
poetry run python manage.py collectstatic --noinput

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "To start the development server:"
echo "  poetry run python manage.py runserver"
echo ""
echo "Or start all services with Docker Compose:"
echo "  docker compose up"
echo ""
echo "Access the application at: http://localhost:8000"
echo "Admin login: admin / admin123"
echo "API docs: http://localhost:8000/api/schema/docs/"
echo ""
