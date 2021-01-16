from pytest import fixture, mark
from tests.message_utils import (
    writer,
    reader,
    generate_messages,
    generate_group_conversation,
    random_datestring,
    random_2000s_datestring,
    random_2010s_datestring,
    MAIN_USER_ID,
    DOG_RATES,
    OBAMA,
    AMAZINGPHIL,
)
from tornado.ioloop import IOLoop
from ArchiveAccess.DBWrite import TwitterDataWriter
from ArchiveAccess import DBRead
from ArchiveAccess.DBRead import TwitterDataReader, ArchivedUserSummary, ArchivedUser


@fixture(scope="module")
def event_loop():
    return IOLoop.current().asyncio_loop


@mark.asyncio
async def test_get_users_by_id(writer: TwitterDataWriter, reader: TwitterDataReader):
    conversation_id = "users by id test"
    obama_message = generate_messages(
        1, random_datestring(), "", conversation_id, OBAMA
    )[0]
    dog_rates_message = generate_messages(
        1, random_datestring(), "", conversation_id, DOG_RATES
    )[0]
    amazing_phil_message = generate_messages(
        1, random_datestring(), "", conversation_id, AMAZINGPHIL
    )[0]

    for message in (obama_message, dog_rates_message, amazing_phil_message):
        writer.add_message(message, True)
    await writer.finalize()

    assert reader.get_users_by_id((OBAMA, AMAZINGPHIL)) == [
        ArchivedUserSummary(
            str(OBAMA),
            "",
            str(OBAMA),
            DBRead.DEFAULT_DISPLAY_NAME,
            DBRead.USER_AVATAR_DEFAULT_URL,
            False,
        ),
        ArchivedUserSummary(
            str(AMAZINGPHIL),
            "",
            str(AMAZINGPHIL),
            DBRead.DEFAULT_DISPLAY_NAME,
            DBRead.USER_AVATAR_DEFAULT_URL,
            False,
        ),
    ]

    assert reader.get_users_by_id((DOG_RATES,), sidecar=False) == [
        ArchivedUser(
            str(DOG_RATES),
            "",
            "dog_rates",
            "We Rate Dogs",
            f"{DBRead.AVATAR_API_URL}{DOG_RATES}.jpg",
            True,
            1,
            "sample bio",
            "",
        )
    ]


@mark.asyncio
async def test_get_users_by_message_count(
    writer: TwitterDataWriter, reader: TwitterDataReader
):
    # conversations 1 and 2
    # first person has 30 in one and 20 in two. next person has 10 in one and 30 in two.
    # so if you sort by overall messages, the first person has more, but if you sort
    # by messages in convo two, the second person has more.

    conversations = (
        "message-count-test-1",
        "message-count-test-2",
        "many-users-test",
    )
    conversation1 = generate_group_conversation(
        (30, 10),
        (random_2000s_datestring(), random_2000s_datestring()),
        (random_2010s_datestring(), random_2010s_datestring()),
        conversations[0],
        (DOG_RATES, MAIN_USER_ID),
    )
    conversation2 = generate_group_conversation(
        (20, 30),
        (random_2000s_datestring(), random_2000s_datestring()),
        (random_2010s_datestring(), random_2010s_datestring()),
        conversations[1],
        (DOG_RATES, MAIN_USER_ID),
    )
    # this conversation has users with ids 1-29 (inclusive) with within-conversation
    # messages counts that are below that of the two "real" users referenced above.
    # they are created in order with each having a lower message count than the last
    # (so they're created in the same order that get_users_by_message_count should
    # return them in)
    conversation3 = generate_group_conversation(
        range(29, 0, -1),
        [random_2000s_datestring()] * 29,
        [random_2010s_datestring()] * 29,
        conversations[2],
        range(1, 30),
    )

    for message in conversation1 + conversation2 + conversation3:
        writer.add_message(message, True)
    await writer.finalize()

    assert reader.get_users_by_message_count(1, conversations[1])[0].id == str(
        MAIN_USER_ID
    )

    ordered_users = reader.get_users_by_message_count(1)
    assert ordered_users[0].id == str(DOG_RATES)
    # skipping the two "real" users, this checks if the other users are being
    # returned in the order that they were created in and paginated properly
    assert [int(x.id) for x in ordered_users[2:22]] == list(range(1, 19))
    ordered_users_2 = reader.get_users_by_message_count(2)
    assert [int(x.id) for x in ordered_users_2] == list(range(19, 30))


@mark.asyncio
async def test_set_user_nicknotes(
    writer: TwitterDataWriter, reader: TwitterDataReader
):
    writer.add_message(
        generate_messages(1, random_2010s_datestring(), "", "whatevs", OBAMA)[0],
        True,
    )
    await writer.finalize()

    reader.set_user_nickname(OBAMA, "obama")
    assert reader.get_users_by_id((OBAMA,))[0].nickname == "obama"

    reader.set_user_notes(OBAMA, "was president")
    assert reader.get_users_by_id((OBAMA,), False)[0].notes == "was president"
