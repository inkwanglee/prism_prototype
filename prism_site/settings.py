import environ
import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env.dev'))

# Variable
DISABLE_OIDC = env.bool('DISABLE_OIDC', default=False)

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env.bool('DJANGO_DEBUG', default=True)
ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    "https://prism-web.kindground-d178727f.australiaeast.azurecontainerapps.io",
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
#    'django.contrib.gis',
    
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
    'apps.ingestion',
    'apps.qaqc',
    'apps.lineage',
]

# Add OIDC app when SSO is enabled
if not DISABLE_OIDC:
    INSTALLED_APPS.append('mozilla_django_oidc')

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
            ],
        },
    },
]

WSGI_APPLICATION = 'prism_site.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Cache
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

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
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

# DRF Spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'PRISM API',
    'DESCRIPTION': 'Platform for Resource Intelligence & Subsurface Management',
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ============================================================
# OIDC Configuration (SSO)
# ============================================================
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
    OIDC_OP_AUTHORIZATION_ENDPOINT = f'{_OIDC_ISSUER}/protocol/openid-connect/auth'
    OIDC_OP_TOKEN_ENDPOINT = f'{_OIDC_ISSUER}/protocol/openid-connect/token'
    OIDC_OP_USER_ENDPOINT = f'{_OIDC_ISSUER}/protocol/openid-connect/userinfo'
    OIDC_OP_JWKS_ENDPOINT = f'{_OIDC_ISSUER}/protocol/openid-connect/certs'
    OIDC_OP_LOGOUT_ENDPOINT = f'{_OIDC_ISSUER}/protocol/openid-connect/logout'

    OIDC_STORE_ACCESS_TOKEN = True
    OIDC_STORE_ID_TOKEN = True

    OIDC_OP_LOGOUT_URL_METHOD = 'apps.accounts.backends.provider_logout_url'

    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = not DEBUG

else:
    LOGIN_URL = '/admin/login/'
    LOGIN_REDIRECT_URL = '/'
    LOGOUT_REDIRECT_URL = '/'

# Celery Configuration
CELERY_BROKER_URL = env('REDIS_URL')
CELERY_RESULT_BACKEND = env('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# MinIO Configuration
MINIO_ENDPOINT = env('MINIO_ENDPOINT')
MINIO_ACCESS_KEY = env('MINIO_ACCESS_KEY')
MINIO_SECRET_KEY = env('MINIO_SECRET_KEY')

# Logging
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

# Session timeout
SESSION_IDLE_TIMEOUT = 60
SESSION_COOKIE_AGE = SESSION_IDLE_TIMEOUT
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Database override for SQLite testing
if env.bool("USE_SQLITE", default=False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
