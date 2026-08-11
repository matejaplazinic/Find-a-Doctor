# Mateja Plazinic 2022/0335
import datetime
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from .models import Lekari, Termini, Aktuelnosti, DoctorDocument, User, Recepti, Slika, OmiljeniLekari, Role, Klinike

APP_NAME = 'doktor'

@patch(f'{APP_NAME}.views.obavesti_o_izmeni_termina')
@patch(f'{APP_NAME}.views.obavesti_doktora_o_novom_termine')
class DoctorProfileTest(TestCase):
    DOCTOR_PROFILE_URL = reverse('doctor_profile')

    @classmethod
    def setUpTestData(cls):
        cls.doktor_role, _ = Role.objects.get_or_create(name='doktor')
        cls.pacijent_role, _ = Role.objects.get_or_create(name='pacijent')

        cls.korisnik = User.objects.create_user(
            username='testdoktor', email='d@d.com', password='testpassword',
            role=cls.doktor_role, ime='Test', prezime='Doktor', verifikovan=True
        )
        cls.klinika = Klinike.objects.create(naziv='Test Klinika', adresa='Adresa 1')
        cls.doktor = Lekari.objects.create(user=cls.korisnik, cena=50, klinika=cls.klinika)

        cls.pacijent = User.objects.create_user(
            username='testpacijent', email='p@p.com', password='testpassword',
            role=cls.pacijent_role, ime='Test', prezime='Pacijent'
        )

        # FIKSIRANI TERMIN
        cls.termin = Termini.objects.create(
            pacijent=cls.pacijent,
            lekar=cls.doktor,
            pocetak=timezone.make_aware(datetime.datetime(2025, 10, 28, 9, 0)),
            kraj=timezone.make_aware(datetime.datetime(2025, 10, 28, 9, 30)),
            status='zakazan',
            cena=75.0
        )

    def setUp(self):
        self.client.force_login(self.korisnik)
        self.dummy_slika = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
        self.dummy_doc = SimpleUploadedFile("test.pdf", b"pdf_content", content_type="application/pdf")
        self.dummy_doc2 = SimpleUploadedFile("test2.pdf", b"pdf_content_2", content_type="application/pdf")

    @patch(f'{APP_NAME}.views.Slika.objects.create')
    @patch(f'{APP_NAME}.views.DoctorDocument.objects.create')
    def test_POST_edit_doctor(self, mock_doc_create, mock_slika_create, mock_obavesti_novi, mock_obavesti_izmena):
        mock_slika_create.return_value = MagicMock(spec=Slika)
        mock_doc_create.return_value = MagicMock(spec=DoctorDocument)

        # Kreiraj prave SimpleUploadedFile objekte
        doc_file1 = SimpleUploadedFile("test1.pdf", b"pdf_content_1", content_type="application/pdf")
        doc_file2 = SimpleUploadedFile("test2.pdf", b"pdf_content_2", content_type="application/pdf")
        profile_img = SimpleUploadedFile("profile.jpg", b"image_content", content_type="image/jpeg")

        data = {
            'action': 'edit_doctor',
            'doc_name': 'Novi Ime Prezime',
            'doc_email': 'novi@email.com',
            'doc_spec': 'Hirurgija',
            'doc_cena': 65,
            'telefon_': '123456789'
        }

        # Koristi običan dict za fajlove
        response = self.client.post(self.DOCTOR_PROFILE_URL, data, files={
            'doc_files': [doc_file1, doc_file2],
            'profile_image': profile_img
        })

        self.assertEqual(response.status_code, 302)

        self.doktor.user.refresh_from_db()
        self.doktor.refresh_from_db()
        self.assertEqual(self.doktor.user.ime, 'Novi')
        self.assertEqual(self.doktor.cena, 65)

        # Proveri da li je create pozvan
        print(f"Mock doc create call count: {mock_doc_create.call_count}")

    def test_POST_accept_termin(self, mock_obavesti_novi, mock_obavesti_izmena):
        mock_obavesti_izmena.delay.reset_mock()
        response = self.client.post(self.DOCTOR_PROFILE_URL, {'action': 'accept', 'termin_id': self.termin.id})
        self.assertEqual(response.status_code, 302)
        self.termin.refresh_from_db()
        self.assertEqual(self.termin.status, 'potvrđen')
        mock_obavesti_izmena.delay.assert_called_once_with(self.termin.id)

    def test_POST_reject_termin(self, mock_obavesti_novi, mock_obavesti_izmena):
        mock_obavesti_izmena.delay.reset_mock()
        response = self.client.post(self.DOCTOR_PROFILE_URL, {'action': 'reject', 'termin_id': self.termin.id})
        self.assertEqual(response.status_code, 302)
        self.termin.refresh_from_db()
        self.assertEqual(self.termin.status, 'otkazan')
        mock_obavesti_izmena.delay.assert_called_once_with(self.termin.id)

    @patch(f'{APP_NAME}.views.Slika.objects.create')
    def test_POST_finish_termin_sa_receptom_i_slikom(self, mock_slika_create, mock_obavesti_novi, mock_obavesti_izmena):
        mock_obavesti_izmena.delay.reset_mock()
        mock_slika_create.return_value = MagicMock(spec=Slika)
        initial_recept_count = Recepti.objects.count()

        data = {
            'action': 'finish',
            'termin_id': self.termin.id,
            'description': 'Dijagnoza: Prehlada',
            'recept_tekst': 'Lek A, Lek B',
        }
        files = {'recept_slika': self.dummy_slika}
        response = self.client.post(self.DOCTOR_PROFILE_URL, data, files=files)
        self.assertEqual(response.status_code, 302)
        self.termin.refresh_from_db()
        self.assertEqual(self.termin.status, 'zavrsen')
        self.assertEqual(Recepti.objects.count(), initial_recept_count + 1)
        mock_obavesti_izmena.delay.assert_called_once_with(self.termin.id)

    @patch(f'{APP_NAME}.views.Slika.objects.create')
    def test_POST_add_news(self, mock_slika_create, mock_obavesti_novi, mock_obavesti_izmena):
        mock_slika_create.return_value = MagicMock(spec=Slika)
        initial_count = Aktuelnosti.objects.count()
        data = {'action': 'add_news', 'news_title': 'Nova Vesti', 'news_content': 'Sadržaj vesti.'}
        files = {'news_image': self.dummy_slika}
        response = self.client.post(self.DOCTOR_PROFILE_URL, data, files=files)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Aktuelnosti.objects.count(), initial_count + 1)

    def test_GET_prikaz_profila(self, mock_obavesti_novi, mock_obavesti_izmena):
        response = self.client.get(self.DOCTOR_PROFILE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn('lekar', response.context)
        self.assertEqual(response.context['lekar'], self.doktor)

    def test_redirekcija_za_neprijavljenog_korisnika(self, mock_obavesti_novi, mock_obavesti_izmena):
        self.client.logout()
        response = self.client.get(self.DOCTOR_PROFILE_URL)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/login/?next={self.DOCTOR_PROFILE_URL}')

    def test_redirekcija_za_korisnika_koji_nije_doktor(self, mock_obavesti_novi, mock_obavesti_izmena):
        self.client.force_login(self.pacijent)
        response = self.client.get(self.DOCTOR_PROFILE_URL)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))


