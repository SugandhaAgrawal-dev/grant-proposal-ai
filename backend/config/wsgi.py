"""
WSGI config for the grant proposal backend.

Exposes the WSGI callable as ``application`` for production servers
(gunicorn, uwsgi, mod_wsgi, etc.).
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
