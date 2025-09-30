# 🚀 PRISM 빠른 시작 가이드 (목요일 데모용)

## 1️⃣ 사전 준비 (5분)

```bash
# Docker 실행 확인
docker --version
docker compose version

# Poetry 설치 확인 (없으면 설치)
poetry --version
# 없다면: curl -sSL https://install.python-poetry.org | python3 -
```

## 2️⃣ 프로젝트 설정 (10분)

```bash
# 프로젝트 폴더로 이동
cd prism

# 실행 권한 부여
chmod +x scripts/*.sh

# 전체 설정 자동화 실행
./scripts/setup.sh
```

이 스크립트는 다음을 자동으로 수행합니다:
- Poetry 의존성 설치
- Docker 서비스 시작 (PostgreSQL, Redis, MinIO, Keycloak)
- 데이터베이스 마이그레이션
- 슈퍼유저 생성 (admin/admin123)
- Static 파일 수집

## 3️⃣ 서버 시작 (1분)

### 옵션 A: 간단한 개발 서버

```bash
poetry run python manage.py runserver
```

### 옵션 B: Docker Compose로 전체 서비스

```bash
docker compose up
```

## 4️⃣ 데모 데이터 생성 (1분)

```bash
# 새 터미널에서 실행
poetry run python scripts/create-demo-data.py
```

이 스크립트는 다음을 생성합니다:
- 샘플 스키마 (drillhole.collar)
- 샘플 데이터셋
- 샘플 Ingestion Run
- 샘플 QAQC Run
- 샘플 Snapshot

## 5️⃣ 접속 확인 ✅

브라우저에서 다음 URL들을 확인하세요:

### 메인 애플리케이션
- 🏠 홈: http://localhost:8000
- 🔐 로그인: http://localhost:8000/admin/
  - Username: `admin`
  - Password: `admin123`

### 주요 페이지
- 📋 Schemas: http://localhost:8000/schemas/
- 📊 Datasets: http://localhost:8000/datasets/
- ⬆️ Ingestion: http://localhost:8000/ingestion/
- ✅ QAQC: http://localhost:8000/qaqc/
- 🔗 Lineage: http://localhost:8000/lineage/

### API & 문서
- 📖 API Docs (Swagger): http://localhost:8000/api/schema/docs/
- 📚 ReDoc: http://localhost:8000/api/schema/redoc/
- 🔧 Admin Panel: http://localhost:8000/admin/

### 인프라 (선택)
- 🗄️ MinIO Console: http://localhost:9001 (minio/minio123)
- 🔑 Keycloak: http://localhost:8080 (admin/admin)

## 6️⃣ 데모 시나리오 📝

### 시나리오 1: 스키마 생성 및 관리

1. **로그인**
   - http://localhost:8000/admin/ 접속
   - admin / admin123 로 로그인

2. **스키마 보기**
   - 좌측 메뉴에서 "Schemas" 클릭
   - 생성된 `drillhole.collar` 스키마 확인

3. **스키마 상세 보기**
   - 스키마 클릭하여 버전 정보 확인
   - v0.1.0 (Approved) 상태 확인

4. **새 버전 추가** (선택)
   - "Add Version" 버튼 클릭
   - 버전: 0.2.0
   