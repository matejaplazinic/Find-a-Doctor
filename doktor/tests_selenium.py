from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import os
from doktor.models import *
import tempfile
from django.urls import reverse
from selenium.webdriver.support.ui import Select


User = get_user_model()


class DoctorProfileTests(StaticLiveServerTestCase):
    """Test cases for doctor_profile view"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = webdriver.Firefox()  # Make sure chromedriver is in PATH
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
        # Create roles
        self.doctor_role = Role.objects.create(name='doktor')
        self.patient_role = Role.objects.create(name='pacijent')

        # Create doctor user
        self.doctor_user = User.objects.create_user(
            username='doctor_test',
            password='testpass123',
            ime='John',
            prezime='Doe',
            email='doctor@test.com',
            role=self.doctor_role,
            verifikovan=True
        )

        # Create clinic
        self.clinic = Klinike.objects.create(
            naziv="Test Klinika",
            adresa="Test Adresa 123",
            grad="Test Grad",
            tip="privatna",
            radno_vreme="08:00-16:00",
            verifikovana=True,
            latitude=44.786568,  # Set directly
            longitude=20.448921  # Set directly
        )

        # Create doctor profile
        self.doctor = Lekari.objects.create(
            user=self.doctor_user,
            klinika=self.clinic,
            specijalizacija='Cardiology',
            cena=2000,
        )

    # Create test image
    # self.test_image = Slika.objects.create(slika_link='test_images/profile.jpg')
    def login_doctor(self):
        """Helper method to log in as doctor"""
        self.selenium.get(f"{self.live_server_url}/login")
        email_input = self.selenium.find_element(By.NAME, "email")
        password_input = self.selenium.find_element(By.NAME, "password")
        email_input.send_keys('doctor@test.com')
        password_input.send_keys('testpass123')

        submit_button = self.selenium.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()

        self.selenium.implicitly_wait(10)
        self.assertIn('/', self.selenium.current_url)

    def test_doctor_profile_access_without_login(self):
        """Test that unauthenticated users are redirected from doctor profile"""
        self.selenium.get(f"{self.live_server_url}/doctor-profile/")

        # Should redirect to login page
        WebDriverWait(self.selenium, 10).until(
            EC.url_contains("/login")
        )

    def test_doctor_profile_access_as_doctor(self):
        """Test that doctor can access their profile"""
        self.login_doctor()

        # Check if doctor info is displayed
        self.selenium.get(f"{self.live_server_url}/doctor-profile/")
        self.selenium.implicitly_wait(10)
        content = self.selenium.page_source
        self.assertIn('John', content)
        self.assertIn('Cardiology', content)


    def test_doctor_profile_edit_functionality(self):
        """Test doctor profile editing functionality"""
        self.login_doctor()
        self.selenium.get(f"{self.live_server_url}/doctor-profile/")
        self.selenium.implicitly_wait(10)

        # Click edit profile button
        edit_button = self.selenium.find_element(By.ID, "enableEditBtn")
        edit_button.click()

        self.selenium.implicitly_wait(10)

        # Fill edit form
        name_input = self.selenium.find_element(By.NAME, "doc_name")
        name_input.clear()
        name_input.send_keys('Dr. Jane Smith')

        email_input = self.selenium.find_element(By.NAME, "doc_email")
        email_input.clear()
        email_input.send_keys('jane.smith@test.com')

        specialization_input = self.selenium.find_element(By.NAME, "doc_spec")
        specialization_input.clear()
        specialization_input.send_keys('Neurology')

        # Submit the form
        submit_button = self.selenium.find_element(By.XPATH, "//button[@type='submit' and contains(text(), 'Sačuvaj')]")
        submit_button.click()

        # Wait for page reload and check success
        self.selenium.implicitly_wait(10)
        content = self.selenium.page_source
        self.assertIn('Neurology', content)

    def test_doctor_termin_management(self):
        """Test doctor can manage appointments"""
        self.login_doctor()
        self.selenium.get(f"{self.live_server_url}/doctor-profile/")

        # Create a test appointment first
        patient_user = User.objects.create_user(
            username='patient_test',
            password='testpass123',
            ime='Patient',
            prezime='Test',
            email='patient@test.com',
            role=self.patient_role
        )

        termin = Termini.objects.create(
            lekar=self.doctor,
            pacijent=patient_user,
            pocetak=timezone.now() + timezone.timedelta(hours=1),
            kraj=timezone.now() + timezone.timedelta(hours=2),
            status='zakazan'
        )

        # Refresh page to see the appointment

        self.selenium.refresh()

        self.assertIn('/doctor-profile', self.selenium.current_url)
