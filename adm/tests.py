# Vuk Luzanin 29/2022
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import date, timedelta
import tempfile
from PIL import Image
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.messages import get_messages


from .forms import *
from doktor.models import *

User = get_user_model()

class ModelTests(TestCase):
    def setUp(self):
        # Create roles
        self.role_patient = Role.objects.create(name='pacijent')
        self.role_doctor = Role.objects.create(name='doktor')
        self.role_admin = Role.objects.create(name='admin')

        # Create test image
        self.create_test_image()

        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role=self.role_admin,
            verifikovan=True
        )

        self.patient_user = User.objects.create_user(
            username='patient',
            email='patient@test.com',
            password='testpass123',
            role=self.role_patient,
            verifikovan=True,
            ime='John',
            prezime='Doe'
        )

        self.doctor_user = User.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='testpass123',
            role=self.role_doctor,
            verifikovan=True,
            ime='Jane',
            prezime='Smith'
        )

        # Create clinic
        self.clinic = Klinike.objects.create(
            naziv='Test Clinic',
            adresa='Test Address 123',
            tip='privatna',
            verifikovana=True
        )

        # Create doctor profile
        self.doctor = Lekari.objects.create(
            user=self.doctor_user,
            klinika=self.clinic,
            specijalizacija='Cardiology',
            biografija='Test bio',
            cena=100
        )

    def create_test_image(self):
        """Create a test image for file uploads"""
        image = Image.new('RGB', (100, 100), color='red')
        image_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        image.save(image_file, 'JPEG')
        image_file.seek(0)
        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )
        image_file.close()

    def test_user_creation(self):
        """Test User model creation and methods"""
        self.assertEqual(str(self.patient_user), 'John Doe')
        self.assertTrue(self.patient_user.check_password('testpass123'))
        self.assertEqual(self.patient_user.role.name, 'pacijent')
        self.assertTrue(self.patient_user.verifikovan)

    def test_clinic_creation(self):
        """Test Klinike model creation"""
        self.assertEqual(str(self.clinic), 'Test Clinic')
        self.assertEqual(self.clinic.tip, 'privatna')
        self.assertTrue(self.clinic.verifikovana)

    def test_doctor_creation(self):
        """Test Lekari model creation"""
        self.assertEqual(str(self.doctor), 'Dr. Jane Smith')
        self.assertEqual(self.doctor.specijalizacija, 'Cardiology')
        self.assertEqual(self.doctor.cena, 100)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create roles
        self.role_patient = Role.objects.create(name='pacijent')
        self.role_doctor = Role.objects.create(name='doktor')
        self.role_admin = Role.objects.create(name='admin')

        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role=self.role_admin,
            verifikovan=True
        )

        # Create test clinic
        self.clinic = Klinike.objects.create(
            naziv='Test Clinic',
            adresa='Test Address',
            tip='privatna',
            verifikovana=True
        )

    def test_login_view_get(self):
        """Test login page GET request"""
        response = self.client.get(reverse('login_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'form')

    def test_login_view_post_success(self):
        """Test successful login"""
        User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role=self.role_patient,
            verifikovan=True
        )

        response = self.client.post(reverse('login_view'), {
            'email': 'test@test.com',
            'password': 'testpass123'
        })

        self.assertRedirects(response, reverse('home'))

    def test_login_view_post_invalid(self):
        """Test login with invalid credentials"""
        response = self.client.post(reverse('login_view'), {
            'email': 'wrong@test.com',
            'password': 'wrongpass'
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Neispravan email ili sifra')

    def test_register_view_get(self):
        """Test register page GET request"""
        response = self.client.get(reverse('register_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
        self.assertContains(response, 'form')

    def test_register_view_post_success(self):
        """Test successful user registration"""
        response = self.client.post(reverse('register_view'), {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'newuser@test.com',
            'password': 'testpass123',
            'birth_date': '1990-01-01',
            'address': 'Test Address',
            'phone_number': '1234567890',
            'medical_history': 'No issues'
        })

        # Should redirect to home
        self.assertRedirects(response, reverse('home'))

        # Check if user was created
        self.assertTrue(User.objects.filter(email='newuser@test.com').exists())

    def test_doctor_register_view_get(self):
        """Test doctor registration page GET request"""
        response = self.client.get(reverse('doctor_register_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'doctor_registration.html')
        self.assertContains(response, 'form')

    def test_logout_view(self):
        """Test logout functionality"""
        # Login first
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('logout_view'))
        self.assertRedirects(response, reverse('home'))

    def test_admin_view_access_denied(self):
        """Test admin view access without admin role"""
        # Create non-admin user
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123',
            role=self.role_patient,
            verifikovan=True
        )

        self.client.force_login(regular_user)
        response = self.client.get(reverse('admin_view'))

        # Should get 404 for non-admin users
        self.assertEqual(response.status_code, 404)

    def test_admin_view_access_granted(self):
        """Test admin view access with admin role"""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin_view'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel.html')

    def test_verify_doctor(self):
        """Test doctor verification by admin"""
        # Create unverified doctor
        doctor_user = User.objects.create_user(
            username='docuser',
            email='doc@test.com',
            password='testpass123',
            role=self.role_doctor,
            verifikovan=False
        )

        doctor = Lekari.objects.create(
            user=doctor_user,
            klinika=self.clinic,
            specijalizacija='Test Specialty'
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('verify_doctor', args=[doctor.id]))

        self.assertEqual(response.status_code, 200)

        # Check if doctor was verified
        doctor_user.refresh_from_db()
        self.assertTrue(doctor_user.verifikovan)

    def test_verify_clinic(self):
        """Test clinic verification by admin"""
        unverified_clinic = Klinike.objects.create(
            naziv='Unverified Clinic',
            adresa='Test Address',
            tip='privatna',
            verifikovana=False
        )

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('verify_clinic', args=[unverified_clinic.id]))

        self.assertEqual(response.status_code, 200)

        # Check if clinic was verified
        unverified_clinic.refresh_from_db()
        self.assertTrue(unverified_clinic.verifikovana)

    def test_activate_account(self):
        """Test account activation via email token"""
        user = User.objects.create_user(
            username='inactive',
            email='inactive@test.com',
            password='testpass123',
            role=self.role_patient,
            verifikovan=False
        )

        # Generate token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        response = self.client.get(reverse('activate', args=[uid, token]))

        self.assertEqual(response.status_code, 200)

        # Check if user was activated
        user.refresh_from_db()
        self.assertTrue(user.verifikovan)

class FormTests(TestCase):
    def setUp(self):
        self.role_patient = Role.objects.create(name='pacijent')
        self.role_doctor = Role.objects.create(name='doktor')

    def test_login_form_valid(self):
        """Test valid login form"""
        form_data = {
            'email': 'test@test.com',
            'password': 'testpass123'
        }
        form = LoginForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_login_form_invalid(self):
        """Test invalid login form"""
        form_data = {
            'email': '',
            'password': ''
        }
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_user_register_form_valid(self):
        """Test valid user registration form"""
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@test.com',
            'password': 'testpass123',
            'birth_date': '1990-01-01',
            'address': 'Test Address',
            'phone_number': '1234567890'
        }
        form = UserRegisterForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_user_register_form_invalid(self):
        """Test invalid user registration form"""
        form_data = {
            'first_name': '',  # Required field missing
            'last_name': 'User',
            'email': 'invalid-email',  # Invalid email
            'password': 'short'  # Too short password
        }
        form = UserRegisterForm(data=form_data)
        self.assertFalse(form.is_valid())


class IntegrationTests(TestCase):
    """Integration tests for complete user flows"""

    def setUp(self):
        self.client = Client()
        self.role_patient = Role.objects.create(name='pacijent')
        self.role_doctor = Role.objects.create(name='doktor')
        self.role_admin = Role.objects.create(name='admin')

    def test_complete_user_registration_flow(self):
        """Test complete user registration and login flow"""
        # Step 1: Register
        response = self.client.post(reverse('register_view'), {
            'first_name': 'Integration',
            'last_name': 'Test',
            'email': 'integration@test.com',
            'password': 'testpass123',
            'birth_date': '1990-01-01',
            'address': 'Integration Test Address',
            'phone_number': '1234567890'
        })

        self.assertRedirects(response, reverse('home'))

        # Step 2: Verify user was created
        user = User.objects.get(email='integration@test.com')
        self.assertFalse(user.verifikovan)  # Not verified yet

        # Step 3: Activate account (simulate email activation)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        activation_response = self.client.get(reverse('activate', args=[uid, token]))
        self.assertEqual(activation_response.status_code, 200)

        # Step 4: Verify user is now activated
        user.refresh_from_db()
        self.assertTrue(user.verifikovan)

        # Step 5: Login with activated account
        login_response = self.client.post(reverse('login_view'), {
            'email': 'integration@test.com',
            'password': 'testpass123'
        })

        self.assertRedirects(login_response, reverse('home'))


class DoctorRegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('doctor_register_view')  # Update with your actual URL name
        self.role = Role.objects.create(name="doktor")

        # Create existing clinic for tests
        self.existing_clinic = Klinike.objects.create(
            naziv="Test Clinic",
            adresa="Test Address"
        )

        # Valid form data templates
        self.valid_data_existing_clinic = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'securepassword123',
            'birth_date': '1990-01-01',
            'address': 'Test Address 123',
            'phone_number': '+381621666937',
            'speciality': 'Cardiology',
            'medical_history': 'Test bio',
            'price': 100,
            'clinic': str(self.existing_clinic.id),
            'docs': []  # Will be replaced with actual files in tests
        }

        self.valid_data_new_clinic = {
            **self.valid_data_existing_clinic,
            'clinic': '0',
            'new_clinic_name': 'New Clinic',
            'new_clinic_address': 'New Address',
            'new_clinic_phone': '+381621666937',
            'new_clinic_docs': []  # Will be replaced with actual files
        }

    def create_test_files(self):
        """Helper method to create test files"""
        clinic_doc = SimpleUploadedFile(
            "clinic_doc.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        doctor_doc = SimpleUploadedFile(
            "doctor_doc.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        return clinic_doc, doctor_doc

    def test_POST_missing_clinic_shows_error(self):
        clinic_doc, doctor_doc = self.create_test_files()
        data = {**self.valid_data_existing_clinic, 'clinic': '-1', 'docs': doctor_doc}

        response = self.client.post(self.url, data)
        if hasattr(response, 'context') and 'form' in response.context:
            form = response.context['form']
            print("Form errors:", form.errors)
            print("Form non-field errors:", form.non_field_errors())
        else:
            print("No form in context")
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), 'Klinika je obavezna.')
        self.assertEqual(response.status_code, 200)

    def test_POST_new_clinic_missing_name_shows_error(self):
        clinic_doc, doctor_doc = self.create_test_files()
        data = {**self.valid_data_new_clinic, 'new_clinic_name': '', 'docs': doctor_doc}
        response = self.client.post(self.url, data)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), 'Ime klinike je obavezno')
        self.assertEqual(response.status_code, 200)

    def test_POST_new_clinic_missing_documents_shows_error(self):
        clinic_doc, doctor_doc = self.create_test_files()
        data = self.valid_data_new_clinic.copy()
        data['docs'] = doctor_doc
        files = {}
        response = self.client.post(self.url, data, files=files)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), 'Dokumenti klinike su obavezni')
        self.assertEqual(response.status_code, 200)

    def test_POST_valid_existing_clinic_creates_objects(self):
        clinic_doc, doctor_doc = self.create_test_files()
        data = self.valid_data_existing_clinic.copy()
        data['docs'] = doctor_doc
        data['new_clinic_docs'] = clinic_doc
        response = self.client.post(self.url, data)

        # Check redirect
        self.assertRedirects(response, reverse('home'))

        # Check database
        self.assertTrue(User.objects.filter(email=data['email']).exists())
        user = User.objects.get(email=data['email'])
        self.assertTrue(Lekari.objects.filter(user=user).exists())
        self.assertTrue(DoctorDocument.objects.filter(lekar__user=user).exists())

    def test_POST_valid_new_clinic_creates_all_objects(self):
        clinic_doc, doctor_doc = self.create_test_files()
        data = self.valid_data_new_clinic.copy()
        data['docs'] = doctor_doc
        data['new_clinic_docs'] = clinic_doc
        response = self.client.post(self.url, data)

        self.assertRedirects(response, reverse('home'))

        # Check clinic creation
        self.assertTrue(Klinike.objects.filter(naziv=data['new_clinic_name']).exists())
        clinic = Klinike.objects.get(naziv=data['new_clinic_name'])
        self.assertTrue(ClinicDocument.objects.filter(clinic=clinic).exists())

        # Check user and doctor
        user = User.objects.get(email=data['email'])
        self.assertTrue(Lekari.objects.filter(user=user, klinika=clinic).exists())

