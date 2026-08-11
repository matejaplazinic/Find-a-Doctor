# Mateja Plazinic 2022/0335
from django.urls import path
from pacijent.views import pacijent_profile, pretraga, dodaj_u_omiljene, ukloni_omiljenog, dodaj_recenziju

urlpatterns = [
    path('profil/', pacijent_profile, name='pacijent_profile'),
    path('pretraga/', pretraga, name='pretraga'),
    path('dodaj-omiljene/<int:lekar_id>/', dodaj_u_omiljene, name='dodaj_omiljene'),
    path('ukloni-omiljenog/', ukloni_omiljenog, name='ukloni_omiljenog'),
    path('dodaj_recenziju',dodaj_recenziju,name='dodaj_recenziju'),

]
