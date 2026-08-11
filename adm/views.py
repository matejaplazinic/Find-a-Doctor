# Autor - Davud Nusevic 2022/0076
from django.shortcuts import render, redirect, get_object_or_404
from .forms import *
from doktor.models import *
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from functools import wraps
from django.http import Http404
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import force_str


def admin_required(view_func):
    """
    Dekoracija koja omogucava samo adminima da pristupe view-u
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            raise Http404("Page not found.")

        if user.role.name != 'admin':
            raise Http404("Page not found.")

        return view_func(request, *args, **kwargs)
    return _wrapped_view


# Create your views here.
def login_view(request):
    """
    Obradjuje prijavu korisnika na sistem.

    **Opis:**

    - Ako je korisnik već prijavljen, preusmerava se na početnu stranicu.
    - Za POST zahtev proverava podatke za prijavu i autentifikuje korisnika.
    - Proverava da li je korisnik verifikovan pre prijave.
    - Nakon uspešne prijave, preusmerava korisnika na odgovarajuću stranicu:
        - Administratori se preusmeravaju na administratorsku stranicu
        - Ostali korisnici se preusmeravaju na početnu stranicu

    **Parametri:**

    :param request: HttpRequest objekat

    **Povratna vrednost:**

    :return:
        - Ako je korisnik prijavljen: redirect na 'home'
        - Za GET: Renderuje template 'login.html' sa praznom formom
        - Za POST: Renderuje template 'login.html' sa formom i porukama o greškama


    **Korišćeni modeli:**

    :model:`doktor.User`

    **Korišćeni formular:**

    :form:`LoginForm`

    **Template**:
    :template: login.html
    """
    if request.user.is_authenticated:
        return redirect('home')  # Prevent logged-in users from logging in again

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                # Look up user by email
                user_obj = User.objects.get(email=email)
            except ObjectDoesNotExist:
                messages.error(request, "Neispravan email ili sifra.")
                return render(request, "login.html", {"form": form})

            user = authenticate(request, username=user_obj.username, password=password)

            if user is None:
                messages.error(request, "Neispravan email ili sifra.")
            elif not user.verifikovan:
                messages.error(request, "Email nije verifikovan.")
            else:
                login(request, user)
                if user.role.name == 'admin':
                    return redirect('admin_view')
                return redirect('home')
        else:
            messages.error(request, "Molimo ispravite greske.")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


def register_view(request):
    """
    Obradjuje registraciju novog korisnika na sistem.

    **Opis:**

    - Ako je korisnik već prijavljen, preusmerava se na početnu stranicu.
    - Za POST zahtev kreira novog korisnika sa ulogom "pacijent".
    - Automatski generiše jedinstveno korisničko ime na osnovu imena i prezimena.
    - Čuva sve uploadovane dokumente korisnika.
    - Šalje verifikacioni email na unetu email adresu.
    - Koristi transakcioni pristup za garantovanje integriteta podataka.

    **Parametri:**

    :param request: HttpRequest objekat (sa POST podacima i FILES za dokumente)

    **Povratna vrednost:**

    :return:
        - Ako je korisnik prijavljen: redirect na 'home'
        - Za GET: Renderuje template 'register.html' sa praznom formom
        - Za POST:
            - Uspešna registracija: redirect na 'home'
            - Neuspešna registracija: Renderuje template 'register.html' sa formom i porukama o greškama

    **Korišćeni modeli:**

    :model:`doktor.User`
    :model:`doktor.Role`
    :model:`doktor.UserDocument`

    **Korišćeni formular:**

    :form:`UserRegisterForm`

    **Dodatne funkcionalnosti:**

    - Generisanje jedinstvenog username-a
    - Upload i čuvanje dokumenata
    - Slanje verifikacionog email-a
    - Atomske transakcije

    **Template**:
    :template: register.html
    :template: activate_email.html (za verifikacioni email)
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Generate a unique username
                    base_username = f"{form.cleaned_data['first_name']}_{form.cleaned_data['last_name']}".lower()
                    username = base_username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    # Retrieve role
                    try:
                        role = Role.objects.get(name="pacijent")
                    except ObjectDoesNotExist:
                        messages.error(request, "User role not found.")
                        return render(request, "register.html", {"form": form})

                    # Create user
                    user = User.objects.create_user(
                        username=username,
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        ime=form.cleaned_data['first_name'],
                        prezime=form.cleaned_data['last_name'],
                        medicinska_istorija=form.cleaned_data.get('medical_history', ''),
                        role=role,
                        datum_rodjenja=form.cleaned_data.get('birth_date'),
                        adresa=form.cleaned_data.get('address'),
                        telefon=form.cleaned_data.get('phone_number'),
                    )

                    # Save uploaded documents
                    for doc_file in request.FILES.getlist('docs'):
                        UserDocument.objects.create(user=user, file=doc_file)

                    token = default_token_generator.make_token(user)
                    # Send verification email
                    current_site = get_current_site(request)
                    subject = "Activate your account"
                    message = render_to_string('activate_email.html', {
                        'user': user,
                        'domain': current_site.domain,
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'token': token,
                    })
                    send_mail(subject, message, None, [user.email])

                    # Auto-login user
                    # login(request, user)
                    return redirect('home')

            except Exception as e:
                messages.error(request, f"Greska pri registraciji: {str(e)}")
        else:
            messages.error(request, "Molimo ispravite greske.")
    else:
        form = UserRegisterForm()

    return render(request, "register.html", {"form": form})


