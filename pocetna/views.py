# Milos Milinkovic 0396/2022
from django.shortcuts import render
from django.utils import timezone
from doktor.models import User, Lekari, Aktuelnosti, Klinike, Termini

def home(request):
    """
    Prikazuje naslovnu stranicu sajta.

    **Opis:**

    - Prikazuje relevantne podatke u zavisnosti od tipa korisnika (doktor, pacijent, gost).
    - Ako je korisnik doktor, prikazuju se njegovi budući termini.
    - Ako je korisnik gost ili pacijent, prikazuju se top klinike i top doktori.
    - Prikazuju se najnovije verifikovane vesti.

    **Korišćeni modeli:**

    :model:`doktor.User` - za informacije o trenutno ulogovanom korisniku

    :model:`doktor.Lekari` - za informacije o doktorima

    :model:`doktor.Aktuelnosti` - za prikaz novosti

    :model:`doktor.Klinike` - za prikaz top klinika

    :model:`doktor.Termini` - za dohvat termina doktora

    **Template:**
    :template:`index.html`
    """
    user = request.user if request.user.is_authenticated else None
    user_type = 'gost'
    termini = None

    if user:
        role_name = user.role.name if hasattr(user, 'role') else ''
        if role_name == 'doktor':
            user_type = 'doktor'
            lekar = Lekari.objects.filter(user=user).first()
            if lekar:
                # samo buduci termini
                    termini = Termini.objects.filter(
                    lekar=lekar,
                    pocetak__gte=timezone.now()
                ).order_by('pocetak')[:6]
        elif role_name == 'pacijent':
            user_type = 'pacijent'

    vesti = Aktuelnosti.objects.filter(verifikovana=True).order_by('-datum')[:5]

    context = {
        "user_type": user_type,
        "user": user,
        "vesti": vesti,
    }

    if user_type == 'doktor' and termini:
        context["termini"] = termini

    if user_type in ['gost', 'pacijent']:
        context["top_klinike"] = Klinike.objects.filter(verifikovana=True)[:3]
        context["top_doktori"] = Lekari.objects.filter(user__verifikovan=True)[:3]

    return render(request, "index.html", context)
