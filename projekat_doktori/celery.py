# Milos Milinkovic 0396/2022
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projekat_doktori.settings')

app = Celery('projekat_doktori')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