@patch(f'{APP_NAME}.views.obavesti_doktora_o_novom_termine')
class DoktorJavniTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.doktor_role, _ = Role.objects.get_or_create(name='doktor')
        cls.pacijent_role, _ = Role.objects.get_or_create(name='pacijent')

        cls.doktor_user = User.objects.create(id=10, username='dr_javni', email='dr@javni.com',
                                              role=cls.doktor_role, ime='Javni', prezime='Lekar', verifikovan=True)
        cls.doktor = Lekari.objects.create(user=cls.doktor_user, cena=50)

        cls.pacijent = User.objects.create(id=11, username='pacijent_javni', email='p@javni.com',
                                           role=cls.pacijent_role, ime='Javni', prezime='Pacijent')

        cls.zauzet_pocetak = timezone.make_aware(datetime.datetime(2025, 10, 28, 10, 0))
        cls.zauzet_kraj = timezone.make_aware(datetime.datetime(2025, 10, 28, 10, 20))
        cls.zauzet_termin = Termini.objects.create(
            lekar=cls.doktor,
            pacijent=cls.pacijent,
            pocetak=cls.zauzet_pocetak,
            kraj=cls.zauzet_kraj,
            status='potvrđen',
            cena=50.0
        )

    def setUp(self):
        self.url = reverse('doktor_javni', args=[self.doktor.user.id])

    def test_GET_prikaz_profila(self, mock_obavesti_novi):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('lekar', response.context)

    def test_omiljeni_lekar_prikazan(self, mock_obavesti_novi):
        self.client.force_login(self.pacijent)
        OmiljeniLekari.objects.create(pacijent=self.pacijent, lekar=self.doktor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['omiljeni'])

    def test_POST_zakazivanje_uspesno(self, mock_obavesti_novi):
        self.client.force_login(self.pacijent)
        mock_obavesti_novi.delay.reset_mock()

        # Koristi naive datetime za budući termin
        pocetak_termina = datetime.datetime(2025, 10, 29, 12, 0)
        data = {'action': 'zakazi', 'pocetak': pocetak_termina.isoformat(), 'trajanje': 20}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)

        aware_pocetak = timezone.make_aware(pocetak_termina)
        self.assertTrue(Termini.objects.filter(lekar=self.doktor, pocetak=aware_pocetak).exists())
        mock_obavesti_novi.delay.assert_called_once()

    def test_POST_zakazivanje_duze_trajanje(self, mock_obavesti_novi):
        self.client.force_login(self.pacijent)
        mock_obavesti_novi.delay.reset_mock()

        pocetak_termina = datetime.datetime(2025, 10, 29, 13, 0)
        data = {'action': 'zakazi', 'pocetak': pocetak_termina.isoformat(), 'trajanje': 60}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)

        aware_pocetak = timezone.make_aware(pocetak_termina)
        termin = Termini.objects.get(lekar=self.doktor, pocetak=aware_pocetak)
        self.assertEqual(termin.cena, self.doktor.cena * 3)
        mock_obavesti_novi.delay.assert_called_once()