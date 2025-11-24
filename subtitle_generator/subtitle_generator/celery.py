import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'subtitle_generator.settings')

app = Celery('subtitle_generator')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находит tasks.py во всех Django приложениях
app.autodiscover_tasks()
