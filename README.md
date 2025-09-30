# PRISM - Platform for Resource Intelligence & Subsurface Management

Sprint 1 MVP Implementation - Django-based Geological Data Management Platform

## Key Features

### Implemented Features (Sprint 1)

- **Authentication System**: Django built-in authentication (OIDC can be disabled in development)
- **Schema Registry**: JSON Schema-based data schema management
  - Schema creation and version management
  - Version-specific approval workflow
  - JSON Schema validation
- **Dataset Catalog**: Dataset registration and management
  - Schema reference-based datasets
  - Filtering and search capabilities
- **Ingestion**: Data collection job tracking (basic structure)
- **QAQC**: Quality assurance dashboard (basic structure)
- **Lineage**: Data lineage tracking (basic structure)
- **REST API**: OpenAPI documented API
- **Admin Panel**: Data management through Django Admin

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Poetry (Python package manager)

### Quick Start

```bash
# 1. Clone the repository
git clone <your-repo>
cd prism

# 2. Install dependencies and setup
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Start development server
poetry run python manage.py runserver

# Or start all services with Docker Compose
docker compose up
```

### Access Information

- **Web Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/
  - Username: `admin`
  - Password: `admin123`
- **API Documentation**: http://localhost:8000/api/schema/docs/
- **Keycloak Admin**: http://localhost:8080 (admin/admin)
- **MinIO Console**: http://localhost:9001 (minio/minio123)

### Creating Demo Data

```bash
poetry run python scripts/create-demo-data.py
```

## Project Structure

```
prism/
├── manage.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.dev
├── prism_site/           # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/                 # Django applications
│   ├── core/            # Core functionality (home, health check)
│   ├── accounts/        # User authentication
│   ├── schemas/         # Schema registry
│   ├── datasets/        # Dataset catalog
│   ├── ingestion/       # Data ingestion
│   ├── qaqc/           # Quality assurance
│   └── lineage/        # Data lineage
├── templates/           # HTML templates
├── static/             # Static files
└── scripts/            # Utility scripts
```

## Development Workflow

### Creating and Applying Migrations

```bash
poetry run python manage.py makemigrations
poetry run python manage.py migrate
```

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black .
poetry run isort .
poetry run flake8 .
```

### Starting Celery Worker

```bash
poetry run celery -A prism_site worker -l info
```

## API Usage Examples

### Register a Schema

```bash
curl -X POST http://localhost:8000/api/schemas/ \
  -H "Content-Type: application/json" \
  -d '{
    "key": "drillhole.assay",
    "owner": "Exploration Team",
    "description": "Assay results schema"
  }'
```

### Validate Payload

```bash
curl -X POST http://localhost:8000/api/schemas/validate/ \
  -H "Content-Type: application/json" \
  -d '{
    "schema_ref": "drillhole.collar@0.1.0",
    "payload": {
      "hole_id": "DH001",
      "x": 123.45,
      "y": 678.90,
      "z": 100.0
    }
  }'
```

## Environment Variables

Configure the following environment variables in the `.env.dev` file:

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True

# Database
DATABASE_URL=postgres://prism:prism@localhost:5432/prism

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio123

# OIDC (optional)
DISABLE_OIDC=True
OIDC_ISSUER=http://keycloak:8080/realms/prism
OIDC_CLIENT_ID=prism-web
OIDC_CLIENT_SECRET=devsecret
```

## Thursday Demo Preparation Checklist

- [x] Docker Compose configuration
- [x] Django project basic structure
- [x] User authentication (development mode)
- [x] Schema registry CRUD
- [x] Dataset catalog CRUD
- [x] Bootstrap 5 UI
- [x] REST API with OpenAPI
- [x] Admin panel
- [x] Demo data generation script
- [ ] Presentation materials

## Next Steps (Sprint 2+)

- JSON Schema compatibility checking
- Drillhole data model implementation
- CSV import functionality
- QAQC validation logic
- Real-time dashboards

## Troubleshooting

### Port Conflicts

```bash
# Check ports in use
lsof -i :8000
lsof -i :5432

# Restart Docker containers
docker compose down
docker compose up -d
```

### Database Reset

```bash
docker compose down -v
docker compose up -d db
poetry run python manage.py migrate
```

### Static Files Issues

```bash
poetry run python manage.py collectstatic --clear --noinput
```

## License

This project is part of an IT Capstone project.

## Team

- Project team members...

## References

- Django Documentation: https://docs.djangoproject.com/
- DRF Documentation: https://www.django-rest-framework.org/
- JSON Schema: https://json-schema.org/
