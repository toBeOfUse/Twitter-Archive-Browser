"""these tests sequentially add messages to a test database and check that the
database is properly finalized with derived data and metadata by the end. basically,
this module tests that the user data that SimpleTwitterAPIClient retrieves is correct
and is saved, and checks that the attributes set by cache_conversation_stats.sql are
accurate."""

from ArchiveAccess.DBWrite import TwitterDataWriter
import pytest
from pytest import fixture
from collections import deque
from typing import Final, Iterable
from datetime import datetime
from random import uniform, choice, randrange
from string import ascii_letters
from tornado.ioloop import IOLoop
from tornado.httpclient import HTTPRequest
import asyncio
import json

DATE_FORMAT: Final = "%Y-%m-%dT%H:%M:%S.%fZ"

MAIN_USER_ID: Final = 3330610905
# accounts that i feel like will be around for a while to run tests against
DOG_RATES: Final = 4196983835
OBAMA: Final = 813286
AMAZINGPHIL: Final = 14631115


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


@fixture
def writer():
    tdw = TwitterDataWriter("test", MAIN_USER_ID, automatic_overwrite=True)
    tdw.api_client.http_client = DummyHTTPClient()
    yield tdw
    tdw.close()


@fixture
def connected_writer():
    tdw = TwitterDataWriter("test", MAIN_USER_ID, automatic_overwrite=True)
    yield tdw
    tdw.close()


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


@pytest.fixture(scope="module")
def event_loop():
    return IOLoop.current().asyncio_loop


def check_dog_rates(writer: TwitterDataWriter):
    """checks that a user matching the description of the dog_rates twitter account
    has been created; this account is the one that even the dummied-out http client
    will return data for. returns the number of messages that that user has been
    recording sending."""
    row = writer.execute(
        """select
        number_of_messages, loaded_full_data, handle
        from users where id=?;""",
        (DOG_RATES,),
    ).fetchone()
    assert row[1:3] == (1, "dog_rates")
    return row[0]


@pytest.mark.asyncio
async def test_normal_individual_conversation(connected_writer: TwitterDataWriter):
    users = (MAIN_USER_ID, DOG_RATES)
    user0_span = ("2020-01-01T10:00:00.100Z", "2020-01-10T10:00:00.100Z")
    user1_span = ("2020-01-02T10:00:00.100Z", "2020-01-09T10:00:00.100Z")
    conversation_id = "simple_conversation"
    side1 = generate_messages(
        10,
        user0_span[0],
        user0_span[1],
        conversation_id,
        users[0],
        users[1],
    )
    side2 = generate_messages(
        10,
        user1_span[0],
        user1_span[1],
        conversation_id,
        users[1],
        users[0],
    )
    for message in sorted(side1 + side2, key=lambda x: x["createdAt"]):
        connected_writer.add_message(message)

    await connected_writer.finalize()

    assert connected_writer.execute(
        "select * from conversations where id=?;", (conversation_id,)
    ).fetchone() == (
        conversation_id,
        "individual",
        None,
        20,
        10,
        int(users[1]),
        user0_span[0],
        user0_span[1],
        1,
        None,
        2,
        0,
    )

    assert check_dog_rates(connected_writer) == 10

    assert connected_writer.execute(
        "select * from participants where conversation=? and participant=?;",
        (conversation_id, int(users[0])),
    ).fetchone() == (
        int(users[0]),
        conversation_id,
        10,
        None,
        None,
        None,
    )

    assert connected_writer.execute(
        "select * from participants where conversation=? and participant=?;",
        (conversation_id, int(users[1])),
    ).fetchone() == (
        int(users[1]),
        conversation_id,
        10,
        None,
        None,
        None,
    )


@pytest.mark.asyncio
async def test_onesided_individual_conversation(writer: TwitterDataWriter):
    conversation_id = "one-sided conversation"
    talking_user = DOG_RATES
    start_time = "2010-06-06T01:00:00.543Z"
    end_time = "2010-09-06T01:00:00.345Z"
    messages = generate_messages(
        5, start_time, end_time, conversation_id, talking_user, MAIN_USER_ID
    )

    for message in messages:
        writer.add_message(message)
    await writer.finalize()

    assert writer.execute(
        "select * from conversations where id=?;", (conversation_id,)
    ).fetchone() == (
        conversation_id,
        "individual",
        None,
        5,
        0,
        int(talking_user),
        start_time,
        end_time,
        0,
        None,
        2,
        0,
    )

    assert check_dog_rates(writer) == 5

    assert writer.execute(
        "select * from participants where conversation=? and participant=?;",
        (conversation_id, int(talking_user)),
    ).fetchone() == (
        int(talking_user),
        conversation_id,
        5,
        None,
        None,
        None,
    )

    assert writer.execute(
        "select * from participants where conversation=? and participant=?;",
        (conversation_id, MAIN_USER_ID),
    ).fetchone() == (
        MAIN_USER_ID,
        conversation_id,
        0,
        None,
        None,
        None,
    )


