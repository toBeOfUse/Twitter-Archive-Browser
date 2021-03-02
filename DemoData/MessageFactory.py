from typing import Final
from datetime import datetime, timedelta


class MessageFactory:
    DATE_FORMAT: Final = "%Y-%m-%dT%H:%M:%S.%fZ"
    next_message_id = 0

    def __init__(
        self,
        conversation_id: str,
        first_message_time: datetime,
        recipients: tuple = None,
        minutes_apart=1,
    ):
        self.conversation_id = conversation_id
        self.next_message_time = first_message_time
        self.recipient_ids = recipients
        self.minutes_apart = minutes_apart

    def get_next_date(self):
        next_date = self.next_message_time.strftime(self.DATE_FORMAT)[0:23] + "Z"
        self.next_message_time += timedelta(minutes=self.minutes_apart)
        return next_date

    @classmethod
    def get_next_message_id(cls):
        next_id = cls.next_message_id
        cls.next_message_id += 1
        return str(next_id)

    def create_message(self, sender_id: int, text: str):
        message = {
            "conversationId": self.conversation_id,
            "createdAt": self.get_next_date(),
            "id": self.get_next_message_id(),
            "mediaUrls": [],
            "reactions": [],
            "senderId": str(sender_id),
            "text": text,
            "type": "messageCreate",
            "urls": [],
        }
        if self.recipient_ids:
            message["recipientId"] = str(
                next(x for x in self.recipient_ids if x != sender_id)
            )
        return message

    def create_name_update(self, initiator_id: int, new_name: str):
        return {
            "initiatingUserId": str(initiator_id),
            "name": new_name,
            "createdAt": self.get_next_date(),
            "type": "conversationNameUpdate",
            "conversationId": self.conversation_id,
        }
