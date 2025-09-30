# PRISM - Platform for Resource Intelligence & Subsurface Management

Sprint 1 MVP 구현 - Django 기반 지질 데이터 관리 플랫폼

## 주요 기능

### ✅ 구현된 기능 (Sprint 1)

- **인증 시스템**: Django 기본 인증 (개발 환경에서는 OIDC 비활성화 가능)
- **스키마 레지스트리**: JSON Schema 기반 데이터 스키마 관리
  - 스키마 생성 및 버전 관리
  - 버전별 승인 워크플로우
  - JSON Schema 유효성 검증
- **데이터셋 카탈로그**: 데이터셋 등록 및 관리
  - 스키마 참조 기반 데이터셋
  - 필터링 및 검색
- **Ingestion**: 데이터 수집 작업 추적 (기본 구조)
- **QAQC**: 품질 관리 대시보드 (기본 구조)
- **Lineage**: 데이터 계보 추적 (기본 구조)
- **REST API**: OpenAPI 문서화된 API
- **관리자 페이지**: Django Admin을 통한 데이터 관리

## 시작하기

### 필수 요구사항

- Python 3.11+
- Docker & Docker Compose
- Poetry (Python 패키지 관리자)

### 빠른 시작

```bash
# 1. 저장소 클론
git clone <your-repo>
cd prism

# 2. 의존성 설치 및 설정
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. 개발 서버 시작
poetry run python manage.py runserver

# 또는 Docker Compose로 전체 서비스 시작
docker compose up
```

### 접속 정보

- **웹 애플리케이션**: http://localhost:8000
- **관리자 페이지**: http://localhost:8000/admin/
  - Username: `admin`
  - Password: `admin123`
- **API 문서**: http://localhost:8000/api/schema/docs/
- **Keycloak 관리**: http://localhost:8080 (admin/admin)
- **MinIO 콘솔**: http://localhost:9001 (minio/minio123)

### 데모 데이터 생성

```bash
poetry run python scripts/create-demo-data.py
```

## 프로젝트 구조

```
prism/
├── manage.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.dev
├── prism_site/           # Django 프로젝트 설정
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── apps/                 # Django 앱들
│   ├── core/            # 핵심 기능 (홈, 헬스체크)
│   ├── accounts/        # 사용자 인증
│   ├── schemas/         # 스키마 레지스트리
│   ├── datasets/        # 데이터셋 카탈로그
│   ├── ingestion/       # 데이터 수집
│   ├── qaqc/           # 품질 관리
│   └── lineage/        # 데이터 계보
├── templates/           # HTML 템플릿
├── static/             # 정적 파일
└── scripts/            # 유틸리티 스크립트
```

## 개발 워크플로우

### 마이그레이션 생성 및 적용

```bash
poetry run python manage.py makemigrations
poetry run python manage.py migrate
```

### 테스트 실행

```bash
poetry run pytest
```

### 코드 포맷팅

```bash
poetry run black .
poetry run isort .
poetry run flake8 .
```

### Celery Worker 시작

```bash
poetry run celery -A prism_site worker -l info
```

## API 사용 예제

### 스키마 등록

```bash
curl -X POST http://localhost:8000/api/schemas/ \
  -H "Content-Type: application/json" \
  -d '{
    "key": "drillhole.assay",
    "owner": "Exploration Team",
    "description": "Assay results schema"
  }'
```

### 페이로드 검증

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

## 환경 변수

`.env.dev` 파일에서 다음 환경 변수를 설정할 수 있습니다:

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True

# Database
DATABASE_URL=postgresql+psycopg://prism:prism@db:5432/prism

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio123

# OIDC (선택사항)
DISABLE_OIDC=True
OIDC_ISSUER=http://keycloak:8080/realms/prism
OIDC_CLIENT_ID=prism-web
OIDC_CLIENT_SECRET=devsecret
```

## 목요일 데모 준비 체크리스트

- [x] Docker Compose 설정
- [x] Django 프로젝트 기본 구조
- [x] 사용자 인증 (개발 모드)
- [x] 스키마 레지스트리 CRUD
- [x] 데이터셋 카탈로그 CRUD
- [x] Bootstrap 5 UI
- [x] REST API with OpenAPI
- [x] Admin 페이지
- [x] 데모 데이터 생성 스크립트
- [ ] 프레젠테이션 자료

## 다음 단계 (Sprint 2+)

- JSON Schema 호환성 검사
- 드릴홀 데이터 모델 구현
- CSV 임포트 기능
- QAQC 검증 로직
- 실시간 대시보드

## 문제 해결

### 포트 충돌

```bash
# 사용 중인 포트 확인
lsof -i :8000
lsof -i :5432

# Docker 컨테이너 재시작
docker compose down
docker compose up -d
```

### 데이터베이스 초기화

```bash
docker compose down -v
docker compose up -d db
poetry run python manage.py migrate
```

### 정적 파일 문제

```bash
poetry run python manage.py collectstatic --clear --noinput
```

## 라이선스

이 프로젝트는 IT Capstone 프로젝트의 일부입니다.

## 팀

- 프로젝트 팀원들...

## 참고 자료

- Django Documentation: https://docs.djangoproject.com/
- DRF Documentation: https://www.django-rest-framework.org/
- JSON Schema: https://json-schema.org/