@pytest.mark.asyncio
async def test_othersided_individual_conversation(writer: TwitterDataWriter):
    start_time = "2015-10-10T07:07:07.777Z"
    end_time = "2020-10-10T07:07:07.777Z"
    conversation_id = "you-talking"
    messages = generate_messages(
        8, start_time, end_time, conversation_id, MAIN_USER_ID, DOG_RATES
    )
    for message in messages:
        writer.add_message(message)
    await writer.finalize()

    assert writer.execute(
        "select * from conversations where id=?;", (conversation_id,)
    ).fetchone() == (
        conversation_id,
        "individual",
        None,
        8,
        8,
        DOG_RATES,
        start_time,
        end_time,
        1,
        None,
        2,
        0,
    )

    assert check_dog_rates(writer) == 0

    assert writer.execute(
        "select * from participants where conversation=? and participant=?;",
        (conversation_id, DOG_RATES),
    ).fetchone() == (
        DOG_RATES,
        conversation_id,
        0,
        None,
        None,
        None,
    )

    assert writer.execute(
        "select * from participants where conversation=? and participant=?;",
        (conversation_id, MAIN_USER_ID),
    ).fetchone() == (
        MAIN_USER_ID,
        conversation_id,
        8,
        None,
        None,
        None,
    )


@pytest.mark.asyncio
async def test_simple_group_conversation(writer: TwitterDataWriter):
    starts = (
        "2010-05-05T12:40:01.000Z",
        "2010-05-05T13:40:01.000Z",
        "2010-05-05T15:50:01.000Z",
    )
    ends = (
        "2011-05-05T12:40:01.000Z",
        "2012-05-05T13:40:01.000Z",
        "2013-05-05T15:50:01.000Z",
    )
    message_counts = (10, 12, 15)
    users = (MAIN_USER_ID, DOG_RATES, OBAMA)
    conversation_id = "simple-group"
    messages = sorted(
        generate_group_conversation(
            message_counts, starts, ends, conversation_id, users
        )
        + [
            {
                "type": "conversationNameUpdate",
                "initiatingUserId": users[1],
                "name": "bim bam boom",
                "createdAt": "2011-02-08T18:43:50.249Z",
                "conversationId": conversation_id,
            }
        ],
        key=lambda x: x["createdAt"],
    )
    for message in messages:
        writer.add_message(message, True)
    await writer.finalize()

    assert writer.execute(
        "select * from conversations where id=?;", (conversation_id,)
    ).fetchone() == (
        conversation_id,
        "group",
        None,
        sum(message_counts),
        message_counts[0],
        None,
        starts[0],
        ends[2],
        1,
        None,
        len(users),
        1,
    )

    assert check_dog_rates(writer) == message_counts[1]

    for i, user in enumerate(users):
        assert writer.execute(
            "select * from participants where participant=? and conversation=?;",
            (int(user), conversation_id),
        ).fetchone() == (
            int(user),
            conversation_id,
            message_counts[i],
            None,
            None,
            None,
        )


