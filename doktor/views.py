# Milos Milinkovic 0396/2022
from django.contrib.auth.decorators import login_required
from django.template.context_processors import request
from django.utils.timezone import localtime

from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.shortcuts import render, redirect, get_object_or_404
from .models import Lekari, Termini, Aktuelnosti, DoctorDocument, Klinike, Slika, Recenzije, OmiljeniLekari, Recepti
from django.utils import timezone
import json
from datetime import datetime, timedelta, time
from .tasks import obavesti_o_izmeni_termina, obavesti_doktora_o_novom_termine


@login_required
def doctor_profile(request):
    """
    Prikazuje profil doktora i omogućava interakciju sa njegovim terminima i dokumentima.

    **Opis:**

    - Provera da li je ulogovan korisnik doktor, ako nije – preusmerava na home.
    - Doktor može da:
        - Završi termin i dodaje recept
        - Potvrdi ili otkaže termin
        - Izmeni svoj profil i dodaje dokumente ili profilnu sliku
        - Dodaje novosti (vesti)
    - Dohvata prošle i buduće termine za prikaz na stranici
    - Prikazuje sve dokumente doktora
    - Prikazuje sve vesti koje je doktor dodao
    - Priprema JSON sa terminima za JS kalendar

    **Korišćeni modeli:**

    :model:`doktor.Lekari` - informacije o doktoru

    :model:`doktor.Termini` - za termine doktora

    :model:`doktor.Recepti` - recepti za završene termine

    :model:`doktor.Slika` - slike recepata ili profilne slike

    :model:`doktor.DoctorDocument` - dokumenti doktora

    :model:`doktor.Aktuelnosti` - vest koju doktor može dodati

    :model:`doktor.Klinike` - za povezivanje doktora sa klinikom

    **Template:**
    :template:`doctor_profile.html`
    """

    if not getattr(request.user, 'role', None) or request.user.role.name != 'doktor':
        return redirect('home')

    lekar = Lekari.objects.filter(user=request.user).first()

    if not lekar:
        return  render(request, 'doctor_profile.html', {'error': 'Nema doktora u bazi za prikaz'})

    if request.method == 'POST':
        action = request.POST.get('action')
        termin_id = request.POST.get('termin_id')

        if action == 'finish' and termin_id:
            termin = get_object_or_404(Termini, id=termin_id, lekar=lekar)

            termin.description = request.POST.get('description', '').strip()
            termin.prescription = request.POST.get('recept_tekst', '').strip()

            recept_tekst = request.POST.get('recept_tekst', '').strip()
            recept_slika = request.FILES.get('recept_slika')

            if recept_tekst or recept_slika:
                recept_obj = Recepti.objects.create(
                    lekar=lekar,
                    pacijent=termin.pacijent,
                    tekst=recept_tekst,
                    slika=Slika.objects.create(slika_link=recept_slika) if recept_slika else None
                )
                termin.recept = recept_obj

            termin.status = 'zavrsen'
            termin.save()

            obavesti_o_izmeni_termina.delay(termin.id)
            return redirect('doctor_profile')


        elif action in ['accept', 'reject'] and termin_id:

            termin = get_object_or_404(Termini, id=termin_id, lekar=lekar)

            termin.status = 'potvrđen' if action == 'accept' else 'otkazan'

            termin.save()

            obavesti_o_izmeni_termina.delay(termin.id)

            return redirect('doctor_profile')


        elif action == 'edit_doctor':
            print("isaoaasdadkasdoiad")
            ime_prezime = request.POST.get('doc_name', '').strip()
            email = request.POST.get('doc_email', '').strip()
            specijalizacija = request.POST.get('doc_spec', '').strip()
            telefon = request.POST.get('telefon_', '').strip()

            if ' ' in ime_prezime:
                ime, prezime = ime_prezime.split(' ', 1)
            else:
                ime, prezime = ime_prezime, ''

            lekar.user.ime = ime
            lekar.user.prezime = prezime
            lekar.user.email = email
            lekar.user.telefon = telefon

            cena = request.POST.get('doc_cena')
            if cena:
                try:
                    lekar.cena = float(cena)
                except ValueError:
                    pass

            lekar.user.save()

            klinika_id = request.POST.get('doc_clinic_id')

            if klinika_id:
                try:
                    klinika = Klinike.objects.get(id=klinika_id)
                    lekar.klinika = klinika
                except Klinike.DoesNotExist:
                    pass

            lekar.specijalizacija = specijalizacija
            lekar.save()

            if 'doc_files' in request.FILES:
                for f in request.FILES.getlist('doc_files'):
                    DoctorDocument.objects.create(lekar=lekar, file=f)

            if 'profile_image' in request.FILES:
                profile_img = request.FILES['profile_image']
                slika_obj = Slika.objects.create(slika_link=profile_img)
                lekar.user.slika = slika_obj
                lekar.user.save()


            return redirect('doctor_profile')

        elif action == 'add_news':
            print("addnews")

            news_title = request.POST.get('news_title', '').strip()
            news_content = request.POST.get('news_content', '').strip()
            news_image = request.FILES.get('news_image')
            slika_obj = None
            if news_image:
                slika_obj = Slika.objects.create(slika_link=news_image)
            if news_title and news_content:
                Aktuelnosti.objects.create(
                    autor=lekar.user,
                    naslov=news_title,
                    sadrzaj=news_content,
                    slika=slika_obj
                )
            return redirect('doctor_profile')

    dokumenti = lekar.documents.all()

    all_events = Termini.objects.filter(lekar=lekar).exclude(status='slobodan')
    events = []
    for t in all_events:
        color_map = {'zakazan':'yellow','potvrđen':'green','zavrsen':'blue','otkazan':'red'}
        patient_name = f"{t.pacijent.ime} {t.pacijent.prezime}" if t.pacijent else "Nema pacijenta"
        events.append({
            'id': t.id,
            'title': f"{patient_name} ({t.status})",
            'start': t.pocetak.isoformat(),
            'end': t.kraj.isoformat(),
            'color': color_map.get(t.status,'gray'),
            'extendedProps': {
                'status': t.status,
                'pacijent': patient_name,
                'vreme': f"{t.pocetak.time()} - {t.kraj.time()}",
                'prescription': t.prescription or '-',
                'description': t.description or '-'
            }
        })

    prosli_termini = Termini.objects.filter(
        lekar=lekar,
        kraj__lt=timezone.now()
    ).filter(Q(status='potvrđen') | Q(status='zavrsen')).order_by('-pocetak')

    klinika_verifikovana = None
    if lekar.klinika:
        klinika_verifikovana = getattr(lekar.klinika, 'verifikovana', None)

    context = {
        'lekar': lekar,
        'dokumenti': dokumenti,
        'istorija': prosli_termini,
        'vesti': Aktuelnosti.objects.filter(autor=lekar.user).order_by('-datum'),
        'events_json': json.dumps(events),
        'sve_klinike': Klinike.objects.all(),
        'verifikovan': lekar.user.verifikovan,
        'klinika_verifikovana': klinika_verifikovana,  # 👈 dodato

    }

    return render(request, 'doctor_profile.html', context)

