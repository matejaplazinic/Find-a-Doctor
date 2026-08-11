# Milos Milinkovic 0396/2022
from django.urls import path
from . import views

urlpatterns = [
    path('', views.aktuelnosti_lista, name='aktuelnosti_lista'),
    path('<int:id>/', views.aktuelnost_detalj, name='aktuelnost_detalj'),
]