@pytest.mark.asyncio
async def test_group_conversations_started_by_various_events(writer):

    starts = (
        "2010-05-05T12:40:01.000Z",
        "2010-05-05T13:40:01.000Z",
        "2010-05-05T15:50:01.000Z",
    )
    ends = (
        "2011-05-05T12:40:01.000Z",
        "2012-05-05T13:40:01.000Z",
        "2013-05-05T15:50:01.000Z",
    )
    message_counts = (78, 102, 52)
    users = (MAIN_USER_ID, DOG_RATES, OBAMA)

    base_conversation = lambda cname: generate_group_conversation(
        message_counts, starts, ends, cname, users
    )

    conversation_start_time = "2009-12-20T10:51:37.176Z"

    all_messages = []

    added_to_id = "added-to"
    added_to = [
        {
            "type": "joinConversation",
            "conversationId": added_to_id,
            "initiatingUserId": str(DOG_RATES),
            "participantsSnapshot": [str(OBAMA)],
            "createdAt": conversation_start_time,
        }
    ] + base_conversation(added_to_id)

    assert isinstance(added_to, list)

    all_messages += added_to

    someone_joined_id = "someone-joined"
    someone_joined = [
        {
            "type": "participantsJoin",
            "conversationId": someone_joined_id,
            "userIds": [str(OBAMA)],
            "initiatingUserId": str(DOG_RATES),
            "createdAt": conversation_start_time,
        }
    ] + base_conversation(someone_joined_id)

    all_messages += someone_joined

    someone_left_id = "someone-left"
    someone_left = [
        {
            "type": "participantsLeave",
            "conversationId": someone_left_id,
            "userIds": [str(AMAZINGPHIL)],
            "createdAt": conversation_start_time,
        }
    ] + base_conversation(someone_left_id)

    all_messages += someone_left

    name_update_id = "name-updated"
    name_update = [
        {
            "type": "conversationNameUpdate",
            "conversationId": name_update_id,
            "initiatingUserId": str(OBAMA),
            "name": "something's turning over",
            "createdAt": conversation_start_time,
        }
    ] + base_conversation(name_update_id)

    all_messages += name_update

    for message in all_messages:
        writer.add_message(message, True)
    await writer.finalize()

    for conversation_id in (
        added_to_id,
        someone_joined_id,
        someone_left_id,
        name_update_id,
    ):
        assert writer.execute(
            "select first_time from conversations where id=?;", (conversation_id,)
        ).fetchone() == (conversation_start_time,)

    assert check_dog_rates(writer) == message_counts[1] * 4

    assert (
        writer.execute(
            """select messages_sent from participants
            where conversation=? and participant=?;""",
            (someone_joined_id, DOG_RATES),
        ).fetchone()[0]
        == message_counts[1]
    )


@pytest.mark.asyncio
async def test_conversation_ended_by_various_events(writer: TwitterDataWriter):
    starts = (
        "2010-05-05T12:40:01.000Z",
        "2010-05-05T13:40:01.000Z",
        "2010-05-05T15:50:01.000Z",
    )
    ends = (
        "2011-05-05T12:40:01.000Z",
        "2012-05-05T13:40:01.000Z",
        "2013-05-05T15:50:01.000Z",
    )
    message_counts = (78, 102, 52)
    users = (MAIN_USER_ID, DOG_RATES, OBAMA)

    base_conversation = lambda cname: generate_group_conversation(
        message_counts, starts, ends, cname, users
    )

    conversation_end_time = "2019-12-20T10:51:37.176Z"

    all_messages = []

    added_to_id = "added-to"
    added_to = base_conversation(added_to_id) + [
        {
            "type": "joinConversation",
            "conversationId": added_to_id,
            "initiatingUserId": str(DOG_RATES),
            "participantsSnapshot": [str(OBAMA)],
            "createdAt": conversation_end_time,
        }
    ]

    all_messages += added_to

    someone_joined_id = "someone-joined"
    someone_joined = base_conversation(someone_joined_id) + [
        {
            "type": "participantsJoin",
            "conversationId": someone_joined_id,
            "userIds": [str(OBAMA)],
            "initiatingUserId": str(DOG_RATES),
            "createdAt": conversation_end_time,
        }
    ]

    all_messages += someone_joined

    someone_left_id = "someone-left"
    someone_left = base_conversation(someone_left_id) + [
        {
            "type": "participantsLeave",
            "conversationId": someone_left_id,
            "userIds": [str(AMAZINGPHIL)],
            "createdAt": conversation_end_time,
        }
    ]

    all_messages += someone_left

    name_update_id = "name-updated"
    name_update = base_conversation(name_update_id) + [
        {
            "type": "conversationNameUpdate",
            "conversationId": name_update_id,
            "initiatingUserId": str(OBAMA),
            "name": "something's turning over",
            "createdAt": conversation_end_time,
        }
    ]

    all_messages += name_update

    for message in all_messages:
        writer.add_message(message, True)
    await writer.finalize()

    for conversation_id in (
        added_to_id,
        someone_joined_id,
        someone_left_id,
        name_update_id,
    ):
        assert writer.execute(
            "select last_time from conversations where id=?;", (conversation_id,)
        ).fetchone() == (conversation_end_time,)
