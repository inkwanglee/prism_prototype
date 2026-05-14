# PRISM — Platform for Resource Intelligence & Subsurface Management

**Sprint 3 – Sprint 7 (March 2026 – May 2026)**

A Django-based geological data management platform built for the resources sector. PRISM is the foundation layer of a broader two-database strategy: it handles **ExploreDB** workloads — the messy, heterogeneous, research and evaluation side of mining data — including spatial datasets, drillhole assays, schema management, and collaborative curation.

---

## PROJECT OVERVIEW

The project scope for this iteration covered:

* **Schema Registry** — a Schema.json-driven control surface where authorised users can edit, save, version, and revert the data model that backs every dataset table.
* **Dataset Catalog** — browsable views over the schema-defined tables with single-row Add, Edit, Delete, and Bulk CSV import paths.
* **Auto-generated primary keys** for `int (pk)` columns (Postgres `SERIAL` / SQLite `AUTOINCREMENT`) so users never input IDs manually.
* **SSO via Keycloak (OIDC)** with seven functional roles plus a read-only **guest** role enforced by `@non_guest_required` and an `is_guest` template flag.
* **CSV-based schema creation and deletion** so new tables can be onboarded without code changes.
* **Schema snapshots and non-destructive revert** so accidental schema edits can be recovered safely.

### Links

* **Demo Video:** https://drive.google.com/file/d/13PUaUarc4zoKteDFv9T4iw5XZdLXwKfg/view?usp=sharing 
* **Notion workspace:** https://www.notion.so/orefox/Prism-25b05cef1f2280ebab83de2bdebbec02  
* **Repository:** https://github.com/inkwanglee/prism_prototype
* **Cloud URL:** https://prism-web.kindground-d178727f.australiaeast.azurecontainerapps.io 
* **Test Cases:** https://docs.google.com/spreadsheets/d/1Nc87LbowZB4dYl9EoC4_D88mOq23Wlm3/edit?usp=sharing&ouid=100433973355983979823&rtpof=true&sd=true 
* **Sprint Roster:** https://docs.google.com/spreadsheets/d/1F-YgqsAQ5ITRycCF53103KPKFlSbhjrb4-fefcK9GJg/edit?gid=0#gid=0 




---

## SET UP INSTRUCTIONS

### Project structure

PRISM uses Django's **multi-app** layout rather than the single-app structure shown in the handover template. Each functional area is its own Django app, so future teams can extend one without touching the others.

```
prism_prototype/
├── manage.py
├── docker-compose.yml
├── Dockerfile, Dockerfile.web, Dockerfile.keycloak
├── pyproject.toml              # Poetry dependencies (acts as the requirements file)
├── .env.dev                    # Development environment variables
├── Schema.json                 # Source of truth for all dataset tables
├── prism_site/                 # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/                       # Functional apps
│   ├── core/                   # Home dashboard, health check, audit log
│   ├── accounts/               # OIDC backend, guest permissions, login
│   ├── schemas/                # Schema.json editor, snapshots, CSV create
│   ├── datasets/               # Browse, add, edit, delete dataset rows
│   ├── qaqc/                   # Quality-assurance dashboards (skeleton)
│   └── lineage/                # Data lineage view (skeleton)
├── templates/                  # HTML templates, one folder per app
├── static/                     # CSS, JS, images
├── keycloak/
│   └── prism-realm.json        # Realm import — roles, users, OIDC client
└── scripts/                    # setup.sh, start-web.sh, create-demo-data.py
```

### Additional packages

All Python dependencies are pinned in `pyproject.toml` (Poetry). Notable additions beyond a stock Django install:

| Package | Why |
|---|---|
| `mozilla-django-oidc` | Keycloak SSO integration |
| `python-jose[cryptography]` | JWT signing / verification used by the OIDC backend |
| `psycopg[binary]` | PostgreSQL driver |
| `django-redis`, `redis`, `celery` | Cache, broker, and async task workers |
| `django-environ` | `.env` file loader |
| `whitenoise` | Static file serving in containers |
| `drf-spectacular`, `drf-spectacular-sidecar` | OpenAPI schema + Swagger UI |
| `django-htmx`, `django-prometheus` | Progressive enhancement and Prometheus metrics |
| `crispy-bootstrap5`, `django-crispy-forms` | Bootstrap 5 form rendering |
| `jsonschema`, `semver` | Schema version validation |
| `pandas`, `numpy`, `scipy` | Tabular and numeric processing |
| `paramiko` | SFTP client (reserved for future LIMS connector) |
| `reportlab` | PDF generation (reserved for future report packs) |

### Installation procedure

**Installation procedure same as before** — the project ships with `docker-compose.yml` and a `scripts/setup.sh` bootstrapper, so the whole stack (web, database, Redis, MinIO, Keycloak) comes up with a single command. The long-form walk-through is in `QUICKSTART.md` in the repo root.

In short:

```bash
git clone https://github.com/inkwanglee/prism_prototype.git
cd prism_prototype
docker compose up --build       # First time, or after pulling new code
```

Once the containers report healthy:

| Service | URL | Credentials |
|---|---|---|
| Web app | http://localhost:8000 | sign in via Keycloak |
| Keycloak admin | http://localhost:8080/admin/ | admin / admin |
| MinIO console | http://localhost:9001/ | minio / minio123 |
| API docs | http://localhost:8000/api/schema/docs/ | (after sign-in) |

Three Keycloak users are seeded by `keycloak/prism-realm.json`:

