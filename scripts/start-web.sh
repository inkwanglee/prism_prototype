#!/bin/sh
set -e

echo "=== PRISM Web Server Starting ==="

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if not exists
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

echo "=== Starting Gunicorn ==="
exec gunicorn prism_site.wsgi:application --bind 0.0.0.0:8000 --reload
