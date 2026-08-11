# Milos Milinkovic 0396/2022
from django.urls import path

from . import views

urlpatterns = [
    path('doctor-profile/', views.doctor_profile, name='doctor_profile'),
    path('doctor/<int:id>/', views.doktor_javni, name='doktor_javni')
]
