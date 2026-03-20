from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('schemas/', include('apps.schemas.urls')),
    path('datasets/', include('apps.datasets.urls')),
    path('ingestion/', include('apps.ingestion.urls')),
    path('qaqc/', include('apps.qaqc.urls')),
    path('lineage/', include('apps.lineage.urls')),

    # API URLs
    path('api/schemas/', include('apps.schemas.api_urls')),
    path('api/datasets/', include('apps.datasets.api_urls')),

    # API Documentation
    path('api/schema/openapi.yaml', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Metrics
    path('', include('django_prometheus.urls')),
]

# OIDC Routes (only when SSO is enabled)
if not getattr(settings, 'DISABLE_OIDC', True):
    urlpatterns += [
        path('oidc/', include('mozilla_django_oidc.urls')),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
