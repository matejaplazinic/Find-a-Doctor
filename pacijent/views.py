# Mateja Plazinic 2022/0335
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Case, When, IntegerField
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
import os

from django.views.decorators.http import require_POST

from doktor.models import Slika, Termini, Recepti, OmiljeniLekari, User, Lekari, Recenzije
from pacijent.geolocation import haversine

@login_required
def pacijent_profile(request):
    """
        View koji prikazuje profil pacijenta i omogućava izmenu ličnih podataka.

        Funkcija omogućava pacijentu da pregleda svoje osnovne podatke, omiljene lekare,
        termine i recepte. Takođe omogućava izmenu ličnih informacija i profilne slike.
        U slučaju POST zahteva, podaci se ažuriraju i čuvaju u bazi.

        Koristi sledeće modele:
        - :model:`doktor.Slika`
        - :model:`doktor.Termini`
        - :model:`doktor.Recepti`
        - :model:`doktor.OmiljeniLekari`
        - :model:`doktor.User`

        :param request: HTTP zahtev korisnika
        :return: Renderovani HTML šablon sa podacima pacijenta
        """
    pacijent = request.user

    if request.method == 'POST':
        if request.POST.get('action') == 'edit_pacijent':
            pacijent.ime = (request.POST.get('ime') or pacijent.ime or '').strip()
            pacijent.email=(request.POST.get('email') or pacijent.email or '').strip()
            pacijent.prezime = (request.POST.get('prezime') or pacijent.prezime or '').strip()
            pacijent.adresa = (request.POST.get('adresa') or pacijent.adresa or '').strip()
            pacijent.telefon = (request.POST.get('telefon') or pacijent.telefon or '').strip()
            pacijent.medicinska_istorija = (request.POST.get('medicinska_istorija') or pacijent.medicinska_istorija or '').strip()

            # Ako je poslata nova profilna slika
            if 'slika' in request.FILES:
                profile_img = request.FILES['slika']

                # obriši staru sliku ako postoji
                if pacijent.slika and pacijent.slika.slika_link:
                    old_path = os.path.join(settings.MEDIA_ROOT, str(pacijent.slika.slika_link))
                    if os.path.exists(old_path):
                        os.remove(old_path)
                    pacijent.slika.delete()

                # sačuvaj novu
                nova_slika = Slika.objects.create(slika_link=profile_img)
                pacijent.slika = nova_slika

            pacijent.save()
            return redirect('pacijent_profile')


    favorites = OmiljeniLekari.objects.filter(pacijent=pacijent).select_related('lekar', 'lekar__user')
    appointments_qs = (
        Termini.objects.filter(pacijent=pacijent)
        .select_related('lekar', 'lekar__user')
        .order_by(
            Case(
                When(status='zakazan', then=0),
                When(status='potvrđen', then=1),
                When(status='završen', then=2),
                When(status='otkazan', then=3),
                default=4,
                output_field=IntegerField()
            ),
            'kraj'
        )
    )

    paginator = Paginator(appointments_qs, 4)
    page_number = request.GET.get('page')
    appointments = paginator.get_page(page_number)
    prescriptions = Recepti.objects.filter(pacijent=pacijent).select_related('lekar', 'lekar__user')
    verifikovan=request.user.verifikovan
    context = {
        'pacijent': pacijent,
        'favorites': favorites,
        'appointments': appointments,
        'prescriptions': prescriptions,
        'verifikovan': verifikovan,
    }

    return render(request, 'profil.html', context)


