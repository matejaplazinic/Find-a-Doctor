# Vuk Luzanin 29/2022
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from doktor.models import Poruke

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer za real-time chat između dva korisnika.

    Funkcionalnosti:
    - Priključivanje i odjavljivanje iz chat sobe
    - Slanje i primanje poruka
    - Slanje statusa "typing" (kucanje poruke)
    - Kreiranje Poruke u bazi podataka asinhrono

    Room_name se očekuje u formatu "user1id_user2id".
    """

    async def connect(self):
        """
        Asinhrono se povezuje na WebSocket i dodaje korisnika u chat grupu.

        self.scope['url_route']['kwargs']['room_name'] mora biti string u formatu 'user1id_user2id'.
        """
        self.user = self.scope["user"]
        self.other_user_id = int(self.scope['url_route']['kwargs']['room_name'].split('_')[0])
        # room_name se prosleđuje kao 'user1id_user2id', uzmi oba
        ids = sorted([self.user.id, self.other_user_id])
        self.room_group_name = f"chat_{ids[0]}_{ids[1]}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """
        Asinhrono uklanja korisnika iz chat grupe prilikom zatvaranja konekcije.
        """
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """
        Prima poruke od klijenta.

        Ako data sadrži 'typing', prosleđuje status kucanja.
        Ako data sadrži 'message' i/ili 'file_url', kreira Poruke objekat i emituje ga grupi.

        Parametri:
        - text_data: JSON string sa ključevima 'message', 'file_url', 'file_name' ili 'typing'
        - bytes_data: ne koristi se
        """
        data = json.loads(text_data)

        if 'typing' in data:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_status',
                    'typing': data['typing'],
                    'sender_id': self.user.id,
                }
            )
            return

        message = data.get('message', '').strip()
        file_url = data.get('file_url', None)
        file_name = data.get('file_name', None)

        if not message and not file_url:
            return

        other_user = await sync_to_async(User.objects.get)(id=self.other_user_id)
        poruka = await sync_to_async(Poruke.objects.create)(
            posiljalac=self.user,
            primalac=other_user,
            tekst=message
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender_id": self.user.id,
                "timestamp": poruka.poslato.strftime('%H:%M %d.%m.%Y'),
                "file_url": file_url,
                "file_name": file_name,
            }
        )

    async def chat_message(self, event):
        """
        Prima event tipa 'chat_message' i šalje ga WebSocket klijentu.

        Parametri:
        - event: dict sa ključevima 'message', 'sender_id', 'timestamp', 'file_url', 'file_name'
        """
        await self.send(text_data=json.dumps(event))

    async def typing_status(self, event):
        """
        Prima event tipa 'typing_status' i šalje ga WebSocket klijentu.

        Parametri:
        - event: dict sa ključevima 'typing', 'sender_id'
        """
        await self.send(text_data=json.dumps(event))
