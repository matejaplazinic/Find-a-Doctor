# Vuk Luzanin 29/2022
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>[\d_]+)/$', consumers.ChatConsumer.as_asgi()),
]