| Username | Password | Role | Notes |
|---|---|---|---|
| `orefox1` | `test1234` | `data_steward` | Full access |
| `orefox2` | `test1234` | `data_steward` | Full access |
| `guest` | `guest123` | `guest` | Read-only |

### Common installation errors

| Symptom | Cause / fix |
|---|---|
| `port is already allocated` on `docker compose up` | Stop any local Postgres / Redis / Keycloak running on host ports 5432 / 6379 / 8080. |
| Login loops back to Keycloak | The `OIDC_ISSUER` URL inside the web container doesn't match the one your browser hits. Check both `OIDC_ISSUER` (browser-facing) and `OIDC_ISSUER_INTERNAL` (Docker-internal) in `docker-compose.yml`. |
| Old realm users still appear after seeding new ones | Realm import only runs on first start. Wipe the Keycloak volume with `docker compose down -v` and bring the stack back up. |
| New Django migrations not applied | `docker compose exec web python manage.py migrate` then `docker compose restart web`. |
| "Schema.json not found" on Initialize Database | Save the editor contents once (Schemas page → Save) before clicking Initialize. |

---

## IMPORTANT NOTES

### Changes to existing code

The most significant changes this team introduced beyond the original Sprint 1 scaffold:

* **Schema-driven dynamic tables.** `apps/datasets/views.py` and `apps/schemas/views.py` issue raw SQL against tables declared in `Schema.json`, so adding or removing entries in that file flows straight through to the database (after Initialize Database). All raw SQL goes through `_quote_ident` to prevent SQL injection through table or column names.
* **Auto-increment primary keys.** `int (pk)` columns become `SERIAL PRIMARY KEY` on Postgres / `INTEGER PRIMARY KEY AUTOINCREMENT` on SQLite. The Add Entry form hides these columns entirely so users can't fight the database for the next ID.
* **Guest role infrastructure.** A reusable `@non_guest_required` decorator plus an `is_guest` template flag, both backed by Keycloak claims with a Django Group fallback for non-OIDC dev setups.
* **Schema snapshot / revert.** Every Save records a `SchemaSnapshot` row when content changes. Reverts are non-destructive — they stage content in the user's session until a fresh Save is clicked.
* **Keycloak admin shortcut.** A header button on the Schemas page opens the Keycloak admin console in a new tab; the URL is derived dynamically from `OIDC_ISSUER` so it works across local, staging, and production.
* **CSV-driven schema creation and deletion.** Upload any CSV on the Schemas page to infer column types and create both the Schema.json entry and the matching DB table; the delete form drops both together.
* **Edit-row UI for dataset tables.** `apps/datasets/views.py:table_edit_entry` plus the matching template let users update individual rows via the same input metadata (`_build_input_meta`) used by Add Entry.

### Incomplete components

These exist as scaffolds for the next team to flesh out:

* **`apps/qaqc/`** — model and dashboard skeleton only. The next team is expected to implement the actual data quality checks (negative values, interval sanity, overlap detection, standards z-scores) and wire them into the ingestion pipeline.
* **`apps/lineage/`** — `Snapshot` and `LineageEdge` models exist but nothing emits edges automatically. The full lineage graph UI (upstream / downstream traversal, snapshot diffing) is unbuilt.
* **`apps/ingestion/`** — files remain in the repo but the app is **NOT** in `INSTALLED_APPS` and has no URL route. Treat it as dead code; remove or reactivate as needed.
* **API endpoints under `/api/schemas/` and `/api/datasets/`** — OpenAPI-documented but only minimally exercised. Tests and pagination polish are still owed.
* **Demo data script** — `scripts/create-demo-data.py` seeds the legacy `Schema` / `SchemaVersion` models but does NOT populate the dynamic Schema.json-driven tables. A future team should add a flag to seed sample collars / assays for end-to-end demos.

### Important information for the next team

1. **Schema.json is the source of truth.** Add a column to the JSON, click Save, then click Initialize Database. Do not bypass this loop with raw migrations — the dynamic SQL paths in `datasets/views.py` will silently miss any column that is in the database but not in `Schema.json`.
2. **`CREATE TABLE IF NOT EXISTS` does not modify existing tables.** Changing an `int` column to `int (pk)` will only take effect on a freshly-created table. The supported way to apply such a change is to drop the table (Delete schema table button on the Schemas page) and re-create it.
3. **Guest accounts must stay read-only.** Every new write view must compose `@login_required` with `@non_guest_required` (from `apps.accounts.permissions`) and every new write button must be wrapped in `{% if not is_guest %}` in its template. The pattern is already applied across the codebase — please continue it.
4. **Keycloak realm changes need a volume wipe.** Edits to `keycloak/prism-realm.json` only re-import on a fresh volume, so users testing realm changes locally need `docker compose down -v` followed by `docker compose up`. Communicate this in advance whenever you ship a realm change — it also wipes the Postgres volume.
5. **All raw SQL must go through `_quote_ident`.** Never interpolate table or column names from user input (or from Schema.json, which is editable in-app) into SQL strings directly. The helper is in both `apps/datasets/views.py` and `apps/core/views.py`.
6. **Code is now commented throughout.** When you add new code, follow the same convention — `#` comment block above every module and function explaining intent and any non-obvious behaviour, plus inline `#` comments for tricky lines. Docstrings (`"""..."""`) were intentionally avoided in favour of plain `#` comments for consistency.

---

_Last updated: May 2026_
