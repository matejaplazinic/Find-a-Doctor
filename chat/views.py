# Vuk Luzanin 29/2022
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from doktor.models import User, Poruke, Slika, Recepti


@login_required
def chat(request, other_id=None):
    """
    Prikazuje chat interfejs između prijavljenog korisnika i izabranog korisnika.

    **Opis:**

    - Filtrira korisnike prema ulozi prijavljenog korisnika (doktor vidi pacijente i obrnuto).
    - Ako je 'other_id' prosleđen, prikazuje sve poruke između dva korisnika sortirane po vremenu.

    **Parametri:**

    :param request: HttpRequest objekat
    :param other_id: ID korisnika sa kojim se chatuje (opciono)

    **Povratna vrednost:**

    :return: Renderuje template 'chat.html' sa kontekstom:
        - other_users: lista korisnika za izbor
        - selected_user: trenutno izabrani korisnik
        - messages: lista poruka između korisnika
        - query: tekst pretrage

    **Korišćeni modeli:**

    :model:`doktor.User`

    :model:`doktor.Poruke`

    Template:
    :template: chat.html
    """
    user = request.user
    user_role = user.role.name.lower()

    if user_role == "doktor":
        other_users = User.objects.filter(role__name__iexact="pacijent")
    elif user_role == "pacijent":
        other_users = User.objects.filter(role__name__iexact="doktor")
    else:
        other_users = User.objects.none()

    query = request.GET.get("q", "")
    if query:
        other_users = other_users.filter(
            Q(ime__icontains=query) | Q(prezime__icontains=query)
        )

    selected_user = None
    messages = []

    if other_id:
        selected_user = get_object_or_404(User, id=other_id)
        messages = Poruke.objects.filter(
            Q(posiljalac=user, primalac=selected_user) |
            Q(posiljalac=selected_user, primalac=user)
        ).order_by("poslato")

    return render(request, "chat.html", {
        "other_users": other_users,
        "selected_user": selected_user,
        "messages": messages,
        "query": query,
    })


@login_required
@csrf_exempt
def upload_recept(request):
    """
    Omogućava slanje poruke i/ili recepta u chat-u.

    **Opis:**

    - Poruka može sadržati tekst, fajl recepta ili oba.
    - Ako korisnik ima lekarsku instancu, kreira se objekat Recepti.
    - Emituje poruku u realnom vremenu preko Django Channels.

    Parametri:

    :param request: HttpRequest sa POST podacima:

        - pacijent_id: ID pacijenta kome se šalje
        - message: tekst poruke (opciono)
        - recept_file: fajl recepta (opciono)

    Korišćeni modeli:

    :model:`doktor.User`

    :model:`doktor.Poruke`

    :model:`doktor.Recepti`

    :model:`doktor.Slika`
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST metoda je obavezna"})

    user = request.user
    pacijent_id = request.POST.get('pacijent_id')
    message = request.POST.get('message', '').strip()
    file = request.FILES.get('recept_file')

    pacijent = get_object_or_404(User, id=pacijent_id)

    recept_obj = None
    file_url = None
    file_name = None

    if file:
        slika_obj = Slika.objects.create(slika_link=file)
        if hasattr(user, "lekari"):
            recept_obj = Recepti.objects.create(
                lekar=user.lekari,
                pacijent=pacijent,
                tekst=message or file.name,
                slika=slika_obj
            )
        file_url = slika_obj.slika_link.url
        file_name = slika_obj.slika_link.name.split("/")[-1]

    if not message and not recept_obj:
        return JsonResponse({"success": False, "error": "Nema poruke ili fajla"})

    poruka_obj = Poruke.objects.create(
        posiljalac=user,
        primalac=pacijent,
        tekst=message or "",
        recept=recept_obj
    )

    timestamp = timezone.localtime(poruka_obj.poslato).strftime("%H:%M %d.%m.%Y")

    channel_layer = get_channel_layer()
    ids = sorted([user.id, pacijent.id])
    room_group_name = f"chat_{ids[0]}_{ids[1]}"

    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            "type": "chat_message",
            "message": poruka_obj.tekst,
            "sender_id": user.id,
            "timestamp": timestamp,
            "file_url": file_url,
            "file_name": file_name,
        }
    )

    return JsonResponse({"success": True})


@login_required
def chat_user_search(request):
    """
    Pretraga korisnika za chat prema imenu ili prezimenu.

    **Opis:**

    - Filtrira korisnike suprotne uloge u odnosu na prijavljenog korisnika.
    - Vraća JSON sa informacijama o korisnicima koji zadovoljavaju kriterijum pretrage.

    **Parametri:**

    :param request: HttpRequest sa GET parametrom 'q' (opciono)

    **Povratna vrednost:**

    :return: JsonResponse sa listom korisnika:
        - id
        - ime
        - prezime
        - role
        - slika_url
        - last_login

    **Korišćeni modeli:**

    :model:`doktor.User`
    """
    user = request.user
    role_name = user.role.name.lower()

    if role_name == "doktor":
        other_users = User.objects.filter(role__name__iexact="pacijent").select_related("role")
    elif role_name == "pacijent":
        other_users = User.objects.filter(role__name__iexact="doktor").select_related("role")
    else:
        other_users = User.objects.none()

    query = request.GET.get("q", "")
    if query:
        other_users = other_users.filter(Q(ime__icontains=query) | Q(prezime__icontains=query))

    users_list = [
        {
            "id": u.id,
            "ime": u.ime,
            "prezime": u.prezime,
            "role": u.role.name.lower(),
            "slika_url": getattr(u.slika, "slika_link.url", None),
            "last_login": u.last_login.strftime("%d.%m.%Y %H:%M") if u.last_login else "-"
        }
        for u in other_users
    ]

    return JsonResponse({"users": users_list})
