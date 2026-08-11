# Milos Milinkovic 0396/2022
from django.shortcuts import render, get_object_or_404
from doktor.models import Aktuelnosti
from django.db.models import Q

def aktuelnosti_lista(request):
    """
    Prikazuje listu verifikovanih vesti (aktuelnosti) sa opcijama pretrage i sortiranja.

    **Opis:**

    - Dohvata sve vesti koje su verifikovane
    - Omogućava pretragu po naslovu koristeći GET parametar `search`
    - Omogućava sortiranje po datumu ili naslovu koristeći GET parametar `sort`
    - Prosleđuje listu vesti i request objekt ka template-u

    **Korišćeni modeli:**

    :model:`doktor.Aktuelnosti` - vesti dodate od strane doktora ili administratora

    **Template:**
    :template:`lista_aktuelnosti.html`
    """

    # samo verifikovane vesti
    vesti = Aktuelnosti.objects.filter(verifikovana=True)

    search_query = request.GET.get('search', '')
    if search_query:
        vesti = vesti.filter(naslov__icontains=search_query)

    sort_option = request.GET.get('sort', 'datum')
    if sort_option == 'naslov':
        vesti = vesti.order_by('naslov')
    else:
        vesti = vesti.order_by('-datum')

    return render(request, 'lista_aktuelnosti.html', {
        'vesti': vesti,
        'request': request
    })



from django.shortcuts import render, get_object_or_404
from doktor.models import Aktuelnosti, Lekari

def aktuelnost_detalj(request, id):
    """
    Prikazuje detalje pojedinačne vesti.

    **Opis:**

    - Dohvata vest po ID-u ili vraća 404 ako ne postoji
    - Proverava da li je autor doktora; ako jeste, prikazuje informacije o doktoru
    - Prosleđuje vest i opcionalnog doktora ka template-u

    **Korišćeni modeli:**

    :model:`doktor.Aktuelnosti` - vest koja se prikazuje

    :model:`doktor.Lekari` - doktor koji je autor vesti (ako postoji)

    **Template:**
    :template:`detalj_aktuelnost.html`
    """

    vest = get_object_or_404(Aktuelnosti, id=id)

    if vest.autor.role.name != 'doktor':
        doktor_id = None
    else :
        doktor_id = vest.autor

    return render(request, 'detalj_aktuelnost.html', {
        'vest': vest,
        'doktor': doktor_id
    })

