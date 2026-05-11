# =============================================================================
# PRISM Django settings.
# =============================================================================
# Single settings module; environment-specific values come from .env.dev
# (via django-environ). The DISABLE_OIDC flag swaps between full Keycloak
# SSO and Django's built-in admin login so local dev works without
# spinning up Keycloak.
# =============================================================================

import environ
import os
from pathlib import Path

# Project root — used to build absolute paths into the source tree.
BASE_DIR = Path(__file__).resolve().parent.parent

# django-environ loads the .env file once at import time. Every env()
# call below pulls from process env first, then this .env file.
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env.dev'))

# Toggle: when True, skip OIDC entirely and fall back to Django admin
# login. Useful for fast local iteration without Keycloak running.
DISABLE_OIDC = env.bool('DISABLE_OIDC', default=False)

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env.bool('DJANGO_DEBUG', default=True)
ALLOWED_HOSTS = ['*']

# CSRF must trust our deployed Azure URL — otherwise POSTs fail with a
# "Origin checking failed" error behind the reverse proxy.
CSRF_TRUSTED_ORIGINS = [
    "https://prism-web.kindground-d178727f.australiaeast.azurecontainerapps.io",
]

# When we're behind a TLS-terminating proxy (Azure Container Apps),
# Django sees plain HTTP — these settings teach it to trust the
# X-Forwarded-Proto / X-Forwarded-Host headers the proxy sets.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'django_prometheus',
    'django_htmx',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',

    # Local apps
    'apps.core',
    'apps.accounts',
    'apps.schemas',
    'apps.datasets',
    'apps.qaqc',
    'apps.lineage',
]

# Add OIDC app when SSO is enabled. Conditional so the dev-only
# DISABLE_OIDC=True path doesn't import a backend we won't use.
if not DISABLE_OIDC:
    INSTALLED_APPS.append('mozilla_django_oidc')

# Middleware order matters. Notes on the PRISM-specific entries:
#   - django_prometheus.PrometheusBeforeMiddleware  : start request timer.
#   - apps.accounts.middleware.OIDCClaimsMiddleware : attach OIDC claims
#       (prism_roles, project_ids) from the session onto request.user.
#   - apps.core.middleware.IdleTimeoutMiddleware    : redirect to logout
#       after SESSION_IDLE_TIMEOUT seconds of inactivity.
#   - django_prometheus.PrometheusAfterMiddleware   : finish request timer.
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.accounts.middleware.OIDCClaimsMiddleware',
    'apps.core.middleware.IdleTimeoutMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'prism_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # PRISM: expose is_guest to every template so the UI
                # can hide write buttons from read-only guests.
                'apps.accounts.context_processors.user_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'prism_site.wsgi.application'

# Database — DATABASE_URL is parsed by django-environ. Postgres in
# production / Docker, SQLite when USE_SQLITE=True (see end of file).
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Redis-backed cache. Shared with Celery (CELERY_BROKER_URL below).
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files. WhiteNoise serves them in-process so we don't need
# a separate Nginx for static content.
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (user uploads — currently unused but configured for future use).
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Use BigAutoField for new models so PK columns get a 64-bit range.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework — Spectacular for OpenAPI, session auth + paged lists.
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

# drf-spectacular config — drives /api/schema/docs/ and /api/schema/redoc/.
SPECTACULAR_SETTINGS = {
    'TITLE': 'PRISM API',
    'DESCRIPTION': 'Platform for Resource Intelligence & Subsurface Management',
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}

# Crispy Forms — Bootstrap 5 layout pack.
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ============================================================
# OIDC Configuration (SSO)
# ============================================================
# Two issuer URLs are wired up:
#   _OIDC_ISSUER          - browser-facing (http://localhost:8080/...)
#   _OIDC_ISSUER_INTERNAL - server-to-server (http://keycloak:8080/...)
# In production both can be the same. In docker-compose the internal
# value is set to the docker-network hostname so the web container can
# reach Keycloak without going through the host machine.
if not DISABLE_OIDC:
    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'apps.accounts.backends.PrismOIDCBackend',
    )

    LOGIN_URL = '/accounts/login/'
    LOGIN_REDIRECT_URL = '/'
    LOGOUT_REDIRECT_URL = '/'

    OIDC_RP_CLIENT_ID = env('OIDC_CLIENT_ID')
    OIDC_RP_CLIENT_SECRET = env('OIDC_CLIENT_SECRET')
    OIDC_RP_SIGN_ALGO = 'RS256'
    OIDC_RP_SCOPES = 'openid profile email'

    _OIDC_ISSUER = env('OIDC_ISSUER')
    _OIDC_ISSUER_INTERNAL = env('OIDC_ISSUER_INTERNAL', default=_OIDC_ISSUER)

    # Browser-facing endpoints (user gets redirected to these).
    OIDC_OP_AUTHORIZATION_ENDPOINT = f'{_OIDC_ISSUER}/protocol/openid-connect/auth'
    OIDC_OP_LOGOUT_ENDPOINT = f'{_OIDC_ISSUER}/protocol/openid-connect/logout'

    # Server-to-server endpoints (Django container talks directly to Keycloak).
    OIDC_OP_TOKEN_ENDPOINT = f'{_OIDC_ISSUER_INTERNAL}/protocol/openid-connect/token'
    OIDC_OP_USER_ENDPOINT = f'{_OIDC_ISSUER_INTERNAL}/protocol/openid-connect/userinfo'
    OIDC_OP_JWKS_ENDPOINT = f'{_OIDC_ISSUER_INTERNAL}/protocol/openid-connect/certs'

    OIDC_STORE_ACCESS_TOKEN = True
    OIDC_STORE_ID_TOKEN = True

    # Custom logout URL builder — assembles the Keycloak RP-initiated
    # logout URL with id_token_hint and post_logout_redirect_uri.
    OIDC_OP_LOGOUT_URL_METHOD = 'apps.accounts.backends.provider_logout_url'

    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = not DEBUG

else:
    # Local-dev fallback: just use Django's admin login form.
    LOGIN_URL = '/admin/login/'
    LOGIN_REDIRECT_URL = '/'
    LOGOUT_REDIRECT_URL = '/'

# Celery — same Redis instance as the cache.
CELERY_BROKER_URL = env('REDIS_URL')
CELERY_RESULT_BACKEND = env('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# MinIO — S3-compatible object storage for local dev. Production
# would swap these for real S3 / Azure Blob credentials.
MINIO_ENDPOINT = env('MINIO_ENDPOINT')
MINIO_ACCESS_KEY = env('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = env('MINIO_SECRET_KEY')

# Logging — single stdout handler so Docker / Azure Container Apps
# pick everything up via container stdout.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Session policy.
# - SESSION_IDLE_TIMEOUT      : enforced by IdleTimeoutMiddleware.
# - SESSION_COOKIE_AGE        : Django's own hard ceiling (8 hours).
# - SESSION_SAVE_EVERY_REQUEST: refresh the cookie expiry on each hit.
SESSION_IDLE_TIMEOUT = 3600  # 1 hour in seconds
SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Database override for SQLite testing. Set USE_SQLITE=True in the env
# to swap the default Postgres connection for a local SQLite file.
# Useful for unit tests that don't want to spin up Docker.
if env.bool("USE_SQLITE", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