def pretraga(request):
    """
        View koji omogućava pacijentu pretragu lekara prema različitim kriterijumima.

        Pretraga se vrši po imenu, prezimenu, specijalizaciji ili klinici.
        Takođe podržava filtriranje po ceni, oceni i sortiranju po lokaciji.
        Rezultati se prikazuju paginirano i mogu uključivati geolokacione markere.

        Koristi sledeće modele:
        - :model:`doktor.Lekari`
        - :model:`doktor.Recenzije`
        - :model:`doktor.Klinike`
        - :model:`doktor.User`

        :param request: HTTP zahtev koji može sadržati GET parametre za pretragu
        :return: Renderovani HTML šablon sa rezultatima pretrage
        """
    query = request.GET.get('q', '').strip()

    rezultati = Lekari.objects.filter(user__verifikovan=True).select_related('user', 'klinika')

    # --- FILTERI ---
    min_cena = request.GET.get('min_cena')
    max_cena = request.GET.get('max_cena')
    specijalizacija = request.GET.get('specijalizacija')

    min_ocena = request.GET.get('min_ocena')
    max_ocena = request.GET.get('max_ocena')

    sort_po_lokaciji = request.GET.get('sort_po_lokaciji')  # checkbox

    q_obj = Q()

    # Pretraga po imenu/prezime/specijalizacija/klinika
    if query:
        reci = query.split()
        q_ime = Q()
        q_prezime = Q()
        q_spec = Q()
        q_klinika = Q()
        for rec in reci:
            q_ime &= Q(user__ime__icontains=rec)
            q_prezime &= Q(user__prezime__icontains=rec)
            q_spec &= Q(specijalizacija__icontains=rec)
            q_klinika &= Q(klinika__naziv__icontains=rec)
        q_obj &= q_ime | q_prezime | q_spec | q_klinika

    # Filter po ceni
    if min_cena:
        try:
            q_obj &= Q(cena__gte=int(min_cena))
        except ValueError:
            pass
    if max_cena:
        try:
            q_obj &= Q(cena__lte=int(max_cena))
        except ValueError:
            pass

    # Filter po specijalizaciji
    if specijalizacija:
        q_obj &= Q(specijalizacija__iexact=specijalizacija)

    # Primeni sve Q filtere
    rezultati = rezultati.filter(q_obj)

    # --- Dodavanje prosečne ocene i filter po oceni ---
    rezultati = rezultati.annotate(prosecna_ocena=Avg('recenzije__ocena'))

    if min_ocena:
        try:
            rezultati = rezultati.filter(prosecna_ocena__gte=float(min_ocena))
        except ValueError:
            pass
    if max_ocena:
        try:
            rezultati = rezultati.filter(prosecna_ocena__lte=float(max_ocena))
        except ValueError:
            pass

    # Za prikaz u HTML-u zaokruži ocenu
    for lekar in rezultati:
        if lekar.prosecna_ocena:
            lekar.prosecna_ocena = round(lekar.prosecna_ocena, 1)
    pacijent_lat=None
    pacijent_long=None
    if request.user.is_authenticated:
        pacijent_lat = request.user.latitude or 44.8176
    if request.user.is_authenticated:
        pacijent_long = request.user.longitude or 20.4569
    # --- Sortiranje po najbližoj lokaciji ---

    if request.user.is_authenticated and sort_po_lokaciji and hasattr(request.user, 'latitude') and hasattr(request.user, 'longitude'):
        user_lat = request.user.latitude
        user_lon = request.user.longitude

        rezultati_list = list(rezultati)  # queryset -> lista
        for lekar in rezultati_list:
            if lekar.klinika and lekar.klinika.latitude and lekar.klinika.longitude:
                lekar.distance = haversine(user_lat, user_lon, lekar.klinika.latitude, lekar.klinika.longitude)
            else:
                lekar.distance = float('inf')  # ako klinika nema koordinate, stavi daleko

        # Sortiraj po rastućoj udaljenosti
        rezultati_list.sort(key=lambda x: x.distance)
        rezultati = rezultati_list  # zamenjujemo queryset sa sortiranom listom
    klinike_coords = []
    for lekar in rezultati:
        if lekar.klinika and lekar.klinika.latitude is not None and lekar.klinika.longitude is not None:
            klinike_coords.append({
                'latitude': float(lekar.klinika.latitude),
                'longitude': float(lekar.klinika.longitude),
                'naziv': lekar.klinika.naziv,
            })


    markers = []
    if pacijent_lat and pacijent_long:
        markers.append(f"{pacijent_lat:.6f},{pacijent_long:.6f},red")
    for klinika in klinike_coords:
        markers.append(f"{klinika['latitude']:.6f},{klinika['longitude']:.6f},blue")

    markers_str = "|".join(markers)
    paginator = Paginator(rezultati, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        'query': query,
        "rezultati": page_obj,
        "page_obj": page_obj,
        'pacijent_lat': pacijent_lat,
        'pacijent_long': pacijent_long,
        'markers': markers_str,
        'klinike_coords': klinike_coords,
    }
    return render(request, 'pretraga.html', context)
