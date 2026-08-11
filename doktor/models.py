from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

from pacijent.geolocation import adresa_u_koordinate


class Role(models.Model):
    """**Uloga korisnika u sistemu** – opisuje tipove korisnika kao što su doktor, pacijent ili admin."""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'roles'


class Slika(models.Model):
    """**Slike u aplikaciji** – čuvaju slike za profile, aktuelnosti i recepte."""
    slika_link = models.ImageField(upload_to='slikeAktuelnosti/')

    class Meta:
        db_table = 'slika'


class User(AbstractUser):
    """**Korisnik** – predstavlja korisnika sistema sa ličnim podacima, ulogom i opcionalnom slikom."""
    ime = models.CharField(max_length=100)
    prezime = models.CharField(max_length=100)
    email = models.CharField(max_length=100, unique=True, null=True, blank=True)
    telefon = models.CharField(max_length=20, blank=True, null=True)
    datum_rodjenja = models.DateField(blank=True, null=True)
    medicinska_istorija = models.TextField(blank=True, null=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    verifikovan = models.BooleanField(default=False)
    slika = models.ForeignKey(Slika, on_delete=models.SET_NULL, null=True, blank=True)
    adresa = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.adresa and (self.latitude is None or self.longitude is None):
            lat, lon = adresa_u_koordinate(self.adresa)
            if lat and lon:
                self.latitude = lat
                self.longitude = lon
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.ime} {self.prezime}"

    class Meta:
        db_table = 'users'


class Klinike(models.Model):
    """**Klinika** – predstavlja medicinsku ustanovu sa nazivom, adresom, tipom(privatna/drzavna) i opcionalnom slikom."""
    naziv = models.CharField(max_length=150)
    adresa = models.CharField(max_length=200)
    grad = models.CharField(max_length=100, blank=True, null=True)
    tip = models.CharField(max_length=20, choices=[('privatna', 'Privatna'), ('drzavna', 'Državna')])
    radno_vreme = models.CharField(max_length=100, blank=True, null=True)
    verifikovana = models.BooleanField(default=False)
    slika = models.ForeignKey(Slika, on_delete=models.SET_NULL, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    def __str__(self):
        return self.naziv
    def save(self, *args, **kwargs):
        if self.adresa and (self.latitude is None or self.longitude is None):
            lat, lon = adresa_u_koordinate(self.adresa)
            if lat and lon:
                self.latitude = lat
                self.longitude = lon
        super().save(*args, **kwargs)
    class Meta:
        db_table = 'klinike'


class Lekari(models.Model):
    """**Doktor** – predstavlja doktora sa povezanim korisničkim nalogom, klinikom i specijalizacijom."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    klinika = models.ForeignKey(Klinike, on_delete=models.SET_NULL, null=True, blank=True)
    specijalizacija = models.CharField(max_length=150, blank=True, null=True)
    biografija = models.TextField(blank=True, null=True)
    cena = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Dr. {self.user.ime} {self.user.prezime}"

    class Meta:
        db_table = 'lekari'


class DoctorDocument(models.Model):
    """**Dokument doktora** – čuva sertifikate i licence vezane za doktore."""
    lekar = models.ForeignKey(Lekari, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='doctor_docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.lekar}"

    class Meta:
        db_table = 'doctor_documents'


class Termini(models.Model):
    """**Termin pregleda** – predstavlja zakazane termine između pacijenta i doktora sa statusom. Cuvaju se samo zauzeti."""
    STATUS_CHOICES = [
        ('zakazan', 'Zakazan'),
        ('otkazan', 'Otkazan'),
        ('zavrsen', 'Završen'),
        ('potvrđen', 'Potvrđen'),
    ]
    lekar = models.ForeignKey(Lekari, on_delete=models.CASCADE)
    pacijent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    pocetak = models.DateTimeField()
    kraj = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='slobodan')
    description = models.TextField(blank=True, null=True)
    prescription = models.TextField(blank=True, null=True)
    recept = models.ForeignKey('Recepti', on_delete=models.SET_NULL, null=True, blank=True)
    cena = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Termin {self.pocetak} - {self.kraj} ({self.status})"

    def is_past(self):
        return self.kraj < timezone.now()

    class Meta:
        db_table = 'termini'


class Aktuelnosti(models.Model):
    """**Aktuelnosti / vesti** – prikazuje vesti ili obaveštenja u sistemu sa autorom i datumom."""
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    naslov = models.CharField(max_length=200)
    sadrzaj = models.TextField()
    datum = models.DateTimeField(auto_now_add=True)
    slika = models.ForeignKey(Slika, on_delete=models.SET_NULL, null=True, blank=True)
    verifikovana = models.BooleanField(default=False)

    def __str__(self):
        return self.naslov

    class Meta:
        db_table = 'aktuelnosti'


class OmiljeniLekari(models.Model):
    """**Omiljeni lekari pacijenata** – čuva vezu između pacijenta i njegovih omiljenih lekara."""
    pacijent = models.ForeignKey(User, on_delete=models.CASCADE)
    lekar = models.ForeignKey(Lekari, on_delete=models.CASCADE)

    class Meta:
        db_table = 'omiljeni_lekari'
        unique_together = ('pacijent', 'lekar')



class Recenzije(models.Model):
    """**Recenzije pacijenata za doktore** – čuva ocene i komentare pacijenata za doktore."""
    pacijent = models.ForeignKey(User, on_delete=models.CASCADE)
    lekar = models.ForeignKey(Lekari, on_delete=models.CASCADE)
    ocena = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    komentar = models.TextField(blank=True, null=True)
    datum = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recenzija {self.lekar} od {self.pacijent}"

    class Meta:
        db_table = 'recenzije'


class Recepti(models.Model):
    """**Recepti** – čuva informacije o receptima koje doktori izdaju pacijentima."""
    lekar = models.ForeignKey(Lekari, on_delete=models.CASCADE)
    pacijent = models.ForeignKey(User, on_delete=models.CASCADE)
    datum = models.DateTimeField(auto_now_add=True)
    tekst = models.TextField()
    slika = models.ForeignKey(Slika, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Recept za {self.pacijent} od {self.lekar}"

    class Meta:
        db_table = 'recepti'

class Poruke(models.Model):
    posiljalac = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    primalac = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    tekst = models.TextField(blank=True)  # može biti prazno
    recept = models.ForeignKey(Recepti, null=True, blank=True, on_delete=models.SET_NULL)  # opcionalni fajl
    poslato = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Poruka od {self.posiljalac} do {self.primalac}"

    class Meta:
        db_table = 'poruke'

class UserDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='user_docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.user}"

    class Meta:
        db_table = 'user_documents'


class ClinicDocument(models.Model):
    clinic = models.ForeignKey(Klinike, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='clinic_docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.user}"

    class Meta:
        db_table = 'clinic_documents'