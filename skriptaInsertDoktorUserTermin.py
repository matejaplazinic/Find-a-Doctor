import os
import django
from datetime import datetime, timedelta, time
from django.utils.timezone import make_aware, localtime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projekat_doktori.settings")
django.setup()

from doktor.models import Termini, Lekari, User

lekar = Lekari.objects.first()

termin = Termini.objects.create(
    lekar=lekar,
    pacijent=User.objects.get(id = 4),
    pocetak=datetime.now() - timedelta(days=1, hours=1),
    kraj=datetime.now() - timedelta(days=1),
    status='potvrđen',
    prescription='',
    description=''
)

print(f"Test termin kreiran: {termin.id}")
