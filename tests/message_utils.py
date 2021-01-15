from ArchiveAccess.DBWrite import TwitterDataWriter
from pytest import fixture
from datetime import datetime
from typing import Final, Iterable
from random import uniform, choice, randrange
from string import ascii_letters
import json
import asyncio

DATE_FORMAT: Final = "%Y-%m-%dT%H:%M:%S.%fZ"

MAIN_USER_ID: Final = 3330610905
# accounts that i feel like will be around for a while to run tests against
DOG_RATES: Final = 4196983835
OBAMA: Final = 813286
AMAZINGPHIL: Final = 14631115


@fixture
def writer():
    tdw = TwitterDataWriter("test", MAIN_USER_ID, in_memory=True)
    tdw.api_client.http_client = DummyHTTPClient()
    yield tdw
    tdw.close()


@fixture
def connected_writer():
    tdw = TwitterDataWriter("test", MAIN_USER_ID, in_memory=True)
    yield tdw
    tdw.close()


class DummyHTTPResponse:
    """very simple class that mocks tornado.httpclient.HTTPRequest"""

    def __init__(self, body):
        if isinstance(body, str):
            self.body = body.encode("utf-8")
        else:
            self.body = body


class DummyHTTPClient:
    """Class that mocks tornado.httpclient.AsyncHTTPClient, providing a fetch method
    and a close method. using DummyHTTPRequest as a container, yields an empty bytes
    object to requests for images and empty json arrays otherwise, unless the id for
    the dog_rates twitter account is detected in the request url; in that case, it
    yields a simplified version of the data that would be returned from the twitter
    api."""

    async def fetch(self, url_or_req):
        await asyncio.sleep(0)
        req = url_or_req if isinstance(url_or_req, str) else url_or_req.url
        if req.endswith(("jpg", "png", "gif")):
            return DummyHTTPResponse(bytes())
        elif str(DOG_RATES) in req:
            return DummyHTTPResponse(
                json.dumps(
                    [
                        {
                            "name": "We Rate Dogs",
                            "screen_name": "dog_rates",
                            "description": "",
                            "profile_image_url_https": "https://google.com/normal.jpg",
                            "id_str": str(DOG_RATES),
                            "id": DOG_RATES,
                        }
                    ]
                )
            )
        else:
            return DummyHTTPResponse("[]")

    def close(self):
        pass


def datetime_to_z_time(dt: datetime):
    """this converts a datetime object to a string in the format that twitter uses"""
    return dt.strftime(DATE_FORMAT)[0:23] + "Z"


def id_generator():
    i = 0
    while True:
        yield i
        i += 1


unique_id = id_generator()


def generate_messages(
    how_many: int,
    start_time: str,
    end_time: str,
    conversation_id: str,
    sender_id: str,
    recipient_id: str = None,
):
    """generates messages with random timestamps between start_time and end_time,
    where those are strings in DATE_FORMAT format."""
    start_datetime = datetime.strptime(start_time, DATE_FORMAT)
    end_datetime = datetime.strptime(end_time, DATE_FORMAT)
    generated_dates = [datetime_to_z_time(start_datetime)]
    in_between_dates = [
        datetime_to_z_time(
            datetime.fromtimestamp(
                uniform(start_datetime.timestamp() + 1, end_datetime.timestamp() - 1)
            )
        )
        for _ in range(how_many - 2)
    ]
    generated_dates += sorted(in_between_dates) + [datetime_to_z_time(end_datetime)]
    return [
        {
            "id": next(unique_id),
            "type": "messageCreate",
            "createdAt": date,
            "senderId": str(sender_id),
            "conversationId": conversation_id,
            "text": "".join(
                choice(ascii_letters + " ") for _ in range(randrange(2, 25))
            ),
            "mediaUrls": [],
            "reactions": [],
            "urls": [],
        }
        | ({"recipientId": str(recipient_id)} if recipient_id else {})
        for date in generated_dates
    ]


def generate_group_conversation(
    how_many: Iterable[int],
    start_times: Iterable[str],
    end_times: Iterable[str],
    conversation_id: str,
    users: Iterable[int],
):
    assert len(how_many) == len(start_times) == len(end_times) == len(users)
    messages = []
    for i in range(len(how_many)):
        messages += generate_messages(
            how_many[i], start_times[i], end_times[i], conversation_id, users[i]
        )
    return sorted(messages, key=lambda x: x["createdAt"])