def logout_view(request):
    """
    Obradjuje odjavu korisnika sa sistema.

    **Opis:**

    - Proverava da li je korisnik trenutno prijavljen.
    - Ako je korisnik prijavljen, izvršava odjavu korisnika.
    - Nakon odjave, preusmerava korisnika na početnu stranicu.

    **Parametri:**

    :param request: HttpRequest objekat

    **Povratna vrednost:**

    :return:
        - Uvek preusmerava na 'home' (početnu stranicu)
        - Bez obzira da li je korisnik bio prijavljen ili ne

    **Template**:
    :template: Nema (samo redirect)
    """
    if request.user.is_authenticated:
        logout(request)
    return redirect('home')

def doctor_register_view(request):
    """
    Obradjuje registraciju novog doktora na sistem.

    **Opis:**

    - Ako je korisnik već prijavljen, preusmerava se na početnu stranicu.
    - Za POST zahtev kreira novog korisnika sa ulogom "doktor" i povezani Lekari profil.
    - Omogućava izbor postojeće klinike ili kreiranje nove klinike.
    - Validira sve obavezne podatke za novu kliniku (naziv, adresa, telefon, dokumenta).
    - Čuva sve uploadovane dokumente i za doktora i za kliniku.
    - Koristi transakcioni pristup za garantovanje integriteta podataka.

    **Parametri:**

    :param request: HttpRequest objekat (sa POST podacima i FILES za dokumente)

    **Povratna vrednost:**

    :return:
        - Ako je korisnik prijavljen: redirect na 'home'
        - Za GET: Renderuje template 'doctor_registration.html' sa praznom formom
        - Za POST:
            - Uspešna registracija: redirect na 'home'
            - Neuspešna registracija: Renderuje template 'doctor_registration.html' sa formom i porukama o greškama

    **Korišćeni modeli:**

    :model:`doktor.User`
    :model:`doktor.Role`
    :model:`doktor.Lekari`
    :model:`doktor.Klinike`
    :model:`doktor.DoctorDocument`
    :model:`doktor.ClinicDocument`

    **Korišćeni formular:**

    :form:`DoctorRegisterForm`


    **Template**:
    :template: doctor_registration.html
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        form = DoctorRegisterForm(request.POST, request.FILES)

        if form.is_valid():
            clinic_choice = form.cleaned_data.get('clinic')
            clinic = None

            if clinic_choice == '-1':
                messages.error(request, 'Klinika je obavezna.')
                return render(request, 'doctor_registration.html', {"form": form})

            elif clinic_choice == '0':
                if not form.cleaned_data.get('new_clinic_name', None):
                    messages.error(request, 'Ime klinike je obavezno')
                    return render(request, 'doctor_registration.html', {"form": form})
                elif not form.cleaned_data.get('new_clinic_address', None):
                    messages.error(request, 'Adresa klinike je obavezna')
                    return render(request, 'doctor_registration.html', {"form": form})
                elif not form.cleaned_data.get('new_clinic_phone', None):
                    messages.error(request, 'Telefon klinike je obavezan')
                    return render(request, 'doctor_registration.html', {"form": form})
                elif 'new_clinic_docs' not in request.FILES:
                    messages.error(request, 'Dokumenti klinike su obavezni')
                    return render(request, 'doctor_registration.html', {"form": form})

                clinic = Klinike(
                    naziv=form.cleaned_data['new_clinic_name'],
                    adresa=form.cleaned_data['new_clinic_address']
                )
            else:
                clinic = get_object_or_404(Klinike, pk=int(clinic_choice))

            try:
                role = Role.objects.get(name="doktor")
            except ObjectDoesNotExist:
                messages.error(request, "Doctor role not found.")
                return render(request, "register.html", {"form": form})

            user = User(
                username=f"{form.cleaned_data['first_name']}_{form.cleaned_data['last_name']}",
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                ime=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                prezime=form.cleaned_data['last_name'],
                role=role,
                datum_rodjenja=form.cleaned_data['birth_date'],
                adresa=form.cleaned_data['address'],
                telefon=form.cleaned_data['phone_number'],
            )
            user.set_password(form.cleaned_data['password'])

            with transaction.atomic():
                if clinic_choice == '0':
                    clinic.save()
                    for f in request.FILES.getlist('new_clinic_docs'):
                        ClinicDocument.objects.create(clinic=clinic, file=f)

                user.save()

                doctor = Lekari.objects.create(
                    user=user,
                    klinika=clinic,
                    specijalizacija=form.cleaned_data['speciality'],
                    biografija=form.cleaned_data['medical_history'],
                    cena=form.cleaned_data['price'], )

                for f in request.FILES.getlist('docs'):
                    DoctorDocument.objects.create(lekar=doctor, file=f)

            #login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Molimo ispravite greske.")
    else:
        form = DoctorRegisterForm()

    return render(request, 'doctor_registration.html', {"form": form})


@admin_required
def admin_view(request):
    """
    Prikazuje administratorski panel za verifikaciju doktora, klinika i vesti.

    **Opis:**

    - Dostupan samo administratorima (zaštićeno @admin_required dekoratorom).
    - Prikazuje različite sekcije u zavisnosti od 'action' parametra:
        - 'doctors': Prikazuje neverifikovane doktore i klinike sa njihovim dokumentima
        - 'news': Prikazuje neverifikovane vesti i formu za upload novih vesti

    **Parametri:**

    :param request: HttpRequest objekat
    :param action: GET parametar koji određuje akciju ('doctors' ili 'news')

    **Povratna vrednost:**

    :return: Renderuje template 'admin_panel.html' sa kontekstom:
        - Za action='doctors':
            - doctors: lista tuple-ova (Lekari objekat, QuerySet dokumenata)
            - clinics: lista tuple-ova (Klinike objekat, QuerySet dokumenata)
        - Za action='news':
            - news: QuerySet neverifikovanih vesti
            - form: NewsUploadForm instanca

    **Korišćeni modeli:**

    :model:`doktor.Lekari`
    :model:`doktor.Klinike`
    :model:`doktor.Aktuelnosti`
    :model:`doktor.DoctorDocument`
    :model:`doktor.ClinicDocument`

    **Korišćeni formular:**

    :form:`NewsUploadForm`

    **Dekoratori:**

    :decorator:`@admin_required` - omogućava pristup samo administratorima

    **Template**:
    :template: admin_panel.html
    """
    action = request.GET.get('action')

    context = {}
    if action == 'doctors':
        doctors = Lekari.objects.filter(user__verifikovan=False)
        clinics = Klinike.objects.filter(verifikovana=False)
        context['doctors'] = [(doc, doc.documents.all()) for doc in doctors]
        context['clinics'] = [(c, c.documents.all()) for c in clinics]
    elif action == 'news':
        news = Aktuelnosti.objects.filter(verifikovana=False)
        context['news'] = news
        context['form'] = NewsUploadForm()

    return render(request, 'admin_panel.html', context)


@admin_required
def verify_doctor(request, id):
    """
    Verifikuje doktora i ažurira prikaz administratorskog panela.

    **Opis:**

    - Dostupan samo administratorima (zaštićeno @admin_required dekoratorom).
    - Pronalazi doktora po ID-u i postavlja njegov status verifikovanog korisnika.
    - Nakon verifikacije, prikazuje ažuriranu listu neverifikovanih doktora i klinika.
    - Automatski se vraća na sekciju 'doctors' administratorskog panela.

    **Parametri:**

    :param request: HttpRequest objekat
    :param id: ID doktora (Lekari model) koji se verifikuje

    **Povratna vrednost:**

    :return: Renderuje template 'admin_panel.html' sa ažuriranim kontekstom:
        - doctors: lista tuple-ova neverifikovanih doktora (Lekari objekat, QuerySet dokumenata)
        - clinics: lista tuple-ova neverifikovanih klinika (Klinike objekat, QuerySet dokumenata)

    **Korišćeni modeli:**

    :model:`doktor.Lekari`
    :model:`doktor.Klinike`
    :model:`doktor.DoctorDocument`
    :model:`doktor.ClinicDocument`

    **Dekoratori:**

    :decorator:`@admin_required` - omogućava pristup samo administratorima

    **Template**:
    :template: admin_panel.html
    """
    doctor = Lekari.objects.get(pk=id)
    doctor.user.verifikovan = True
    doctor.user.save()

    context = {}
    doctors = Lekari.objects.filter(user__verifikovan=False)
    context['doctors'] = [(doc, doc.documents.all()) for doc in doctors]
    clinics = Klinike.objects.filter(verifikovana=False)
    context['clinics'] = [(c, c.documents.all()) for c in clinics]
    return render(request, 'admin_panel.html', context)


@admin_required
def verify_clinic(request, id):
    """
    Verifikuje kliniku i ažurira prikaz administratorskog panela.

    **Opis:**

    - Dostupan samo administratorima (zaštićeno @admin_required dekoratorom).
    - Pronalazi kliniku po ID-u i postavlja njen status na verifikovanu.
    - Nakon verifikacije, prikazuje ažuriranu listu neverifikovanih doktora i klinika.
    - Automatski se vraća na sekciju 'doctors' administratorskog panela.

    **Parametri:**

    :param request: HttpRequest objekat
    :param id: ID klinike (Klinike model) koja se verifikuje

    **Povratna vrednost:**

    :return: Renderuje template 'admin_panel.html' sa ažuriranim kontekstom:
        - doctors: lista tuple-ova neverifikovanih doktora (Lekari objekat, QuerySet dokumenata)
        - clinics: lista tuple-ova neverifikovanih klinika (Klinike objekat, QuerySet dokumenata)

    **Korišćeni modeli:**

    :model:`doktor.Klinike`
    :model:`doktor.Lekari`
    :model:`doktor.ClinicDocument`
    :model:`doktor.DoctorDocument`

    **Dekoratori:**

    :decorator:`@admin_required` - omogućava pristup samo administratorima

    **Template**:
    :template: admin_panel.html
    """
    clinic = Klinike.objects.get(pk=id)
    clinic.verifikovana = True
    clinic.save()

    context = {}
    doctors = Lekari.objects.filter(user__verifikovan=False)
    context['doctors'] = [(doc, doc.documents.all()) for doc in doctors]
    clinics = Klinike.objects.filter(verifikovana=False)
    context['clinics'] = [(c, c.documents.all()) for c in clinics]
    return render(request, 'admin_panel.html', context)


@admin_required
def verify_news(request, id):
    """
    Verifikuje vest i ažurira prikaz administratorskog panela.

    **Opis:**

    - Dostupan samo administratorima (zaštićeno @admin_required dekoratorom).
    - Pronalazi vest po ID-u i postavlja njen status na verifikovanu.
    - Nakon verifikacije, prikazuje ažuriranu listu neverifikovanih vesti.
    - Automatski se vraća na sekciju 'news' administratorskog panela.

    **Parametri:**

    :param request: HttpRequest objekat
    :param id: ID vesti (Aktuelnosti model) koja se verifikuje

    **Povratna vrednost:**

    :return: Renderuje template 'admin_panel.html' sa ažuriranim kontekstom:
        - news: QuerySet neverifikovanih vesti
        - form: NewsUploadForm instanca za upload novih vesti

    **Korišćeni modeli:**

    :model:`doktor.Aktuelnosti`

    **Korišćeni formular:**

    :form:`NewsUploadForm`

    **Dekoratori:**

    :decorator:`@admin_required` - omogućava pristup samo administratorima

    **Template**:
    :template: admin_panel.html
    """
    context = {}
    n = Aktuelnosti.objects.get(pk=id)
    n.verifikovana = True
    n.save()
    news = Aktuelnosti.objects.filter(verifikovana=False)
    context['news'] = news
    context['form'] = NewsUploadForm()
    return render(request, 'admin_panel.html', context)


@admin_required
def admin_news_upload(request):
    """
    Obradjuje upload novih vesti od strane administratora.

    **Opis:**

    - Dostupan samo administratorima (zaštićeno @admin_required dekoratorom).
    - Za POST zahtev kreira novu vest sa automatskom verifikacijom.
    - Obradjuje upload slike za vest (uzima samo prvu uploadovanu sliku).
    - Vest se automatski označava kao verifikovana i povezuje sa trenutnim administratorom kao autorom.
    - Nakon obrade, prikazuje ažuriranu listu neverifikovanih vesti.

    **Parametri:**

    :param request: HttpRequest objekat (sa POST podacima i FILES za sliku)

    **Povratna vrednost:**

    :return: Uvek renderuje template 'admin_panel.html' sa kontekstom:
        - news: QuerySet neverifikovanih vesti
        - form: NewsUploadForm instanca

    **Korišćeni modeli:**

    :model:`doktor.Aktuelnosti`
    :model:`doktor.Slika`

    **Korišćeni formular:**

    :form:`NewsUploadForm`

    **Dekoratori:**

    :decorator:`@admin_required` - omogućava pristup samo administratorima

    **Template**:
    :template: admin_panel.html
    """
    if request.method == 'POST':
        form = NewsUploadForm(request.POST, request.FILES)
        if form.is_valid():
            news = Aktuelnosti(
                naslov = form.cleaned_data['title'],
                sadrzaj = form.cleaned_data['content'],
                verifikovana = True,
                autor = request.user,
            )

            img = request.FILES.getlist('image')
            for f in img:
                news.slika = Slika.objects.create(slika_link=f)
                break

            news.save()

    context = {}
    news = Aktuelnosti.objects.filter(verifikovana=False)
    context['news'] = news
    context['form'] = NewsUploadForm()
    return render(request, 'admin_panel.html', context)


def activate(request, uidb64, token):
    """
    Aktivira korisnički nalog putem verifikacionog linka.

    **Opis:**

    - Dekodira user ID iz base64 formata i proverava validnost tokena.
    - Ako su podaci validni, označava korisnički nalog kao verifikovan.
    - Implementira mehanizam za verifikaciju email adrese.

    **Parametri:**

    :param request: HttpRequest objekat
    :param uidb64: User ID kodiran u base64 formatu
    :param token: Token za verifikaciju generisan od strane sistema

    **Povratna vrednost:**

    :return: HttpResponse sa porukom o statusu:
        - "Your account has been activated. You can now log in." - uspešna aktivacija
        - "Activation link is invalid or expired." - neuspešna aktivacija

    **Korišćeni modeli:**

    :model:`doktor.User`

    **Template**:
    :template: Nema (vraća direktan HTTP odgovor)
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        print(f"Decoded UID: {uid}")  # Debug
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.verifikovan = True
        user.save()
        return HttpResponse("Your account has been activated. You can now log in.")
    else:
        return HttpResponse("Activation link is invalid or expired.")
