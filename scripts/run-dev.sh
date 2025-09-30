#!/bin/bash
set -e

echo "Starting development server..."
poetry run python manage.py migrate
poetry run python manage.py runserver 0.0.0.0:8000