@login_required
def dodaj_u_omiljene(request, lekar_id):
    """
        Dodaje određenog lekara u listu omiljenih za prijavljenog pacijenta.

        Ako lekar već postoji u listi omiljenih, vraća se odgovarajuća JSON poruka.
        Dostupno samo korisnicima sa ulogom "pacijent".

        Koristi sledeće modele:
        - :model:`doktor.OmiljeniLekari`
        - :model:`doktor.Lekari`

        :param request: HTTP zahtev korisnika
        :param lekar_id: ID lekara koji se dodaje u omiljene
        :return: JSON odgovor sa statusom uspeha ili greške
        """
    user = request.user
    if user.role.name != 'pacijent':
        return JsonResponse({'status': 'error', 'message': 'Samo pacijent može dodati u omiljene.'})

    try:
        lekar = Lekari.objects.get(id=lekar_id)
    except Lekari.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Doktor ne postoji.'})

    # Provera da li je već dodat
    omiljeni, created = OmiljeniLekari.objects.get_or_create(pacijent=user, lekar=lekar)
    if created:
        return JsonResponse({'status': 'ok', 'message': 'Lekar dodat u omiljene.'})
    else:
        return JsonResponse({'status': 'exists', 'message': 'Lekar je već u omiljenim.'})
@login_required
def ukloni_omiljenog(request):
    """
        Uklanja lekara iz liste omiljenih pacijenta.

        Očekuje POST zahtev sa ID-em lekara. Ako lekar ne postoji u listi omiljenih,
        vraća se JSON greška.

        Koristi sledeće modele:
        - :model:`doktor.OmiljeniLekari`

        :param request: HTTP POST zahtev sa lekar_id parametrom
        :return: JSON odgovor sa informacijom o uspehu operacije
        """
    if request.method == 'POST':
        lekar_id = request.POST.get('lekar_id')
        try:
            omiljeni = OmiljeniLekari.objects.get(pacijent=request.user, lekar_id=lekar_id)
            omiljeni.delete()
            return JsonResponse({'success': True})
        except OmiljeniLekari.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Lekar nije u omiljenima'})
    return JsonResponse({'success': False, 'error': 'Nevalidan zahtev'})
@login_required
@require_POST
def dodaj_recenziju(request):
    """
        Dodaje ili ažurira recenziju za određenog lekara od strane pacijenta.

        Ako pacijent već ima recenziju za datog lekara, postojeća recenzija se ažurira.
        Nakon dodavanja ili izmene, automatski se izračunava nova prosečna ocena lekara.

        Koristi sledeće modele:
        - :model:`doktor.Lekari`
        - :model:`doktor.Recenzije`

        :param request: HTTP POST zahtev koji sadrži ocenu, komentar i ID lekara
        :return: JSON odgovor sa statusom i ažuriranom prosečnom ocenom lekara
        """
    lekar_id = request.POST.get('lekar_id')
    ocena = request.POST.get('ocena')
    komentar = request.POST.get('komentar', '').strip()

    if not lekar_id or not ocena:
        return JsonResponse({'status': 'error', 'message': 'Nedostaju podaci.'}, status=400)

    try:
        ocena = int(ocena)
        if ocena < 1 or ocena > 5:
            return JsonResponse({'status': 'error', 'message': 'Ocena mora biti između 1 i 5.'}, status=400)
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Nevažeća ocena.'}, status=400)

    try:
        lekar = Lekari.objects.get(id=lekar_id)
    except Lekari.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Lekar ne postoji.'}, status=404)

    #  Proveri da li pacijent već ima recenziju
    recenzija, created = Recenzije.objects.get_or_create(
        pacijent=request.user,
        lekar=lekar,
        defaults={'ocena': ocena, 'komentar': komentar}
    )

    #  Ako već postoji — ažuriraj
    if not created:
        recenzija.ocena = ocena
        recenzija.komentar = komentar
        recenzija.save()

    #  Izračunaj prosečnu ocenu
    prosecna = Recenzije.objects.filter(lekar=lekar).aggregate(Avg('ocena'))['ocena__avg'] or 0

    return JsonResponse({
        'status': 'ok',
        'prosecna_ocena': round(prosecna, 1),
        'moja_ocena': recenzija.ocena,
        'moj_komentar': recenzija.komentar,
    })