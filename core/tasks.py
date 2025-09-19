from __future__ import absolute_import, unicode_literals
import os
import django
from venv import logger
from celery import shared_task
from time import sleep
import logging

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()


@shared_task
def test_task():
    logger.info("Task started")
    sleep(10)  # Simula una tarea que toma tiempo
    logger.info("Task completed")
    return "Task finished"
