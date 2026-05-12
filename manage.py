# =============================================================================
# Django command-line entrypoint.
# =============================================================================
# Invoked as `python manage.py <command>` for migrations, dev server,
# management commands like `create_guest_user`, shell access, etc.
# =============================================================================

import os
import sys


def main():
    # Run administrative tasks.
    # Point Django at our settings module before importing anything that
    # depends on Django being configured.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prism_site.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Translate the cryptic ImportError into something a new developer
        # can actually act on (forgot to activate venv, missed `poetry install`,
        # etc.).
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