from django.utils.timezone import make_aware, localtime
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.shortcuts import render, get_object_or_404, redirect
from .models import Lekari, Termini, Recenzije, Klinike

from datetime import datetime, timedelta, time

def doktor_javni(request, id):
    """
    Prikazuje javni profil doktora za pacijente ili goste.

    **Opis:**

    - Dohvata informacije o doktoru prema ID-u korisnika
    - Prikazuje recenzije doktora sa paginacijom
    - Izračunava prosečnu ocenu
    - Generiše listu slobodnih termina u 20-minutnim slotovima za narednih 10 dana
    - Omogućava pacijentima zakazivanje termina (20, 40 ili 60 minuta)
    - Priprema zauzete termine za JS kalendar
    - Prikazuje da li je doktor omiljeni korisniku (ako je pacijent)

    **Korišćeni modeli:**

    :model:`doktor.Lekari` - informacije o doktoru

    :model:`doktor.Termini` - termini doktora

    :model:`doktor.Recenzije` - ocene i komentari pacijenata

    :model:`doktor.Klinike` - za prikaz informacija o klinikama

    :model:`doktor.OmiljeniLekari` - za proveru omiljenih lekara pacijenta

    **Template:**
    :template:`doktor_javni.html`
    """

    lekar = get_object_or_404(Lekari, user_id=id)

    # --- Recenzije ---
    recenzije_qs = Recenzije.objects.filter(lekar=lekar).order_by('-datum')
    prosecna_ocena = recenzije_qs.aggregate(Avg('ocena'))['ocena__avg'] or 'Nema ocena'

    paginator = Paginator(recenzije_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- Slobodni periodi (20-min slotovi) ---
    danas = datetime.now().date()
    slobodni_periodi = []

    for dan_offset in range(11):
        datum = danas + timedelta(days=dan_offset)
        if datum.weekday() >= 5:  # skip vikend
            continue

        pocetak_radnog = make_aware(datetime.combine(datum, time(9, 0)))
        kraj_radnog = make_aware(datetime.combine(datum, time(17, 0)))

        zauzeti = Termini.objects.filter(
            lekar=lekar,
            pocetak__date=datum,
            status__in=['zakazan', 'potvrđen', 'zavrsen']
        ).order_by('pocetak')

        slobodni = [(pocetak_radnog, kraj_radnog)]
        for t in zauzeti:
            zp = t.pocetak
            zk = t.kraj
            novi = []
            for s, e in slobodni:
                if e <= zp or s >= zk:
                    novi.append((s, e))
                else:
                    if s < zp: novi.append((s, zp))
                    if e > zk: novi.append((zk, e))
            slobodni = novi

        for start, end in slobodni:
            # ignorisanje prošlih termina
            if end <= timezone.now():
                continue

            trajanje = (end - start).total_seconds() / 60
            if trajanje >= 20:
                # ako početak već prošao, pomeri ga na sada
                if start < timezone.now():
                    start = timezone.now()
                    trajanje = (end - start).total_seconds() / 60
                slobodni_periodi.append({
                    'datum': start,
                    'pocetak': start.time(),
                    'kraj': end.time(),
                    'trajanje_max': min(int(trajanje), 60)
                })

    # --- Zakazivanje ---
    error = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'zakazi':
            pocetak_str = request.POST.get('pocetak')
            trajanje = int(request.POST.get('trajanje', 0))

            if trajanje not in [20, 40, 60]:
                error = 'Trajanje mora biti 20, 40 ili 60 minuta.'
            else:
                try:
                    pocetak = make_aware(datetime.fromisoformat(pocetak_str))
                    kraj = pocetak + timedelta(minutes=trajanje)

                    valid = False
                    for p in slobodni_periodi:
                        p_start = p['datum']
                        p_end = make_aware(datetime.combine(p_start.date(), p['kraj']))
                        if p_start <= pocetak <= p_end and kraj <= p_end and trajanje <= p['trajanje_max']:
                            valid = True
                            break

                    if not valid:
                        error = 'Izabrani termin nije slobodan.'
                    else:
                        multiplikator = trajanje / 20  # 20 minuta = osnovna cena
                        ukupna_cena = lekar.cena * multiplikator

                        termin = Termini.objects.create(
                            lekar=lekar,
                            pacijent=request.user if request.user.is_authenticated else None,
                            pocetak=pocetak,
                            kraj=kraj,
                            status='zakazan',
                            cena=ukupna_cena
                        )

                        obavesti_doktora_o_novom_termine.delay(termin.id)

                        return redirect('doktor_javni', id=id)

                except ValueError as e:
                    error = f'Greška u formatu vremena: {e}'

    # --- Priprema zauzetih termina za JS ---
    zauzeti_za_js = Termini.objects.filter(
        lekar=lekar,
        status__in=['zakazan', 'potvrđen', 'zavrsen']
    ).values_list('pocetak', 'kraj')

    zauzeti_termini_js = [
        {
            'start': localtime(p).strftime('%Y-%m-%dT%H:%M'),
            'end': localtime(k).strftime('%Y-%m-%dT%H:%M')
        }
        for p, k in zauzeti_za_js
    ]
    omiljeni = False
    if request.user.is_authenticated and request.user.role.name == 'pacijent':
        omiljeni = OmiljeniLekari.objects.filter(pacijent=request.user, lekar=lekar).exists()

    context = {
        'lekar': lekar,
        'recenzije': page_obj,
        'page_obj': page_obj,
        'prosecna_ocena': prosecna_ocena,
        'slobodni_periodi': slobodni_periodi,
        'error': error,
        'zauzeti_termini_js': zauzeti_termini_js,
        'sve_klinike': Klinike.objects.all(),
        'can_book': request.user.is_authenticated and getattr(request.user, 'role', None) and request.user.role.name == 'pacijent',
        'omiljeni':omiljeni,
        'cena_pregleda': lekar.cena,  # cena za 20 minuta

    }

    return render(request, 'doktor_javni.html', context)
