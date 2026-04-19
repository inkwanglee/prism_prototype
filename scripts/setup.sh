#!/bin/bash
set -e

echo "=== PRISM Setup Script ==="

# Check Poetry installation
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
echo "Installing dependencies..."
poetry install

# Start Docker Compose services
echo "Starting Docker services..."
docker compose up -d db redis minio keycloak

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run migrations
echo "Running migrations..."
poetry run python manage.py makemigrations
poetry run python manage.py migrate

# Create superuser (only if one does not already exist)
echo "Creating superuser..."
poetry run python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Collect static files
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
