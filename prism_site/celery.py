# =============================================================================
# Celery application setup for PRISM.
# =============================================================================
# Imported by prism_site/__init__.py so Celery picks up the app at startup,
# and used by the `celery -A prism_site` command line.
# =============================================================================

import os
from celery import Celery

# Make sure the Django settings module is set before we start Celery —
# Celery imports task modules and many of them touch Django internals.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prism_site.settings')

# The Celery app instance. The name ('prism_site') is what `celery -A`
# expects on the command line.
app = Celery('prism_site')

# Pull Celery config from Django settings using the CELERY_ namespace.
# So CELERY_BROKER_URL in settings.py becomes broker_url here, etc.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover @shared_task functions in every installed app's tasks.py.
app.autodiscover_tasks()
