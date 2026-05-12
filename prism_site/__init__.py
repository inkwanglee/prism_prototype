# =============================================================================
# Package init for prism_site.
# =============================================================================
# Imports the Celery app at startup so `@shared_task` decorators work
# the moment any code does `from celery import shared_task`.
# =============================================================================

from .celery import app as celery_app

# Re-export the celery app so external code can do
# `from prism_site import celery_app`.
__all__ = ('celery_app',)
