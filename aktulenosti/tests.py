# Vuk Luzanin 29/2022
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from doktor.models import Role, Lekari, Aktuelnosti

User = get_user_model()


class AktuelnostiTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.doktor_role = Role.objects.create(name='doktor')
        cls.pacijent_role = Role.objects.create(name='pacijent')
        cls.admin_role = Role.objects.create(name='admin')

        cls.autor_doktor = User.objects.create_user(
            email='doktor.autor@example.com',
            ime='Autor',
            prezime='Doktor',
            password='testpassword',
            role=cls.doktor_role,
            username='autor.doktor'
        )
        cls.autor_admin = User.objects.create_user(
            email='admin.autor@example.com',
            ime='Autor',
            prezime='Admin',
            password='testpassword',
            role=cls.admin_role,
            username='autor.admin'
        )
        cls.lekar_autor = Lekari.objects.create(
            user=cls.autor_doktor,
            specijalizacija='Opšta'
        )

        cls.vest_stara = Aktuelnosti.objects.create(
            autor=cls.autor_doktor,
            naslov='AAA Stara Test Vest',
            sadrzaj='Sadržaj stare vesti',
            datum=timezone.now() - datetime.timedelta(days=10),
            verifikovana=True
        )
        cls.vest_nova = Aktuelnosti.objects.create(
            autor=cls.autor_admin,
            naslov='BBB Nova Test Vest',
            sadrzaj='Sadržaj nove vesti',
            datum=timezone.now() - datetime.timedelta(days=5),
            verifikovana=True
        )
        cls.vest_nevalidna = Aktuelnosti.objects.create(
            autor=cls.autor_admin,
            naslov='CCC Neverifikovana Vest',
            sadrzaj='Sadržaj neverifikovane vesti',
            datum=timezone.now() - datetime.timedelta(days=1),
            verifikovana=False
        )

        cls.lista_url = reverse('aktuelnosti_lista')
        cls.detalj_stara_url = reverse('aktuelnost_detalj', args=[cls.vest_stara.id])
        cls.detalj_nova_url = reverse('aktuelnost_detalj', args=[cls.vest_nova.id])

    def test_lista_prikazuje_samo_verifikovane(self):
        response = self.client.get(self.lista_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lista_aktuelnosti.html')

        self.assertEqual(len(response.context['vesti']), 2)
        self.assertNotIn(self.vest_nevalidna, response.context['vesti'])
        self.assertIn(self.vest_stara, response.context['vesti'])
        self.assertIn(self.vest_nova, response.context['vesti'])

    def test_lista_sortiranje_po_datumu_podrazumevano(self):
        response = self.client.get(self.lista_url)

        self.assertEqual(response.context['vesti'][0], self.vest_nova)
        self.assertEqual(response.context['vesti'][1], self.vest_stara)

    def test_lista_sortiranje_po_naslovu(self):
        response = self.client.get(self.lista_url + '?sort=naslov')

        self.assertEqual(response.context['vesti'][0], self.vest_stara)
        self.assertEqual(response.context['vesti'][1], self.vest_nova)

    def test_lista_pretraga_po_naslovu(self):
        response = self.client.get(self.lista_url + '?search=Nova')

        self.assertEqual(len(response.context['vesti']), 1)
        self.assertEqual(response.context['vesti'][0], self.vest_nova)

        response_all = self.client.get(self.lista_url + '?search=Test Vest')
        self.assertEqual(len(response_all.context['vesti']), 2)

    def test_detalj_prikazuje_vest(self):
        response = self.client.get(self.detalj_stara_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'detalj_aktuelnost.html')
        self.assertEqual(response.context['vest'].naslov, 'AAA Stara Test Vest')

    def test_detalj_autor_je_doktor(self):
        response = self.client.get(self.detalj_stara_url)

        self.assertIn('doktor', response.context)

        self.assertEqual(response.context['doktor'].pk, self.autor_doktor.pk)
        self.assertEqual(response.context['doktor'].ime, self.autor_doktor.ime)
        self.assertIsInstance(response.context['doktor'], User)

    def test_detalj_autor_nije_doktor(self):
        response = self.client.get(self.detalj_nova_url)
        self.assertIn('doktor', response.context)
        self.assertIsNone(response.context['doktor'])

    def test_detalj_nepostojeca_vest(self):
        response = self.client.get(reverse('aktuelnost_detalj', args=[99999]))
        self.assertEqual(response.status_code, 404)