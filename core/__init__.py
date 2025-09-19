
from __future__ import absolute_import, unicode_literals

# Esto asegura que la app de Celery esté siempre importada cuando
# Django inicie para que shared_task use esta app.
from .celery import app as celery_app

__all__ = ('celery_app',)
