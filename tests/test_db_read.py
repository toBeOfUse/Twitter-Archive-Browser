from pytest import fixture, mark
from tests.message_utils import (
    writer,
    reader,
    generate_messages,
    generate_conversation,
    generate_name_update,
    get_random_text,
    random_datestring,
    random_2000s_datestring,
    random_2010s_datestring,
    unique_id,
    MAIN_USER_ID,
    DOG_RATES,
    OBAMA,
    AMAZINGPHIL,
)
from random import shuffle, choice, randint
from tornado.ioloop import IOLoop
from pprint import pprint
from ArchiveAccess.DBWrite import TwitterDataWriter
from ArchiveAccess import DBRead
from ArchiveAccess.DBRead import (
    TwitterDataReader,
    ArchivedUserSummary,
    ArchivedUser,
    Conversation,
    Message,
    NameUpdate,
    ParticipantJoin,
    ParticipantLeave,
)


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
    conversation1 = generate_conversation(
        (30, 10),
        (random_2000s_datestring(), random_2000s_datestring()),
        (random_2010s_datestring(), random_2010s_datestring()),
        conversations[0],
        (DOG_RATES, MAIN_USER_ID),
    )
    conversation2 = generate_conversation(
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
    conversation3 = generate_conversation(
        range(29, 0, -1),
        [random_2000s_datestring()] * 29,
        [random_2010s_datestring()] * 29,
        conversations[2],
        range(1, 30),
    )

    for message in conversation1 + conversation2 + conversation3:
        writer.add_message(message, True)
    await writer.finalize()

    conversation2_users = reader.get_users_by_message_count(1, conversations[1])
    assert conversation2_users[0].id == str(MAIN_USER_ID)
    assert len(conversation2_users) == 2

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


@mark.asyncio
async def test_conversations_by_time(
    writer: TwitterDataWriter, reader: TwitterDataReader
):

    page_length = DBRead.CONVERSATIONS_PER_PAGE

    group_ids = [get_random_text() for _ in range(page_length + 2)]
    group_messages = sum(
        [
            generate_messages(
                2,
                random_2000s_datestring(),
                random_2010s_datestring(),
                group_id,
                10101,
            )
            for group_id in group_ids
        ],
        [],
    )

    individual_ids = [get_random_text() for _ in range(page_length + 2)]
    individual_messages = sum(
        [
            generate_messages(
                2,
                random_2000s_datestring(),
                random_2010s_datestring(),
                individual_id,
                MAIN_USER_ID,
                next(unique_id),
            )
            for individual_id in individual_ids
        ],
        [],
    )

    messages = individual_messages + group_messages

    # since every conversation has two messages, every other message starting with
    # the first one is the first in a conversation, and every other message starting
    # with the second one is the last; the firsts will end up in ascending_ids and
    # the lasts in descending_ids
    ascending_ids = [
        m["conversationId"]
        for m in sorted(messages[::2], key=lambda x: x["createdAt"])
    ]
    descending_ids = [
        m["conversationId"]
        for m in sorted(messages[1::2], key=lambda x: x["createdAt"], reverse=True)
    ]

    # the same conversation ids should be in both lists; just sorted according to
    # different times
    assert set(ascending_ids) == set(descending_ids)

    for message in individual_messages:
        writer.add_message(message)
    for message in group_messages:
        writer.add_message(message, True)
    await writer.finalize()

    # check !group and !individual results:

    assert reader.get_conversations_by_time(1, group=False, individual=False) == []

    # check group + individual conversation results:

    asc_conversations_p1 = reader.get_conversations_by_time(1)
    assert ascending_ids[0:page_length] == [x.id for x in asc_conversations_p1]
    asc_conversations_p2 = reader.get_conversations_by_time(2)
    assert ascending_ids[page_length : page_length * 2] == [
        x.id for x in asc_conversations_p2
    ]

    dsc_conversations = reader.get_conversations_by_time(1, asc=False)
    assert [x.id for x in dsc_conversations] == descending_ids[0:page_length]

    # check individual conversation results:
    iac = reader.get_conversations_by_time(1, group=False)
    assert [i.id for i in iac] == [x for x in ascending_ids if x in individual_ids][
        0:page_length
    ]

    # check group conversation results:
    gdc = reader.get_conversations_by_time(2, asc=False, individual=False)
    assert [i.id for i in gdc] == [x for x in descending_ids if x in group_ids][
        page_length : page_length * 2
    ]


@mark.asyncio
async def test_conversations_by_message_count(
    writer: TwitterDataWriter, reader: TwitterDataReader
):
    """generate two conversations; one (group) with many messages and one
    (individual) with many messages from you. check that they're both returned real
    good. this test does not test for pagination bc it's the same code as the other
    ones"""

    conversation1 = generate_conversation(
        (50, 40),
        [random_2000s_datestring()] * 2,
        [random_2010s_datestring()] * 2,
        "group",
        (OBAMA, AMAZINGPHIL),
    )

    conversation2 = generate_conversation(
        (60, 10),
        [random_2000s_datestring()] * 2,
        [random_2010s_datestring()] * 2,
        "individual",
        (MAIN_USER_ID, OBAMA),
        False,
    )

    for message in conversation1:
        writer.add_message(message, True)
    for message in conversation2:
        writer.add_message(message)
    await writer.finalize()

    assert (
        reader.get_conversations_by_message_count(1, True, True, True)[0].id
        == "individual"
    )

    assert (
        reader.get_conversations_by_message_count(1, True, True, False)[0].id
        == "group"
    )

    assert (
        reader.get_conversations_by_message_count(1, True, False, True)[0].id
        == "group"
    )

    assert (
        reader.get_conversations_by_message_count(1, False, True, False)[0].id
        == "individual"
    )


@mark.asyncio
async def test_conversations_by_user(
    writer: TwitterDataWriter, reader: TwitterDataReader
):
    """create a conversation or two with random users and then like 30 with a
    particular user. make sure they come back in the right order. this test also
    doesn't bother testing pagination"""
    dummy_convo = generate_messages(
        2,
        random_2000s_datestring(),
        random_2010s_datestring(),
        "won't be returned",
        OBAMA,
        AMAZINGPHIL,
    )

    messages_with_dog_rates = []
    for how_many in range(30, 0, -1):
        messages_with_dog_rates += generate_messages(
            how_many,
            random_2000s_datestring(),
            random_2010s_datestring(),
            get_random_text(),
            DOG_RATES,
        )

    descending_ids = []
    prev_id = ""
    for message in messages_with_dog_rates:
        if message["conversationId"] != prev_id:
            descending_ids.append(message["conversationId"])
            prev_id = message["conversationId"]

    shuffle(messages_with_dog_rates)

    for message in dummy_convo:
        writer.add_message(message)
    for message in messages_with_dog_rates:
        writer.add_message(message, True)
    await writer.finalize()

    assert [
        c.id for c in reader.get_conversations_by_user(DOG_RATES, 1)
    ] == descending_ids[: DBRead.CONVERSATIONS_PER_PAGE]


@mark.asyncio
async def test_conversation_by_id(
    writer: TwitterDataWriter, reader: TwitterDataReader
):
    conversation_id = "a-conversation"
    convo = generate_conversation(
        (10, 15),
        ("2009-09-09T05:05:05.000Z", "2009-10-09T05:05:05.000Z"),
        ("2010-09-09T05:05:05.000Z", "2010-10-09T05:05:05.000Z"),
        conversation_id,
        (MAIN_USER_ID, AMAZINGPHIL),
        False,
    )
    convo += generate_conversation(
        (20, 20),
        [random_2000s_datestring()] * 2,
        [random_2010s_datestring()] * 2,
        "decoy-conversation",
        (MAIN_USER_ID, DOG_RATES),
        False,
    )

    for message in convo:
        writer.add_message(message)
    await writer.finalize()

    result = reader.get_conversation_by_id(conversation_id)

    assert result == Conversation(
        conversation_id,
        "individual",
        25,
        10,
        "2009-09-09T05:05:05.000Z",
        "2010-10-09T05:05:05.000Z",
        2,
        0,
        True,
        ArchivedUserSummary(
            str(AMAZINGPHIL),
            "",
            str(AMAZINGPHIL),
            DBRead.DEFAULT_DISPLAY_NAME,
            DBRead.USER_AVATAR_DEFAULT_URL,
            False,
        ),
        None,
        f"{DBRead.DEFAULT_DISPLAY_NAME} (@{AMAZINGPHIL})",
        DBRead.USER_AVATAR_DEFAULT_URL,
        "",
    )


@mark.asyncio
async def test_conversation_names(
    writer: TwitterDataWriter, reader: TwitterDataReader
):
    """generate more than name_updates_per_page name updates for two conversations;
    check the first page of the first conversation and the second page of the second;
    then also check to make sure that the conversation records include the most
    recent names"""
    updates = []
    for i in range(DBRead.CONVERSATION_NAMES_PER_PAGE + 5):
        updates.append(
            generate_name_update(
                choice((MAIN_USER_ID, AMAZINGPHIL, OBAMA, randint(1, 2 ** 60))),
                get_random_text(),
                random_2010s_datestring(),
                "conversation-one",
            )
        )
    conversation_one_names_asc = [
        x["name"] for x in sorted(updates, key=lambda x: x["createdAt"])
    ]
    for i in range(DBRead.CONVERSATION_NAMES_PER_PAGE + 5):
        updates.append(
            generate_name_update(
                choice((MAIN_USER_ID, OBAMA, DOG_RATES, randint(1, 2 ** 60))),
                get_random_text(),
                random_2010s_datestring(),
                "conversation-two",
            )
        )
    conversation_two_names_asc = [
        x["name"]
        for x in sorted(
            updates[len(conversation_one_names_asc) :], key=lambda x: x["createdAt"]
        )
    ]

    for update in updates:
        writer.add_message(update, True)
    await writer.finalize()

    assert (
        reader.get_conversation_by_id("conversation-one").name
        == conversation_one_names_asc[-1]
    )

    assert (
        reader.get_conversation_by_id("conversation-two").name
        == conversation_two_names_asc[-1]
    )

    conversation_one_results = reader.get_conversation_names("conversation-one")

    assert [
        x.new_name for x in conversation_one_results["results"]
    ] == conversation_one_names_asc[0 : DBRead.CONVERSATION_NAMES_PER_PAGE]

    assert set(x.id for x in conversation_one_results["users"]) == set(
        x.initiator for x in conversation_one_results["results"]
    )

    conversation_two_results = reader.get_conversation_names(
        "conversation-two", False, 2
    )

    assert [x.new_name for x in conversation_two_results["results"]] == [
        x for x in reversed(conversation_two_names_asc)
    ][DBRead.CONVERSATION_NAMES_PER_PAGE :]

    assert [x.update_time for x in conversation_two_results["results"]] == [
        x.sort_by_timestamp for x in conversation_two_results["results"]
    ]


@mark.asyncio
async def test_conversation_notes(
    writer: TwitterDataWriter, reader: TwitterDataReader
):
    writer.add_message(
        generate_messages(
            1, random_2000s_datestring(), "", "a-conversation", MAIN_USER_ID
        )[0],
        True,
    )
    await writer.finalize()

    reader.set_conversation_notes("a-conversation", "this is a conversation")

    assert (
        reader.get_conversation_by_id("a-conversation").notes
        == "this is a conversation"
    )


@mark.asyncio
async def test_traverse_messages(
    writer: TwitterDataWriter, reader: TwitterDataReader
):
    # testing traversing messages. to test everything, we should have a main
    # conversation, a smaller conversation that one user from the main conversation
    # is in (to test that using the user parameter brings up both), and a third small
    # conversation that will also be show up with no user and conversation parameters
    # specified. the main conversation should include name changes, joins, and
    # leaves, to make sure those can be prevailed upon to show up. the idea would
    # probably be to have non-message messagelikes in the input at regular intervals
    # so that the output can be taken apart in sections and inspected appropriately.
    # so a main conversation like:

    # 20 normal messages
    # name change event
    # 20 normal messages
    # leaving event
    # 20 normal messages
    # joining event
    # 20 normal messages
    # you being added to the conversation

    # i think the best approach so as not to assume things about the
    # messages-per-page in the tests would be to get every page of results for a
    # specific set of paramaters and concatenate them together and inspect the
    # results - and then we can take apart the total output to make sure it looks
    # like the above.

    # make sure to test beginning and end and then go forward/backward starting there
    # to get the whole conversation, as described above, to make sure those work; and
    # then test after and before with real timestamps to just grab like 10 messages
    # at the beginning and end to make sure those work. at is even more fun in that
    # way.

    # search can be tested in a separaate method since it demands specific messages
    # with real words and doesn't include events and such.

    # this first conversation we are generating will be traversed using the
    # conversation parameter. dog_rates will be seen to join and leave the
    # conversation to ensure those events are returned properly.
    dog_rates_span = ("2007-09-09T05:05:45.556Z", "2012-09-09T05:05:45.556Z")

    main_messages = generate_conversation(
        [20] * 4,
        [random_2000s_datestring() for _ in range(3)] + [dog_rates_span[0]],
        [random_2010s_datestring() for _ in range(3)] + [dog_rates_span[1]],
        "main",
        (MAIN_USER_ID, AMAZINGPHIL, OBAMA, DOG_RATES),
    )

    # this name change will show up in the conversation and user searches
    name_change = generate_name_update(
        AMAZINGPHIL, "new_name", random_2000s_datestring(), "main"
    )

    # this one will not
    other_name_change = generate_name_update(
        MAIN_USER_ID, "other_new_name", random_2000s_datestring(), "main"
    )

    participant_leaving = {
        "userIds": [str(DOG_RATES)],
        # right after the last dog_rates message
        "createdAt": "2012-10-09T05:05:45.556Z",
        "conversationId": "main",
        "type": "participantsLeave",
    }

    participant_joining = {
        "initiatingUserId": str(OBAMA),
        "userIds": [str(DOG_RATES)],
        # right before the first dog_rates message
        "createdAt": "2007-08-09T05:05:45.556Z",
        "conversationId": "main",
        "type": "participantsJoin",
    }

    us_being_added = {
        "initiatingUserId": str(OBAMA),
        "participantsSnapshot": [str(AMAZINGPHIL)],
        "createdAt": "1999-12-20T10:51:37.176Z",
        "type": "joinConversation",
        "conversationId": "main",
    }

    main_conversation = sorted(
        main_messages
        + [
            name_change,
            other_name_change,
            participant_joining,
            participant_leaving,
            us_being_added,
        ],
        key=lambda x: x["createdAt"],
    )

    # this conversation provides additional messages that will show up when
    # traversing messages when using the user parameter set to AMAZINGPHIL.
    user_conversation = generate_conversation(
        (30, 20),
        [random_2000s_datestring() for _ in range(2)],
        [random_2010s_datestring() for _ in range(2)],
        "user",
        (MAIN_USER_ID, AMAZINGPHIL),
        False,
    )

    # redundant copy of specific messages from above conversation; do not send to
    # writer
    phil_messages = sorted(
        [
            x
            for x in main_messages + user_conversation
            if x["senderId"] == str(AMAZINGPHIL)
        ],
        key=lambda x: x["createdAt"],
    )

    # these messages should not show up until all messages are retrieved
    decoy_conversation = generate_conversation(
        (30, 20),
        [random_2000s_datestring() for _ in range(2)],
        [random_2010s_datestring() for _ in range(2)],
        "decoy",
        (OBAMA, DOG_RATES),
    )

    all_messages = sorted(
        main_conversation + decoy_conversation + user_conversation,
        key=lambda x: x["createdAt"],
    )

    for message in main_conversation + decoy_conversation:
        writer.add_message(message, True)
    for message in user_conversation:
        writer.add_message(message)
    await writer.finalize()

    main_conversation_results = []
    traverse_from = "beginning"
    while result := reader.traverse_messages(
        conversation="main", after=traverse_from
    )["results"]:
        main_conversation_results += result
        traverse_from = result[-1].sort_by_timestamp

    assert len(main_conversation_results) == len(main_conversation)

    for i in range(len(main_conversation_results)):
        result = main_conversation_results[i]
        original = main_conversation[i]
        if isinstance(result, Message):
            assert result.id == str(original["id"])
        if isinstance(result, ParticipantJoin) or isinstance(
            result, ParticipantLeave
        ):
            assert result.sort_by_timestamp == original["createdAt"]
        if isinstance(result, NameUpdate):
            assert result.sort_by_timestamp == original["createdAt"]
            assert result.new_name == original["name"]

    reverse_conversation_results = []
    traverse_from = "end"
    while result := reader.traverse_messages(
        conversation="main", before=traverse_from
    )["results"]:
        reverse_conversation_results = result + reverse_conversation_results
        traverse_from = result[0].sort_by_timestamp

    assert len(reverse_conversation_results) == len(main_conversation)

    assert main_conversation_results == reverse_conversation_results

    after_timestamp = main_conversation_results[-10].sort_by_timestamp

    assert (
        reader.traverse_messages(conversation="main", after=after_timestamp)[
            "results"
        ]
        == main_conversation_results[-9:]
    )

    before_timestamp = main_conversation_results[10].sort_by_timestamp

    assert (
        reader.traverse_messages(conversation="main", before=before_timestamp)[
            "results"
        ]
        == main_conversation_results[:10]
    )

    at_timestamp = main_messages[30]["createdAt"]
    at_start_timestamp = main_messages[11]["createdAt"]
    at_end_timestamp = main_messages[50]["createdAt"]

    at_results = reader.traverse_messages(conversation="main", at=at_timestamp)[
        "results"
    ]
    assert (
        next(x for x in at_results if isinstance(x, Message)).sort_by_timestamp
        == at_start_timestamp
    )
    assert (
        next(
            x for x in reversed(at_results) if isinstance(x, Message)
        ).sort_by_timestamp
        == at_end_timestamp
    )

    assert at_results == [
        x
        for x in main_conversation_results
        if x.sort_by_timestamp >= at_results[0].sort_by_timestamp
        and x.sort_by_timestamp <= at_results[-1].sort_by_timestamp
    ]

    user_results = []
    traverse_from = "beginning"
    while results := reader.traverse_messages(user=AMAZINGPHIL, after=traverse_from)[
        "results"
    ]:
        user_results += results
        traverse_from = results[-1].sort_by_timestamp

    assert [x.id for x in user_results if isinstance(x, Message)] == [
        x["id"] for x in phil_messages
    ]

    user_name_changes = [x for x in user_results if isinstance(x, NameUpdate)]
    assert len(user_name_changes) == 1
    assert user_name_changes[0].sort_by_timestamp == name_change["createdAt"]

    all_results = []
    traverse_from = "beginning"
    results = "placeholder"
    users = []
    while True:
        results_and_users = reader.traverse_messages(after=traverse_from)
        results = results_and_users["results"]
        if not results:
            break
        users += results_and_users["users"]
        all_results += results
        traverse_from = results[-1].sort_by_timestamp

    assert len(all_results) == len(all_messages)

    user_ids = set(x.id for x in users)
    for message in all_results:
        for user_id in message.user_ids:
            assert str(user_id) in user_ids


@mark.asyncio
async def test_text_search(writer: TwitterDataWriter, reader: TwitterDataReader):
    texts = ("i am home", "home i am", "being at home", "home is here")

    messages = generate_messages(
        20,
        random_2000s_datestring(),
        random_2010s_datestring(),
        "searchyconvo",
        MAIN_USER_ID,
        AMAZINGPHIL,
    )

    for i in range(len(texts)):
        messages[i]["text"] = texts[i]

    for message in messages:
        writer.add_message(message)
    await writer.finalize()

    results = reader.traverse_messages(after="beginning", search="home")["results"]
    assert len(results) == len(texts)


@mark.asyncio
async def test_get_message(writer: TwitterDataWriter, reader: TwitterDataReader):
    message_with_media = {
        "conversationId": "846137120209190912-3330610905",
        "createdAt": "2018-02-20T05:53:06.308Z",
        "id": "1",
        "mediaUrls": [
            "https://video.twimg.com/dm_video/995295295943700480/vid/1280x720/rVyBaawRDLp1f2AdJdkdkDIKdmKDIdLCVecgWinASM.mp4",
        ],
        "reactions": [],
        "recipientId": "846137120209190912",
        "senderId": "3330610905",
        "text": "Duis iaculis pretium lorem, id sodales ante accumsan nec. Maecenas. https://t.co/kuJj6jjLhJ",
        "type": "messageCreate",
        "urls": [
            {
                "url": "https://t.co/kuJj6jjLhJ",
                "expanded": "https://twitter.com/messages/media/700921094409056259",
                "display": "pic.twitter.com/kuJj6jjLhJ",
            }
        ],
    }

    message_with_link_and_reaction = {
        "conversationId": "846137120209190912-3330610905",
        "createdAt": "2017-09-26T09:00:00.000Z",
        "id": "2",
        "mediaUrls": [],
        "reactions": [
            {
                "senderId": "3330610905",
                "reactionKey": "funny",
                "eventId": "1320946773276291073",
                "createdAt": "2020-10-27T04:33:47.424Z",
            },
            {
                "senderId": "846137120209190912",
                "reactionKey": "heart",
                "eventId": "1320946773276291074",
                "createdAt": "2020-10-28T04:33:47.424Z",
            },
        ],
        "recipientId": "3330610905",
        "senderId": "846137120209190912",
        "text": "https://t.co/somenonsense In incididunt velit id commodo officia deserunt ad aliquip voluptate quis id cillum.",
        "type": "messageCreate",
        "urls": [
            {
                "url": "https://t.co/somenonsense",
                "expanded": "https://youtu.be/dQw4w9WgXcQ",
                "display": "youtu.be/dQw4w9WgXcQ",
            }
        ],
    }

    writer.add_message(message_with_media)
    writer.add_message(message_with_link_and_reaction)
    await writer.finalize()

    result_with_media = reader.get_message(1)["results"][0]
    assert result_with_media.id == message_with_media["id"]
    assert len(result_with_media.media) == len(message_with_media["mediaUrls"])
    assert (
        "/individual/"
        + message_with_media["id"]
        + "-"
        + message_with_media["mediaUrls"][0].split("/")[-1]
        == result_with_media.media[0].file_path
    )
    assert message_with_media["urls"][0]["url"] not in result_with_media.html_content

    result_with_links_and_reactions = reader.get_message(2)["results"][0]
    for reactions_result, reaction in zip(
        result_with_links_and_reactions.reactions,
        message_with_link_and_reaction["reactions"],
    ):
        assert reactions_result.creation_time == reaction["createdAt"]
        assert reactions_result.emotion == reaction["reactionKey"]
    assert (
        result_with_links_and_reactions.html_content
        == '<a href="https://youtu.be/dQw4w9WgXcQ">youtu.be/dQw4w9WgXcQ</a> In incididunt velit id commodo officia deserunt ad aliquip voluptate quis id cillum.'
    )


# TODO: also, have a test that makes sure that the different user objects are
# constructed correctly. and should probably go through and check conversation names
