# Vuk Luzanin 29/2022
from django.urls import path
from chat.views import chat, chat_user_search, upload_recept

urlpatterns = [
    path('chat/', chat, name='chat'),
    path('chat/<int:other_id>/', chat, name='chat'),
    path('chat/search/', chat_user_search, name='chat_user_search'),
    path('chat/upload-recept/', upload_recept, name='upload_recept'),
]
