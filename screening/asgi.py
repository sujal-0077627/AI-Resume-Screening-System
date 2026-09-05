"""ASGI config for AI Resume Screening System."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'screening.settings')

application = get_asgi_application()