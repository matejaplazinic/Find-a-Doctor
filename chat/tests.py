from django.test import TestCase
from django.contrib.auth import get_user_model
from doktor.models import Poruke, Recepti, Lekari, Role

User = get_user_model()


class ChatBackendTests(TestCase):

    def setUp(self):
        self.role_user = Role.objects.create(name="pacijent")
        self.role_doctor = Role.objects.create(name="doktor")

        self.user1 = User.objects.create_user(
            username="pera",
            password="test123",
            role=self.role_user,
            ime="Pera",
            prezime="Peric",
            email="pera@example.com"
        )
        self.user2 = User.objects.create_user(
            username="mika",
            password="test123",
            role=self.role_user,
            ime="Mika",
            prezime="Mikic",
            email="mika@example.com"
        )

    def test_message_creation(self):
        poruka = Poruke.objects.create(
            posiljalac=self.user1,
            primalac=self.user2,
            tekst="Zdravo!"
        )

        self.assertEqual(poruka.posiljalac, self.user1)
        self.assertEqual(poruka.primalac, self.user2)
        self.assertEqual(poruka.tekst, "Zdravo!")
        self.assertIsNotNone(poruka.poslato)
        self.assertEqual(Poruke.objects.count(), 1)

    def test_messages_ordered_by_time(self):
        Poruke.objects.create(posiljalac=self.user1, primalac=self.user2, tekst="1")
        Poruke.objects.create(posiljalac=self.user1, primalac=self.user2, tekst="2")
        Poruke.objects.create(posiljalac=self.user1, primalac=self.user2, tekst="3")

        poruke = Poruke.objects.filter(
            posiljalac=self.user1, primalac=self.user2
        ).order_by("poslato")

        self.assertEqual(poruke[0].tekst, "1")
        self.assertEqual(poruke[1].tekst, "2")
        self.assertEqual(poruke[2].tekst, "3")

    def test_message_with_recept_file(self):
        lekar = Lekari.objects.create(user=self.user1)
        recept = Recepti.objects.create(
            lekar=lekar,
            pacijent=self.user2,
            tekst="Test recept"
        )

        poruka = Poruke.objects.create(
            posiljalac=self.user1,
            primalac=self.user2,
            tekst="Recept!",
            recept=recept
        )

        self.assertEqual(poruka.recept, recept)
        self.assertEqual(poruka.tekst, "Recept!")

    def test_message_from_doctor_to_patient(self):
        lekar = Lekari.objects.create(user=self.user1)
        poruka = Poruke.objects.create(
            posiljalac=self.user1,
            primalac=self.user2,
            tekst="Vaš recept je spreman"
        )
        self.assertEqual(poruka.posiljalac, self.user1)
        self.assertEqual(poruka.primalac, self.user2)

    def test_multiple_messages_between_users(self):
        for i in range(5):
            Poruke.objects.create(posiljalac=self.user1, primalac=self.user2, tekst=f"Poruka {i}")
        self.assertEqual(Poruke.objects.filter(posiljalac=self.user1, primalac=self.user2).count(), 5)

    def test_message_str_method(self):
        poruka = Poruke.objects.create(
            posiljalac=self.user1,
            primalac=self.user2,
            tekst="Zdravo"
        )
        self.assertIn("Pera", str(poruka))
        self.assertIn("Mika", str(poruka))

    def test_user_search_by_name(self):
        User.objects.create_user(
            username="luka",
            password="test123",
            role=self.role_user,
            ime="Luka",
            prezime="Lukic",
            email="luka@example.com"
        )

        rezultat = User.objects.filter(ime__icontains="Pera")
        self.assertEqual(len(rezultat), 1)
        self.assertEqual(rezultat[0].ime, "Pera")

        rezultat = User.objects.filter(ime__icontains="a")
        imena = [u.ime for u in rezultat]
        self.assertIn("Pera", imena)
        self.assertIn("Mika", imena)
        self.assertIn("Luka", imena)

    def test_user_search_no_results(self):
        rezultat = User.objects.filter(ime__icontains="NePostojiIme")
        self.assertEqual(len(rezultat), 0)

def test_message_combinations(self):
    lekar = Lekari.objects.create(user=self.user1)
    recept = Recepti.objects.create(
        lekar=lekar,
        pacijent=self.user2,
        tekst="Test recept"
    )

    poruka1 = Poruke.objects.create(
        posiljalac=self.user1,
        primalac=self.user2,
        tekst="Samo poruka"
    )
    self.assertEqual(poruka1.tekst, "Samo poruka")
    self.assertIsNone(poruka1.recept)

    poruka2 = Poruke.objects.create(
        posiljalac=self.user1,
        primalac=self.user2,
        tekst="",
        recept=recept
    )
    self.assertEqual(poruka2.recept, recept)
    self.assertEqual(poruka2.tekst, "")

    poruka3 = Poruke.objects.create(
        posiljalac=self.user1,
        primalac=self.user2,
        tekst="Poruka i recept",
        recept=recept
    )
    self.assertEqual(poruka3.tekst, "Poruka i recept")
    self.assertEqual(poruka3.recept, recept)
