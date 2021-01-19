from ArchiveAccess.DBWrite import TwitterDataWriter
from ArchiveAccess.DBRead import TwitterDataReader
from pytest import fixture
from datetime import datetime
from typing import Final, Iterable, Union
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
    tdw = TwitterDataWriter(
        "file:memdb1?mode=memory&cache=shared", "test", MAIN_USER_ID
    )
    tdw.api_client.http_client = DummyHTTPClient()
    yield tdw
    tdw.close()


@fixture
def connected_writer():
    tdw = TwitterDataWriter(
        "file:memdb1?mode=memory&cache=shared", "test", MAIN_USER_ID
    )
    yield tdw
    tdw.close()


@fixture
def reader():
    tdr = TwitterDataReader("file:memdb1?mode=memory&cache=shared")
    yield tdr
    tdr.close()


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
                            "description": "sample bio",
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


def datetime_to_z_time(dt: datetime) -> str:
    """this converts a datetime object to a string in the format that twitter uses"""
    return dt.strftime(DATE_FORMAT)[0:23] + "Z"


def z_time_to_datetime(ztime: str) -> datetime:
    return datetime.strptime(ztime, DATE_FORMAT)


def random_datestring() -> str:
    return datetime_to_z_time(
        datetime.fromtimestamp(
            uniform(datetime(2000, 1, 1).timestamp(), datetime.now().timestamp())
        )
    )


def random_2000s_datestring() -> str:
    return datetime_to_z_time(
        datetime.fromtimestamp(
            uniform(
                datetime(2000, 1, 1).timestamp(), datetime(2009, 12, 31).timestamp()
            )
        )
    )


def random_2010s_datestring() -> str:
    return datetime_to_z_time(
        datetime.fromtimestamp(
            uniform(
                datetime(2010, 1, 1).timestamp(), datetime(2019, 12, 31).timestamp()
            )
        )
    )


def id_generator() -> int:
    i = 0
    while True:
        yield str(i)
        i += 1


unique_id = id_generator()


def get_random_text():
    return "".join(choice(ascii_letters + " ") for _ in range(randrange(2, 25)))


def generate_messages(
    how_many: int,
    start_time: str,
    end_time: str,
    conversation_id: str,
    sender_id: Union[str, int],
    recipient_id: Union[str, int] = None,
) -> list[dict]:
    """generates messages with random timestamps between start_time and end_time,
    where those are strings in DATE_FORMAT format. end_time can be any string if you
    only want 1 message"""
    assert how_many > 0
    start_datetime = z_time_to_datetime(start_time)
    generated_dates = [datetime_to_z_time(start_datetime)]
    if how_many > 1:
        end_datetime = z_time_to_datetime(end_time)
        assert end_datetime > start_datetime
        in_between_dates = [
            datetime_to_z_time(
                datetime.fromtimestamp(
                    uniform(
                        start_datetime.timestamp() + 1,
                        end_datetime.timestamp() - 1,
                    )
                )
            )
            # this makes in_between_dates empty if how_many == 2
            for _ in range(how_many - 2)
        ]
        generated_dates += sorted(in_between_dates) + [
            datetime_to_z_time(end_datetime)
        ]
    generated_messages = [
        {
            "id": next(unique_id),
            "type": "messageCreate",
            "createdAt": date,
            "senderId": str(sender_id),
            "conversationId": conversation_id,
            "text": get_random_text(),
            "mediaUrls": [],
            "reactions": [],
            "urls": [],
        }
        | ({"recipientId": str(recipient_id)} if recipient_id else {})
        for date in generated_dates
    ]
    return generated_messages


def generate_conversation(
    how_many: Iterable[int],
    start_times: Iterable[str],
    end_times: Iterable[str],
    conversation_id: str,
    users: Iterable[int],
    group: bool = True,
) -> list[dict]:
    assert len(how_many) == len(start_times) == len(end_times) == len(users)
    if not group:
        assert len(how_many) == 2, "individual conversations need to have two people"
    messages = []
    for i in range(len(how_many)):
        parameters = [
            how_many[i],
            start_times[i],
            end_times[i],
            conversation_id,
            users[i],
        ]
        if not group:
            parameters.append(users[0 if i == 1 else 1])
        messages += generate_messages(*parameters)
    return sorted(messages, key=lambda x: x["createdAt"])


def generate_name_update(
    initiator: Union[str, int], new_name: str, time: str, conversation_id: str
) -> dict:
    return {
        "initiatingUserId": str(initiator),
        "name": new_name,
        "createdAt": time,
        "type": "conversationNameUpdate",
        "conversationId": conversation_id,
    }
