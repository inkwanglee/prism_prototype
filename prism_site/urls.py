from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
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

# OIDC URLs (개발 환경에서는 선택적)
if not settings.DEBUG or not getattr(settings, 'DISABLE_OIDC', False):
    from mozilla_django_oidc import views as oidc_views
    urlpatterns += [
        path('oidc/authenticate/', oidc_views.OIDCAuthenticationRequestView.as_view(), name='oidc_auth'),
        path('oidc/callback/', oidc_views.OIDCAuthenticationCallbackView.as_view(), name='oidc_callback'),
        path('oidc/logout/', oidc_views.OIDCLogoutView.as_view(), name='oidc_logout'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)