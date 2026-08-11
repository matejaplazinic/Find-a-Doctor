# Milos Milinkovic 0396/2022
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from .models import Termini

@shared_task
def obavesti_o_izmeni_termina(termin_id):
    """
    Kada lekar promeni termin (status) pacijent dobija mejl obaveštenja.
    """
    try:
        termin = Termini.objects.get(id=termin_id)
        pacijent = termin.pacijent
        if pacijent and pacijent.email:
            vreme = timezone.localtime(termin.pocetak).strftime("%d.%m.%Y u %H:%M")
            poruka = (
                f"Poštovani {pacijent.ime},\n\n"
                f"Vaš termin kod doktora {termin.lekar.user.get_full_name()} je promenjen.\n"
                f"Vreme termina: {vreme}\n"
                f"Status termina: {termin.status}\n\n"
            )
            if termin.description:
                poruka += f"\nOpis posete:\n{termin.description}\n"

            poruka += "\nHvala na korišćenju naše platforme!"

            send_mail(
                subject="🔔 Obaveštenje o promeni termina",
                message=poruka,
                from_email="noreply@pronadjidoktora.rs",
                recipient_list=[pacijent.email],
                fail_silently=True
            )
    except Termini.DoesNotExist:
        pass


@shared_task
def obavesti_doktora_o_novom_termine(termin_id):
    """
    Kada pacijent zakazuje termin, lekar dobija mejl obaveštenja.
    """
    try:
        termin = Termini.objects.get(id=termin_id)
        lekar = termin.lekar
        if lekar and lekar.user.email:
            pocetak_local = timezone.localtime(termin.pocetak)
            kraj_local = timezone.localtime(termin.kraj)

            vreme = f"{pocetak_local.strftime('%d.%m.%Y')} {pocetak_local.strftime('%H:%M')} - {kraj_local.strftime('%H:%M')}"

            pacijent_ime = termin.pacijent.ime+ " " +termin.pacijent.prezime if termin.pacijent else "Nepoznati pacijent"

            poruka = (
                f"Poštovani {lekar.user.ime},\n\n"
                f"Zakazan je novi termin kod Vas.\n"
                f"Pacijent: {pacijent_ime}\n"
                f"Vreme termina: {vreme}\n"
                f"Status termina: {termin.status}\n\n"
                f"Hvala na korišćenju platforme!"
            )

            send_mail(
                subject="🔔 Novi zakazani termin",
                message=poruka,
                from_email="noreply@pronadjidoktora.rs",
                recipient_list=[lekar.user.email],
                fail_silently=True
            )
    except Termini.DoesNotExist:
        pass

