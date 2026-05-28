"""
Configuración global de pytest para FairBet Lab.
"""
import django
from django.conf import settings


def pytest_configure(config):
    """Asegura que Django esté configurado antes de correr tests."""
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
