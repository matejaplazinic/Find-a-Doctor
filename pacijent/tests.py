# Milos Milinkovic 0396/2022
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Avg
from datetime import datetime, timedelta, date
from django.utils import timezone

from doktor.models import Lekari, Termini, Recepti, OmiljeniLekari, Recenzije, Slika, Klinike,Role,User


class PacijentViewsTests(TestCase):
    @patch('doktor.models.adresa_u_koordinate', return_value=(45.0, 19.8))
    def setUp(self,mock_geo):
        self.client = Client()

        # 🔹 Kreiramo uloge
        self.role_pacijent = Role.objects.create(name='pacijent')
        self.role_lekar = Role.objects.create(name='lekar')

        # 🔹 Kreiramo pacijenta
        self.pacijent = User.objects.create_user(
            username='pera',
            password='test123',
            ime='Pera',
            prezime='Perić',
            role=self.role_pacijent,
            email='pera@example.com'
        )

        # 🔹 Kreiramo lekara
        self.lekar_user = User.objects.create_user(
            username='doktor',
            password='test123',
            ime='Milan',
            prezime='Milić',
            role=self.role_lekar,
            verifikovan=True
        )
        self.klinika = Klinike.objects.create(
            naziv='Klinika Sunce',
            adresa='Novi Sad, Bulevar Oslobodjenja 1',
            tip='privatna',
            verifikovana=True
        )
        self.lekar = Lekari.objects.create(user=self.lekar_user, klinika=self.klinika, specijalizacija='Kardiolog')

        self.client.login(username='pera', password='test123')

    # ---------------- pacijent_profile ----------------

    def test_get_pacijent_profile(self):
        """GET na pacijent_profile vraća stranicu i kontekst"""
        response = self.client.get(reverse('pacijent_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('appointments', response.context)
        self.assertTemplateUsed(response, 'profil.html')

    def test_edit_pacijent_post(self):
        """Pacijent može ažurirati svoje podatke"""
        response = self.client.post(reverse('pacijent_profile'), {
            'action': 'edit_pacijent',
            'ime': 'Novo',
            'prezime': 'Prezime',
            'email': 'novo@example.com',
            'telefon': '12345',
            'medicinska_istorija': 'Alergija na penicilin'
        })
        self.pacijent.refresh_from_db()
        self.assertEqual(self.pacijent.ime, 'Novo')
        self.assertRedirects(response, reverse('pacijent_profile'))

    def test_edit_pacijent_with_image(self):
        """Test upload profilne slike"""
        image = SimpleUploadedFile("slika.jpg", b"fakecontent", content_type="image/jpeg")
        response = self.client.post(reverse('pacijent_profile'), {
            'action': 'edit_pacijent',
            'slika': image
        })
        self.pacijent.refresh_from_db()
        self.assertIsNotNone(self.pacijent.slika)
        self.assertRedirects(response, reverse('pacijent_profile'))

    # ---------------- dodaj_u_omiljene ----------------

    def test_dodaj_u_omiljene_uspesno(self):
        """Pacijent može dodati lekara u omiljene"""
        response = self.client.get(reverse('dodaj_omiljene', args=[self.lekar.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(OmiljeniLekari.objects.filter(pacijent=self.pacijent, lekar=self.lekar).exists())

    def test_dodaj_u_omiljene_ponovo(self):
        """Ako lekar već postoji u omiljenima, vraća exists"""
        OmiljeniLekari.objects.create(pacijent=self.pacijent, lekar=self.lekar)
        response = self.client.get(reverse('dodaj_omiljene', args=[self.lekar.id]))
        self.assertJSONEqual(response.content, {'status': 'exists', 'message': 'Lekar je već u omiljenim.'})

    # ---------------- ukloni_omiljenog ----------------

    def test_ukloni_omiljenog_uspesno(self):
        """Pacijent može ukloniti lekara iz omiljenih"""
        OmiljeniLekari.objects.create(pacijent=self.pacijent, lekar=self.lekar)
        response = self.client.post(reverse('ukloni_omiljenog'), {'lekar_id': self.lekar.id})
        self.assertJSONEqual(response.content, {'success': True})
        self.assertFalse(OmiljeniLekari.objects.filter(pacijent=self.pacijent, lekar=self.lekar).exists())

    def test_ukloni_omiljenog_nepostojeci(self):
        """Uklanjanje nepostojećeg lekara"""
        response = self.client.post(reverse('ukloni_omiljenog'), {'lekar_id': 999})
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    # ---------------- dodaj_recenziju ----------------

    def test_dodaj_recenziju_nova(self):
        """Dodavanje nove recenzije"""
        response = self.client.post(reverse('dodaj_recenziju'), {
            'lekar_id': self.lekar.id,
            'ocena': 5,
            'komentar': 'Odličan doktor!'
        })
        self.assertEqual(response.status_code, 200)
        rec = Recenzije.objects.get(lekar=self.lekar, pacijent=self.pacijent)
        self.assertEqual(rec.ocena, 5)
        self.assertEqual(rec.komentar, 'Odličan doktor!')

    def test_dodaj_recenziju_update(self):
        """Ažuriranje postojeće recenzije"""
        Recenzije.objects.create(lekar=self.lekar, pacijent=self.pacijent, ocena=3, komentar="ok")
        response = self.client.post(reverse('dodaj_recenziju'), {
            'lekar_id': self.lekar.id,
            'ocena': 4,
            'komentar': 'Bolje sada'
        })
        self.assertEqual(response.status_code, 200)
        rec = Recenzije.objects.get(lekar=self.lekar, pacijent=self.pacijent)
        self.assertEqual(rec.ocena, 4)
        self.assertEqual(rec.komentar, 'Bolje sada')

    def test_dodaj_recenziju_nevalidna_ocena(self):
        """Nevažeća ocena vraća 400"""
        response = self.client.post(reverse('dodaj_recenziju'), {
            'lekar_id': self.lekar.id,
            'ocena': 10
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

    def test_dodaj_recenziju_nepostojeci_lekar(self):
        """Ako lekar ne postoji"""
        response = self.client.post(reverse('dodaj_recenziju'), {
            'lekar_id': 999,
            'ocena': 5
        })
        self.assertEqual(response.status_code, 404)

    # ---------------- pretraga ----------------

    def test_pretraga_get(self):
        """Osnovni GET za pretragu"""
        response = self.client.get(reverse('pretraga'), {'q': 'Milan'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pretraga.html')
        self.assertIn('rezultati', response.context)