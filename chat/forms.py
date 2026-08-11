# Vuk Luzanin 29/2022
from django import forms
from doktor.models import Poruke


class PorukaForm(forms.ModelForm):
    """
    Forma za kreiranje Poruke između korisnika.

    Polje:
    - tekst: tekst poruke koji korisnik želi da pošalje.

    Widget je TextInput sa placeholder-om i CSS klasom za Bootstrap stilizaciju.
    """
    class Meta:
        model = Poruke
        fields = ['tekst']
        widgets = {
            'tekst': forms.TextInput(attrs={'placeholder': 'Upiši poruku...', 'class': 'form-control'})
        }
