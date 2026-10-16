"""
WebSocket Consumers — Real-Time Chat Messaging & User Presence

Provides two AsyncWebSocketConsumer classes:

1. ChatConsumer:  Handles real-time chat messages, typing indicators,
                  read receipts, and message deletion events.
2. PresenceConsumer: Tracks online/offline user status globally and
                     broadcasts connect/disconnect to all clients.

Both consumers use Django Channels' group-based messaging to deliver
events to the correct recipients in real time.
"""

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from .models import Message
from core.users.models import User


# =============================================================================
# ChatConsumer — Real-time messaging, typing, read receipts, deletion
# =============================================================================

class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for one-on-one real-time chat.

    Each authenticated user joins a personal group (``user_{id}``) on
    connect.  All chat events (new messages, typing, read receipts,
    deletions) are sent to the relevant user's group so the recipient
    receives them instantly.
    """

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        """Authenticate user and join their personal notification group."""
        self.user = self.scope.get('user', AnonymousUser())
        if self.user.is_anonymous:
            await self.close()
            return

        self.user_room = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.user_room, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            'presence',
            {
                'type': 'user_online',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )

    async def disconnect(self, close_code):
        """Leave personal group and broadcast offline status."""
        if hasattr(self, 'user_room'):
            await self.channel_layer.group_discard(self.user_room, self.channel_name)

        if hasattr(self, 'user') and not self.user.is_anonymous:
            await self.channel_layer.group_send(
                'presence',
                {
                    'type': 'user_offline',
                    'user_id': self.user.id,
                    'username': self.user.username,
                }
            )

    # ------------------------------------------------------------------
    # Inbound message dispatcher
    # ------------------------------------------------------------------

    async def receive(self, text_data):
        """Parse incoming JSON and route to the appropriate handler."""
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == 'chat_message':
            await self.handle_chat_message(data)
        elif msg_type == 'mark_read':
            await self.handle_mark_read(data)
        elif msg_type == 'typing':
            await self.handle_typing(data)
        elif msg_type == 'delete_message':
            await self.handle_delete_message(data)

    # ------------------------------------------------------------------
    # Outbound event dispatchers (called by group_send)
    # ------------------------------------------------------------------

    async def chat_message(self, event):
        """Send a new_message event to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message'],
        }))

    async def messages_read(self, event):
        """Send a read_receipt event to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'read_by': event['read_by'],
            'count': event['count'],
        }))

    async def typing_indicator(self, event):
        """Send a typing notification to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing'],
        }))

    async def message_deleted(self, event):
        """Notify the WebSocket client that a message was deleted."""
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
        }))

    # ------------------------------------------------------------------
    # Cross-app notification / social broadcast handlers
    # ------------------------------------------------------------------

    async def notification_event(self, event):
        """Relay a notification (from notifications app)."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification'],
        }))

    async def friend_request_sent(self, event):
        """Relay a friend request notification."""
        await self.send(text_data=json.dumps({
            'type': 'friend_request_sent',
            'from_user': event['from_user'],
            'notification': event.get('notification'),
        }))

    async def friend_request_accepted(self, event):
        """Relay a friend request accepted notification."""
        await self.send(text_data=json.dumps({
            'type': 'friend_request_accepted',
            'by_user': event['by_user'],
            'notification': event.get('notification'),
        }))

    # ------------------------------------------------------------------
    # Handler implementations
    # ------------------------------------------------------------------

    async def handle_chat_message(self, data):
        """
        Persist and broadcast a new chat message.

        Saves the message to the database, then sends it to both the
        sender (with ``is_mine: True``) and the receiver (with
        ``is_mine: False``) so each sees the correct translation.
        """
        receiver_id = data.get('receiver_id')
        content = data.get('content', '')
        message_type = data.get('message_type', 'text')
        asl_content = data.get('asl_content')
        gesture_id = data.get('gesture_id')

        result = await self.save_message(
            receiver_id=receiver_id,
            content=content,
            message_type=message_type,
            asl_content=asl_content,
            gesture_id=gesture_id,
        )
        if result is None:
            return

        sender_msg, receiver_msg = result

        receiver_room = f'user_{receiver_id}'
        await self.channel_layer.group_send(
            receiver_room,
            {
                'type': 'chat_message',
                'message': {**receiver_msg, 'is_mine': False},
            }
        )

        await self.channel_layer.group_send(
            self.user_room,
            {
                'type': 'chat_message',
                'message': {**sender_msg, 'is_mine': True},
            }
        )

    async def handle_mark_read(self, data):
        """
        Mark all unread messages from a given sender as read.

        Broadcasts a read receipt back to the original sender so their
        UI can update the unread badge and message status.
        """
        sender_id = data.get('sender_id')
        if sender_id:
            count = await self.mark_messages_read(sender_id)

            sender_room = f'user_{sender_id}'
            await self.channel_layer.group_send(
                sender_room,
                {
                    'type': 'messages_read',
                    'read_by': self.user.id,
                    'count': count,
                }
            )

    async def handle_typing(self, data):
        """Broadcast typing indicator to the conversation partner."""
        receiver_id = data.get('receiver_id')
        is_typing = data.get('is_typing', False)

        receiver_room = f'user_{receiver_id}'
        await self.channel_layer.group_send(
            receiver_room,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.get_full_name() or self.user.username,
                'is_typing': is_typing,
            }
        )

    async def handle_delete_message(self, data):
        """Delete a message owned by the current user and notify clients."""
        message_id = data.get('message_id')
        if not message_id:
            return
        deleted = await self.delete_message(message_id)
        if deleted:
            await self.channel_layer.group_send(
                self.user_room,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                }
            )

    # ------------------------------------------------------------------
    # Database helpers (wrapped in database_sync_to_async)
    # ------------------------------------------------------------------

    @database_sync_to_async
    def save_message(self, receiver_id, content, message_type, asl_content, gesture_id):
        """
        Create a Message in the database and return translated dicts.

        Returns a tuple ``(sender_dict, receiver_dict)`` where each dict
        is the message serialised from the respective user's perspective
        (including translated display fields).  Returns ``None`` when the
        receiver does not exist.
        """
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return None

        msg = Message.objects.create(
            sender=self.user,
            receiver=receiver,
            content=content,
            message_type=message_type,
            asl_content=asl_content,
            gesture_id=gesture_id,
        )

        sender_msg = msg.to_dict(msg.sender)
        receiver_msg = msg.to_dict(msg.receiver)

        return sender_msg, receiver_msg

    @database_sync_to_async
    def mark_messages_read(self, sender_id):
        """
        Mark all unread messages from ``sender_id`` to the current user
        as read.  Returns the number of messages updated.
        """
        count = Message.objects.filter(
            sender_id=sender_id,
            receiver=self.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        return count

    @database_sync_to_async
    def delete_message(self, message_id):
        """
        Delete a message owned by the current user.

        Returns ``True`` if the message was found and deleted,
        ``False`` otherwise.
        """
        try:
            msg = Message.objects.get(id=message_id, sender=self.user)
            msg.delete()
            return True
        except Message.DoesNotExist:
            return False


# =============================================================================
# PresenceConsumer — Online / offline user tracking
# =============================================================================

class PresenceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that tracks which users are currently online.

    Maintains a class-level ``online_users`` set and broadcasts
    connect / disconnect events to the global ``presence`` group so
    every connected client stays in sync.
    """

    online_users = set()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        """Authenticate, join presence group, and broadcast online."""
        self.user = self.scope.get('user', AnonymousUser())
        if self.user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add('presence', self.channel_name)
        await self.accept()

        PresenceConsumer.online_users.add(self.user.id)

        await self.channel_layer.group_send(
            'presence',
            {
                'type': 'user_online',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )

        await self.send(text_data=json.dumps({
            'type': 'online_users',
            'user_ids': list(PresenceConsumer.online_users),
        }))

    async def disconnect(self, close_code):
        """Leave presence group and broadcast offline."""
        await self.channel_layer.group_discard('presence', self.channel_name)

        if hasattr(self, 'user') and not self.user.is_anonymous:
            PresenceConsumer.online_users.discard(self.user.id)
            await self.channel_layer.group_send(
                'presence',
                {
                    'type': 'user_offline',
                    'user_id': self.user.id,
                    'username': self.user.username,
                }
            )

    # ------------------------------------------------------------------
    # Outbound event dispatchers
    # ------------------------------------------------------------------

    async def user_online(self, event):
        """Notify all clients that a user came online."""
        await self.send(text_data=json.dumps({
            'type': 'user_online',
            'user_id': event['user_id'],
            'username': event.get('username', ''),
        }))

    async def user_offline(self, event):
        """Notify all clients that a user went offline."""
        await self.send(text_data=json.dumps({
            'type': 'user_offline',
            'user_id': event['user_id'],
            'username': event.get('username', ''),
        }))
