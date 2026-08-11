# Autor - Davud Nusevic 2022/0076
from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login_view'),
    path('register/', views.register_view, name='register_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('doctor/register', views.doctor_register_view, name='doctor_register_view'),
    path('adm/', views.admin_view, name='admin_view'),
    path('adm/verify_doctor/<int:id>/', views.verify_doctor, name='verify_doctor'),
    path('adm/verify_clinic/<int:id>/', views.verify_clinic, name='verify_clinic'),
    path('adm/verify_news/<int:id>/', views.verify_news, name='verify_news'),
    path('adm/news/upload', views.admin_news_upload, name='admin_news_upload'),
    path('activate/<str:uidb64>/<str:token>/', views.activate, name='activate')
]