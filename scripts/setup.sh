#!/bin/bash
set -e

echo "=== PRISM Setup Script ==="

# Poetry 설치 확인
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# 의존성 설치
echo "Installing dependencies..."
poetry install

# Docker Compose 실행
echo "Starting Docker services..."
docker compose up -d db redis minio keycloak

# 서비스가 준비될 때까지 대기
echo "Waiting for services to be ready..."
sleep 10

# 마이그레이션 실행
echo "Running migrations..."
poetry run python manage.py makemigrations
poetry run python manage.py migrate

# 슈퍼유저 생성 (존재하지 않을 경우)
echo "Creating superuser..."
poetry run python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Static 파일 수집
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