# PRISM Quick Start Guide (Thursday Demo)

## 1. Prerequisites (5 min)

```bash
# Check Docker is running
docker --version
docker compose version

# Check Poetry is installed (install if missing)
poetry --version
# If missing: curl -sSL https://install.python-poetry.org | python3 -
```

## 2. Project Setup (10 min)

```bash
# Move to the project folder
cd prism

# Grant execute permission
chmod +x scripts/*.sh

# Run the automated full setup
./scripts/setup.sh
```

This script performs the following automatically:
- Install Poetry dependencies
- Start Docker services (PostgreSQL, Redis, MinIO, Keycloak)
- Apply database migrations
- Create the superuser (admin/admin123)
- Collect static files

## 3. Start the Server (1 min)

### Option A: Simple dev server

```bash
poetry run python manage.py runserver
```

### Option B: Full stack via Docker Compose

```bash
docker compose up
```

## 4. Create Demo Data (1 min)

```bash
# In a new terminal
poetry run python scripts/create-demo-data.py
```

This script creates:
- A sample schema (drillhole.collar)
- A sample dataset
- A sample Ingestion Run
- A sample QAQC Run
- A sample Snapshot

## 5. Verify Access

Open these URLs in your browser:

### Main application
- Home: http://localhost:8000
- Login: http://localhost:8000/admin/
  - Username: `admin`
  - Password: `admin123`

### Key pages
- Schemas: http://localhost:8000/schemas/
- Datasets: http://localhost:8000/datasets/
- Ingestion: http://localhost:8000/ingestion/
- QAQC: http://localhost:8000/qaqc/
- Lineage: http://localhost:8000/lineage/

### API & Docs
- API Docs (Swagger): http://localhost:8000/api/schema/docs/
- ReDoc: http://localhost:8000/api/schema/redoc/
- Admin Panel: http://localhost:8000/admin/

### Infrastructure (optional)
- MinIO Console: http://localhost:9001 (minio/minio123)
- Keycloak: http://localhost:8080 (admin/admin)

## 6. Demo Scenarios

### Scenario 1: Create and manage a schema

1. **Log in**
   - Open http://localhost:8000/admin/
   - Sign in as admin / admin123

2. **View schemas**
   - Click "Schemas" in the left sidebar
   - Confirm the `drillhole.collar` schema that was seeded

3. **View schema details**
   - Click the schema to see its version information
   - Confirm v0.1.0 is in the Approved state

4. **Add a new version** (optional)
   - Click the "Add Version" button
   - Version: 0.2.0
