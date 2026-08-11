# Autor - Davud Nusevic 2022/0076
from django import forms
from django.core.validators import RegexValidator
import datetime
import re
from doktor.models import Klinike

class LoginForm(forms.Form):

    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={
            "class": "input"
        }),
    )
    password = forms.CharField(
        label="Sifra",
        widget=forms.PasswordInput(attrs={
            "class": "input"
        }),
    )

class UserRegisterForm(forms.Form):

    first_name = forms.CharField(
        max_length=100,
        min_length=2,
        required=True,
        label='Ime',
        widget=forms.TextInput(attrs={
            'class': 'input',
        })
    )

    last_name = forms.CharField(
        max_length=100,
        min_length=2,
        required=True,
        label='Prezime',
        widget=forms.TextInput(attrs={
            'class': 'input',
        })
    )

    email = forms.EmailField(
        label="Email",
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "input"
        }),
    )

    password = forms.CharField(
        label="Sifra",
        required=True,
        widget=forms.PasswordInput(attrs={
            "class": "input"
        }),
    )

    address = forms.CharField(
        max_length=100,
        min_length=2,
        required=True,
        label='Adresa',
        widget=forms.TextInput(attrs={
            'class': 'input',
        })
    )

    birth_date = forms.DateField(
        label="Datum rodjenja",
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    docs = forms.FileField(
        required=False,
        widget = forms.FileInput(attrs={'name': 'docs'})
    )

    phone_number = forms.CharField(
        required=True,
        label='Telefon',
        max_length=17,
        widget=forms.TextInput(attrs={
            'pattern': '^\+?1?\d{9,15}$',  # HTML5 pattern validation
            'title': 'Unesite broj u formatu: +19995551234',
            'class': 'input',
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Broj mora biti u formatu: '+999999999'. Dozvoljeno je do 15 cifara."
            )
        ],
        help_text='Unesite broj za kodom zemlje (e.g., +1 555 123 4567)'
    )

    medical_history = forms.CharField(
        label="Medicinska Istorija",
        widget=forms.Textarea(attrs={
            "id": "reg-desc",
            "class": "input"
        }),
        required=False
    )


class DoctorRegisterForm(UserRegisterForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [("-1", "Izaberite kliniku")] + [(k.id, k.naziv) for k in Klinike.objects.all()] + [("0", "Dodajte novu kliniku")]
        self.fields['clinic'].choices = choices

    docs = forms.FileField(
        required=True,
        label="Diploma",
        widget=forms.FileInput(attrs={'name': 'docs'})
    )

    clinic = forms.ChoiceField(
        choices=[],
        required=True,
        label='Klinika',
        widget=forms.Select(attrs={
            "id": "clinic",
            "class": "input"
        })
    )

    new_clinic_name = forms.CharField(
        label="Naziv nove klinike",
        min_length=2,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input",
            "id": "clinic_name",
        })
    )

    new_clinic_address = forms.CharField(
        label="Adresa nove klinike",
        min_length=2,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input",
            "id": "clinic_address",
        })
    )

    new_clinic_phone = forms.CharField(
        required=False,
        label='Telefon',
        min_length=4,
        max_length=17,
        widget=forms.TextInput(attrs={
            'pattern': '^\+?1?\d{9,15}$',  # HTML5 pattern validation
            'title': 'Unesite broj u formatu: +19995551234',
            'class': 'input',
            'id': 'clinic_phone',
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Broj mora biti u formatu: '+999999999'. Up to 15 digits allowed."
            )
        ],
        help_text='Unesite broj sa kodom zemlje (e.g., +1 555 123 4567)'
    )

    new_clinic_docs = forms.FileField(
        required=False,
        label="Dokumenta",
        widget=forms.FileInput(attrs={
            'name': 'clinic_docs',
            'id': 'clinic_docs',
        })
    )

    speciality = forms.CharField(
        label="Specijalizacija",
        min_length=2,
        required=True,
        widget=forms.TextInput(attrs={'class': 'input'})
    )

    medical_history = forms.CharField(
        label="Biografija",
        widget=forms.Textarea(attrs={
            "id": "reg-desc",
            "class": "input"
        }),
        required=False
    )

    price = forms.DecimalField(
        required=True,
        label='Cijena',
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'min': '1',
            'class': 'input',
        })
    )


class NewsUploadForm(forms.Form):

    title = forms.CharField(
        max_length=100,
        min_length=2,
        required=True,
        label='Naslov',
        widget=forms.TextInput()
    )

    content = forms.CharField(
        label="Sadrzaj",
        widget=forms.Textarea(),
        required=True
    )

    image = forms.ImageField(
        label="Slika",
        required=False,
        widget=forms.FileInput()
    )