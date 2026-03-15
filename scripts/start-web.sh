#!/bin/sh
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); username='admin'; password='admin123'; email='admin@example.com'; User.objects.filter(username=username).exists() or User.objects.create_superuser(username, email, password)"
exec gunicorn prism_site.wsgi:application --bind 0.0.0.0:8000 --reload
