# Mateja Plazinic 2022/0335
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from doktor.models import Role, Lekari, Klinike, Termini, Aktuelnosti, Recenzije

User = get_user_model()


class HomeViewTest(TestCase):
    """Testira funkcionalnost pocetne stranice za razlicite korisnike."""

    # Postavljanje test podataka
    @classmethod
    def setUpTestData(cls):
        # Postavljanje trenutnog vremena
        cls.TEST_NOW = timezone.now()

        # 1. Kreiranje Uloga
        cls.doktor_role = Role.objects.create(name='doktor')
        cls.pacijent_role = Role.objects.create(name='pacijent')

        # 2. Kreiranje Korisnika
        # Napomena: Lekar mora biti verifikovan da bi se pojavio u top_doktori
        cls.doktor_user = User.objects.create_user(
            email='doktor.test@example.com',
            ime='Dragan',
            prezime='Doktoric',
            password='testpassword',
            role=cls.doktor_role,
            username='doktor.test',
            verifikovan=True  # OBAVEZNO ZA TEST PROLAZAK
        )
        cls.pacijent_user = User.objects.create_user(
            email='pacijent.test@example.com',
            ime='Pera',
            prezime='Peric',
            password='testpassword',
            role=cls.pacijent_role,
            username='pacijent.test'
        )

        # 3. Kreiranje Klinike
        cls.klinika = Klinike.objects.create(
            naziv='Test Klinika',
            adresa='Test Adresa 1',
            grad='Test Grad',
            tip='privatna',
            verifikovana=True
        )

        # 4. Kreiranje Lekara
        cls.lekar = Lekari.objects.create(
            user=cls.doktor_user,
            klinika=cls.klinika,
            specijalizacija='Kardiologija',
            cena=5000
        )

        # 5. Kreiranje Aktuelnosti (Vesti) - FIX: Dodato obavezno polje 'autor'
        for i in range(1, 7):
            Aktuelnosti.objects.create(
                autor=cls.doktor_user,
                naslov=f'Vest {i}',
                sadrzaj=f'Sadrzaj vesti {i} je duzi od 10 karaktera.',
                datum=timezone.now() - datetime.timedelta(days=i),
                verifikovana=(i <= 5)
            )

        # 6. Kreiranje Termina (Termini) - FIX: Dodato obavezno polje 'kraj'
        cls.zakazan_termin_pacijent = Termini.objects.create(
            lekar=cls.lekar,
            pacijent=cls.pacijent_user,
            pocetak=cls.TEST_NOW + datetime.timedelta(hours=1),
            kraj=cls.TEST_NOW + datetime.timedelta(hours=1, minutes=30),
            status='zakazan'
        )
        cls.termin_doktor = Termini.objects.create(
            lekar=cls.lekar,
            pacijent=None,
            pocetak=cls.TEST_NOW + datetime.timedelta(hours=2),
            kraj=cls.TEST_NOW + datetime.timedelta(hours=2, minutes=30),
            status='zakazan'
        )

        # 7. Kreiranje Recenzije
        Recenzije.objects.create(
            pacijent=cls.pacijent_user,
            lekar=cls.lekar,
            ocena=5,
            komentar='Odličan doktor'
        )

        cls.home_url = reverse('home')

    def test_gost_neprijavljen_korisnik(self):
        """Testira pocetnu stranicu za neprijavljenog korisnika (Gost)."""

        client = Client()
        response = client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

        # Provera ključnih podataka
        self.assertIn('vesti', response.context)
        self.assertEqual(len(response.context['vesti']), 5)

        self.assertIn('top_doktori', response.context)
        #self.assertIn('top_klinike', response.context)

        self.assertNotIn('termini', response.context)
        self.assertNotIn('zakazan', response.context)

    def test_pacijent_prijavljen(self):
        """Testira pocetnu stranicu za prijavljenog pacijenta. Ne treba da vidi termine."""

        client = Client()
        client.login(username=self.pacijent_user.username, password='testpassword')
        response = client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

        self.assertIn('top_doktori', response.context)
        #self.assertIn('top_klinike', response.context)

        self.assertNotIn('termini', response.context)
        self.assertNotIn('zakazan', response.context)

    def test_doktor_prijavljen(self):
        """Testira pocetnu stranicu za prijavljenog doktora. Treba da vidi svoje buduce termine."""
        client = Client()
        # Napomena: Koristimo username (email, ali ga test code prepoznaje kao username)
        client.login(username=self.doktor_user.username, password='testpassword')
        response = client.get(self.home_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

        # Provera da li su prisutni termini za doktora
        self.assertIn('termini', response.context)
        # Očekujemo 2 buduća termina
        self.assertGreaterEqual(len(response.context['termini']), 2)

        # Provera da NEMA klinika/doktora u kontekstu za doktora
        #self.assertNotIn('top_klinike', response.context)
        self.assertNotIn('top_doktori', response.context)