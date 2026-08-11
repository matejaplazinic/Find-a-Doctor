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


class AuthenticationTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Use Chrome driver - make sure chromedriver is in your PATH
        cls.selenium = webdriver.Firefox()
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
        self.role_patient, _ = Role.objects.get_or_create(name='pacijent')
        self.role_admin, _ = Role.objects.get_or_create(name='admin')

        # Create a verified test user for login tests
        self.test_user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123',
            ime='Test',
            prezime='User',
            role=self.role_patient,
            verifikovan=True
        )

        # Create an unverified user
        self.unverified_user = User.objects.create_user(
            username='unverified_user',
            email='unverified@example.com',
            password='testpass123',
            ime='Unverified',
            prezime='User',
            role=self.role_patient,
            verifikovan=False
        )

    def test_successful_login(self):
        """Test successful login with valid credentials"""
        self.selenium.get(f"{self.live_server_url}/login")  # Adjust URL if different

        # Fill login form
        email_input = self.selenium.find_element(By.NAME, "email")
        password_input = self.selenium.find_element(By.NAME, "password")

        email_input.send_keys('test@example.com')
        password_input.send_keys('testpass123')

        # Submit form
        submit_button = self.selenium.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()

        # Wait for redirect and check if we're on home page

        self.selenium.implicitly_wait(10)
        self.assertIn('/', self.selenium.current_url)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials shows error message"""
        self.selenium.get(f"{self.live_server_url}/login")

        # Fill with wrong credentials
        email_input = self.selenium.find_element(By.NAME, "email")
        password_input = self.selenium.find_element(By.NAME, "password")

        email_input.send_keys('wrong@example.com')
        password_input.send_keys('wrongpassword')

        submit_button = self.selenium.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()

        # Check for error message
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "error"))  # Adjust based on your error class
        )

        error_message = self.selenium.find_element(By.CLASS_NAME, "error").text
        self.assertIn("Neispravan email ili sifra", error_message)


    def test_login_unverified_user(self):
        """Test login with unverified user shows appropriate error"""
        self.selenium.get(f"{self.live_server_url}/login")

        email_input = self.selenium.find_element(By.NAME, "email")
        password_input = self.selenium.find_element(By.NAME, "password")

        email_input.send_keys('unverified@example.com')
        password_input.send_keys('testpass123')

        submit_button = self.selenium.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()

        # Check for verification error message
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "error"))
        )

        error_message = self.selenium.find_element(By.CLASS_NAME, "error").text
        self.assertIn("Email nije verifikovan", error_message)

    def test_successful_registration(self):
        """Test successful user registration"""
        self.selenium.get(f"{self.live_server_url}/register")  # Adjust URL if different

        # Fill registration form
        form_data = {
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'address': 'Test Address 123',
            'birth_date': '1990-01-01',
            'phone_number': '+381641234567',
            'medical_history': 'No significant medical history'
        }

        for field_name, value in form_data.items():
            element = self.selenium.find_element(By.NAME, field_name)
            element.send_keys(value)

        # Submit form
        submit_button = self.selenium.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()

        # Wait for redirect to home page
        self.selenium.implicitly_wait(10)
        self.assertIn('/', self.selenium.current_url)

        # Verify user was created in database
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

        # Check that user is not verified
        new_user = User.objects.get(email='newuser@example.com')
        self.assertFalse(new_user.verifikovan)

    def test_registration_duplicate_email(self):
        """Test registration with duplicate email shows error"""
        self.selenium.get(f"{self.live_server_url}/register")

        # Fill form with existing email
        form_data = {
            'first_name': 'Duplicate',
            'last_name': 'User',
            'email': 'test@example.com',  # Already exists
            'password': 'testpass123',
            'address': 'Test Address',
            'birth_date': '1990-01-01',
            'phone_number': '+381641234567'
        }

        for field_name, value in form_data.items():
            element = self.selenium.find_element(By.NAME, field_name)
            element.send_keys(value)

        submit_button = self.selenium.find_element(By.XPATH, "//button[@type='submit']")
        submit_button.click()

        # Check for error message
        WebDriverWait(self.selenium, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "error"))
        )

        self.assertIn('/register', self.selenium.current_url)


User = get_user_model()
class DoctorRegistrationTests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = webdriver.Firefox()
        cls.selenium.implicitly_wait(10)
        cls.wait = WebDriverWait(cls.selenium, 10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
        # Create test role
        self.doctor_role, _ = Role.objects.get_or_create(name="doktor")

        # Create existing clinics for testing
        self.existing_clinic = Klinike.objects.create(
            naziv="Test Klinika",
            adresa="Test Adresa 123",
            grad="Test Grad",
            tip="privatna",
            radno_vreme="08:00-16:00",
            verifikovana=True
        )

        # Create temporary files for upload
        self.temp_diploma = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        self.temp_diploma.write(b"Fake diploma content")
        self.temp_diploma.close()

        self.temp_clinic_docs = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        self.temp_clinic_docs.write(b"Fake clinic docs content")
        self.temp_clinic_docs.close()

    def tearDown(self):
        # Clean up temporary files
        os.unlink(self.temp_diploma.name)
        os.unlink(self.temp_clinic_docs.name)

    def fill_basic_user_info(self, first_name="John", last_name="Doe", email="john.doe@example.com"):
        """Helper method to fill basic user information"""
        self.selenium.find_element(By.NAME, "first_name").send_keys(first_name)
        self.selenium.find_element(By.NAME, "last_name").send_keys(last_name)
        self.selenium.find_element(By.NAME, "email").send_keys(email)
        self.selenium.find_element(By.NAME, "phone_number").send_keys("+381641234567")
        self.selenium.find_element(By.NAME, "birth_date").send_keys("1990-01-01")
        self.selenium.find_element(By.NAME, "address").send_keys("Test Address 123")
        self.selenium.find_element(By.NAME, "password").send_keys("TestPass123!")

    def fill_doctor_specific_info(self, speciality="Cardiology", price="100"):
        """Helper method to fill doctor-specific information"""
        self.selenium.find_element(By.NAME, "speciality").send_keys(speciality)
        self.selenium.find_element(By.NAME, "medical_history").send_keys("Test biografija doktora")
        self.selenium.find_element(By.NAME, "price").send_keys(price)
        self.selenium.find_element(By.NAME, "docs").send_keys(self.temp_diploma.name)

    def test_doctor_registration_with_existing_clinic(self):
        url = reverse('doctor_register_view')
        """Test doctor registration with existing clinic selection"""
        self.selenium.get(f"{self.live_server_url}/{url}")

        # Fill basic user information
        self.fill_basic_user_info()

        # Fill doctor-specific information
        self.fill_doctor_specific_info()

        # Select existing clinic
        clinic_select = Select(self.selenium.find_element(By.ID, "clinic"))
        clinic_select.select_by_visible_text("Test Klinika")

        # Submit form
        self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        # Verify success - redirected to home page
        self.selenium.implicitly_wait(10)
        self.assertIn('/', self.selenium.current_url)

        # Verify user was created
        user = User.objects.get(email="john.doe@example.com")
        self.assertEqual(user.ime, "John")
        self.assertEqual(user.prezime, "Doe")
        self.assertEqual(user.role, self.doctor_role)
        self.assertFalse(user.verifikovan)  # Should not be verified initially

        # Verify doctor profile was created
        doctor = Lekari.objects.get(user=user)
        self.assertEqual(doctor.klinika, self.existing_clinic)
        self.assertEqual(doctor.specijalizacija, "Cardiology")
        self.assertEqual(doctor.cena, 100)

    def test_doctor_registration_with_new_clinic(self):
        url = reverse('doctor_register_view')
        """Test doctor registration with new clinic creation"""
        self.selenium.get(f"{self.live_server_url}/{url}")

        # Fill basic user information
        self.fill_basic_user_info(first_name="Jane", last_name="Smith", email="jane.smith@example.com")

        # Fill doctor-specific information
        self.fill_doctor_specific_info(speciality="Dermatology", price="150")

        # Select "Add new clinic" option
        clinic_select = Select(self.selenium.find_element(By.ID, "clinic"))
        clinic_select.select_by_visible_text("Dodajte novu kliniku")

        # Wait for new clinic fields to appear (if they are dynamically shown)
        self.wait.until(EC.visibility_of_element_located((By.ID, "clinic_name")))

        # Fill new clinic information
        self.selenium.find_element(By.ID, "clinic_name").send_keys("Nova Klinika")
        self.selenium.find_element(By.ID, "clinic_address").send_keys("Nova Adresa 456")
        self.selenium.find_element(By.ID, "clinic_phone").send_keys("+381641234568")
        self.selenium.find_element(By.ID, "clinic_docs").send_keys(self.temp_clinic_docs.name)

        # Submit form
        self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        # Verify success - redirected to home page
        self.selenium.implicitly_wait(10)
        self.assertIn('/', self.selenium.current_url)

        # Verify user was created
        user = User.objects.get(email="jane.smith@example.com")

        # Verify new clinic was created
        new_clinic = Klinike.objects.get(naziv="Nova Klinika")
        self.assertEqual(new_clinic.adresa, "Nova Adresa 456")

        # Verify doctor profile was created with new clinic
        doctor = Lekari.objects.get(user=user)
        self.assertEqual(doctor.klinika, new_clinic)
        self.assertEqual(doctor.specijalizacija, "Dermatology")

    def test_clinic_selection_validation(self):
        url = reverse('doctor_register_view')
        """Test clinic selection validation scenarios"""
        self.selenium.get(f"{self.live_server_url}/{url}")

        # Fill basic user information
        self.fill_basic_user_info(email="test@example.com")
        self.fill_doctor_specific_info()

        # Select "Choose clinic" (-1) and submit
        clinic_select = Select(self.selenium.find_element(By.ID, "clinic"))
        clinic_select.select_by_value("-1")

        self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        # Should show clinic required error
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "error")))
        error_text = self.selenium.find_element(By.CLASS_NAME, "error").text
        self.assertIn("Klinika je obavezna", error_text)
