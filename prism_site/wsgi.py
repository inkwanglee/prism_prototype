# =============================================================================
# WSGI entry point for PRISM.
# =============================================================================
# Used by Gunicorn (see scripts/start-web.sh) and by Azure Container
# Apps when serving the production deployment.
# =============================================================================

import os
from django.core.wsgi import get_wsgi_application

# Ensure Django knows which settings module to load. setdefault means
# an outer environment value (e.g. set by Docker) wins over this default.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prism_site.settings')

# The WSGI callable that Gunicorn / mod_wsgi / Azure looks for.
application = get_wsgi_application()
