"""these tests sequentially add messages to a test database and check that the
corresponding records were added. this module checks for the accuracy of the data
that are immediately added to the database when a message is added; information about
users obtained from the twitter api or final stats about conversations or
participants calculated in cache_conversation_stats.sql are assumed to be absent
here"""

from ArchiveAccess.DBWrite import TwitterDataWriter
from pytest import fixture
from collections import deque
from typing import Final
import re
from tests.message_utils import MAIN_USER_ID, writer

# todo: each dict could probably be a separate fixture
@fixture(scope="module")
def messages() -> deque[dict]:
    return deque(
        (
            {
                "conversationId": "846137120209190912-3330610905",
                "createdAt": "2017-01-01T09:00:00.000Z",
                "id": "901563245546405895",
                "mediaUrls": [],
                "reactions": [],
                "recipientId": "846137120209190912",
                "senderId": "3330610905",
                "text": "Culpa ut ut irure velit id duis.",
                "type": "messageCreate",
                "urls": [],
            },
            {
                "conversationId": "846137120209190912-3330610905",
                "createdAt": "2017-08-26T22:53:22.712Z",
                "id": "901563245546405896",
                "mediaUrls": [],
                "reactions": [
                    # TODO: technically, this data is inconsistent; the
                    # "recipientId" field indicates a message in an individual
                    # conversation, but someone is leaving a reaction who is not
                    # either the sender or the recipient. good enough for now; could
                    # be fixed if this fixture is ever refactored like it should be.
                    {
                        "senderId": "3330610905",
                        "reactionKey": "funny",
                        "eventId": "1320946773276291073",
                        "createdAt": "2020-10-27T04:33:47.424Z",
                    },
                    {
                        "senderId": "54456454645",
                        "reactionKey": "heart",
                        "eventId": "1320946773276291074",
                        "createdAt": "2020-10-28T04:33:47.424Z",
                    },
                ],
                "recipientId": "846137120209190912",
                "senderId": "3330610905",
                "text": "Proin commodo, velit id porta condimentum, ex turpis vestibulum purus.",
                "type": "messageCreate",
                "urls": [],
            },
            {
                "conversationId": "846137120209190912-3330610905",
                "createdAt": "2017-09-26T09:00:00.000Z",
                "id": "901563245546405865",
                "mediaUrls": [],
                "reactions": [],
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
            },
            {
                "conversationId": "846137120209190912-3330610905",
                "createdAt": "2018-02-20T05:53:06.308Z",
                "id": "9015632455440",
                "mediaUrls": [
                    "https://ton.twitter.com/dm/9015632455440/700921094430072832/f7JooNMW.jpg",
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
            },
            {
                "conversationId": "846137120209190912-3330610905",
                "createdAt": "2018-02-20T05:53:06.308Z",
                "id": "9015632455450",
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
            },
            {
                "conversationId": "846137120209190912-3330610906",
                "createdAt": "2018-02-20T05:53:06.308Z",
                "id": "9015632455460",
                "mediaUrls": [
                    "https://video.twimg.com/dm_gif/705625850826223617/STB-shdfkhsjKDJSFKJSj-unT0KsNH5zslGh.mp4"
                ],
                "reactions": [],
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
            },
            {
                "reactions": [],
                "urls": [],
                "text": "Donec sit amet turpis enim. Etiam id feugiat diam, non.",
                "mediaUrls": [],
                "senderId": "56783491",
                "id": "700928326240632835",
                "createdAt": "2016-02-20T06:21:50.277Z",
                "type": "messageCreate",
                "conversationId": "a_group_chat",
            },
            {
                "initiatingUserId": "864856772913184772",
                "name": "sphinx zone",
                "createdAt": "2019-02-08T18:43:50.249Z",
                "type": "conversationNameUpdate",
                "conversationId": "another_group_chat",
            },
            {
                "initiatingUserId": "56783491",
                "name": "bulldogs zone",
                "createdAt": "2017-02-08T18:43:50.249Z",
                "type": "conversationNameUpdate",
                "conversationId": "a_group_chat",
            },
            {
                "initiatingUserId": "16573941",
                "userIds": ["56783491"],
                "createdAt": "2016-02-09T01:38:06.141Z",
                "conversationId": "a_group_chat",
                "type": "participantsJoin",
            },
            {
                "userIds": ["18393773"],
                "createdAt": "2016-02-19T01:38:06.141Z",
                "conversationId": "a_group_chat",
                "type": "participantsLeave",
            },
            {
                "initiatingUserId": "16573941",
                "userIds": ["18393773"],
                "createdAt": "2016-02-09T05:38:06.141Z",
                "conversationId": "a_group_chat",
                "type": "participantsJoin",
            },
            {
                "initiatingUserId": "16573941",
                "userIds": ["813286", "10010"],
                "createdAt": "2016-02-09T05:38:06.141Z",
                "conversationId": "a_group_chat",
                "type": "participantsJoin",
            },
            {
                "initiatingUserId": "3307595502",
                "participantsSnapshot": [
                    "8132865",
                    "101",
                    "90420314",
                    "1588486417",
                    "5162861",
                    "4196983835",
                    "16573941",
                    "31239408",
                ],
                "createdAt": "2015-12-20T10:51:37.176Z",
                "type": "joinConversation",
                "conversationId": "a_group_chat",
            },
        )
    )


def test_db_initial_state(writer: TwitterDataWriter):
    assert writer.account == "test"
    assert writer.account_id == MAIN_USER_ID
    assert writer.execute("select * from me;").fetchone()[0] == MAIN_USER_ID


def test_add_normal_message(
    writer: TwitterDataWriter, messages: deque[dict]
) -> None:
    message_add_with_checks(writer, messages.popleft())


def test_add_message_with_reactions(
    writer: TwitterDataWriter, messages: deque[dict]
):
    message = messages.popleft()
    message_add_with_checks(writer, message)
    added_reactions = writer.execute(
        "select * from reactions where message=?;",
        (int(message["id"]),),
    ).fetchall()
    assert len(added_reactions) == 2
    for reaction in message["reactions"]:
        assert (
            reaction["reactionKey"],
            reaction["createdAt"],
            int(reaction["senderId"]),
            int(message["id"]),
        ) in added_reactions


def test_add_message_with_link(writer: TwitterDataWriter, messages: deque[dict]):
    message = messages.popleft()
    message_add_with_checks(writer, message)
    link = message["urls"][0]
    added_link = writer.execute(
        "select * from links where message=?;", (int(message["id"]),)
    ).fetchone()
    assert added_link == (
        link["expanded"],
        link["display"],
        link["url"],
        int(message["id"]),
    )


def test_add_message_with_media(writer: TwitterDataWriter, messages: deque[dict]):
    image_message = messages.popleft()
    message_add_with_checks(writer, image_message)
    image_url = image_message["mediaUrls"][0]
    image_url_comps = image_url.replace("https://", "").split("/")
    assert writer.execute(
        "select * from media where message=?", (int(image_message["id"]),)
    ).fetchone() == (
        int(image_url_comps[3]),
        image_url,
        "image",
        image_url_comps[-1],
        int(image_url_comps[2]),
        0,
    )

    video_message = messages.popleft()
    message_add_with_checks(writer, video_message)
    video_url = video_message["mediaUrls"][0]
    video_url_comps = video_url.replace("https://", "").split("/")
    assert writer.execute(
        "select * from media where message=?;", (int(video_message["id"]),)
    ).fetchone() == (
        int(video_url_comps[2]),
        video_url,
        "video",
        video_url_comps[-1],
        int(video_message["id"]),
        0,
    )

    gif_message = messages.popleft()
    message_add_with_checks(writer, gif_message, True)
    gif_url = gif_message["mediaUrls"][0]
    gif_url_comps = gif_url.replace("https://", "").split("/")
    assert writer.execute(
        "select * from media where message=?;", (int(gif_message["id"]),)
    ).fetchone() == (
        int(gif_url_comps[2]),
        gif_url,
        "gif",
        gif_url_comps[-1],
        int(gif_message["id"]),
        1,
    )


def test_add_group_message(writer: TwitterDataWriter, messages: deque[dict]):
    message_add_with_checks(writer, messages.popleft(), True)


def test_new_convo_name_update(writer: TwitterDataWriter, messages: deque[dict]):
    check_name_update(writer, messages.popleft())


def test_old_convo_name_update(writer: TwitterDataWriter, messages: deque[dict]):
    check_name_update(writer, messages.popleft())


def test_known_participant_join(writer: TwitterDataWriter, messages: deque[dict]):
    join_event = messages.popleft()
    writer.add_message(join_event, True)
    check_conversation(writer, join_event, True)
    check_user(writer, join_event["initiatingUserId"])
    check_participant(
        writer, join_event["initiatingUserId"], join_event["conversationId"]
    )
    for user in join_event["userIds"]:
        check_user(writer, user)
        assert writer.execute(
            "select * from participants where participant=? and conversation=?;",
            (int(user), join_event["conversationId"]),
        ).fetchone() == (
            int(user),
            join_event["conversationId"],
            None,
            join_event["createdAt"],
            None,
            int(join_event["initiatingUserId"]),
        )


def test_join_after_leave(writer: TwitterDataWriter, messages: deque[dict]):
    leave_event = messages.popleft()
    writer.add_message(leave_event, True)
    check_conversation(writer, leave_event, True)
    for user in leave_event["userIds"]:
        check_user(writer, user)
        assert writer.execute(
            "select * from participants where participant=? and conversation=?;",
            (int(user), leave_event["conversationId"]),
        ).fetchone() == (
            int(user),
            leave_event["conversationId"],
            None,
            None,
            leave_event["createdAt"],
            None,
        )

    join_event = messages.popleft()
    writer.add_message(join_event, True)
    check_conversation(writer, join_event, True)
    check_participant(
        writer, join_event["initiatingUserId"], join_event["conversationId"]
    )
    user = join_event["userIds"][0]
    check_user(writer, user)
    assert writer.execute(
        "select * from participants where participant=? and conversation=?;",
        (int(user), join_event["conversationId"]),
    ).fetchone() == (
        int(user),
        join_event["conversationId"],
        None,
        join_event["createdAt"],
        # todo: with separate fixtures for each test's data this wouldn't have to be
        # hard-coded; it can be taken from the data for the above tests
        "2016-02-19T01:38:06.141Z",
        16573941,
    )


def test_new_participants_join(writer: TwitterDataWriter, messages: deque[dict]):
    join_event = messages.popleft()
    writer.add_message(join_event, True)
    check_conversation(writer, join_event, True)
    check_participant(
        writer, join_event["initiatingUserId"], join_event["conversationId"]
    )
    for user in join_event["userIds"]:
        check_user(writer, user)
        assert writer.execute(
            "select * from participants where participant=? and conversation=?;",
            (int(user), join_event["conversationId"]),
        ).fetchone() == (
            int(user),
            join_event["conversationId"],
            None,
            join_event["createdAt"],
            None,
            int(join_event["initiatingUserId"]),
        )


def test_self_being_added(writer: TwitterDataWriter, messages: deque[dict]):
    message = messages.popleft()
    writer.add_message(message, True)
    assert writer.execute(
        "select * from conversations where id=?;", (message["conversationId"],)
    ).fetchone() == (
        message["conversationId"],
        "group",
        None,
        None,
        None,
        None,
        message["createdAt"],
        None,
        0,
        int(message["initiatingUserId"]),
        None,
        None,
    )
    check_user(writer, message["initiatingUserId"])
    check_participant(writer, message["initiatingUserId"], message["conversationId"])
    assert writer.execute(
        "select * from participants where participant=? and conversation=?;",
        (MAIN_USER_ID, message["conversationId"]),
    ).fetchone() == (
        MAIN_USER_ID,
        message["conversationId"],
        None,
        message["createdAt"],
        None,
        int(message["initiatingUserId"]),
    )
    for user in message["participantsSnapshot"]:
        check_user(writer, user)
        assert (
            writer.execute(
                """select start_time
                    from participants where conversation=? and participant=?;""",
                (message["conversationId"], int(user)),
            ).fetchone()
            == (None,)
        )


def check_name_update(writer: TwitterDataWriter, name_update: dict):
    writer.add_message(name_update, True)
    check_conversation(writer, name_update, True)
    check_user(writer, name_update["initiatingUserId"])
    check_participant(
        writer, name_update["initiatingUserId"], name_update["conversationId"]
    )
    assert writer.execute(
        "select * from name_updates where conversation=?;",
        (name_update["conversationId"],),
    ).fetchone() == (
        name_update["createdAt"],
        int(name_update["initiatingUserId"]),
        name_update["name"],
        name_update["conversationId"],
    )


def check_conversation(writer: TwitterDataWriter, message: dict, group_dm: bool):
    if group_dm:
        other_person = None
    elif int(message["recipientId"]) == MAIN_USER_ID:
        other_person = int(message["senderId"])
    else:
        other_person = int(message["recipientId"])
    assert writer.execute(
        """select * from conversations where id=?;""",
        (message["conversationId"],),
    ).fetchone() == (
        message["conversationId"],
        "group" if group_dm else "individual",
        None,
        None,
        None,
        other_person,
        None,
        None,
        1,
        None,
        None,
        None,
    )
    check_participant(writer, MAIN_USER_ID, message["conversationId"])


def check_user(writer: TwitterDataWriter, user_id: str):
    assert writer.execute(
        "select * from users where id=?",
        (int(user_id),),
    ).fetchone() == (
        int(user_id),
        None,
        0,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )


def check_participant(writer: TwitterDataWriter, user: str, conversation: str):
    assert writer.execute(
        "select * from participants where participant=? and conversation=?;",
        (int(user), conversation),
    ).fetchone() == (
        int(user),
        conversation,
        None,
        None,
        None,
        None,
    )


def message_add_with_checks(
    writer: TwitterDataWriter, message: dict, group_dm: bool = False
):
    old_added_messages = writer.added_messages
    old_added_users = writer.added_users
    old_conversations = writer.added_conversations
    new_conversation = (
        message["conversationId"] not in writer.added_conversations_cache
    )
    new_users = 0
    if (not group_dm) and message["recipientId"] not in writer.added_users_cache:
        new_users += 1
    if message["senderId"] not in writer.added_users_cache:
        new_users += 1
    for reactor in set(x["senderId"] for x in message["reactions"]):
        if (
            reactor not in writer.added_users_cache
            and reactor != message["senderId"]
            and (group_dm or reactor != message["recipientId"])
        ):
            new_users += 1
    writer.add_message(message, group_dm)
    # check that cache was updated
    if new_conversation:
        assert writer.added_conversations == old_conversations + 1
    assert writer.added_messages == old_added_messages + 1
    assert writer.added_users == old_added_users + new_users
    assert group_dm or message["recipientId"] in writer.added_users_cache
    assert message["senderId"] in writer.added_users_cache
    assert (
        message["senderId"],
        message["conversationId"],
    ) in writer.added_participants_cache
    for reaction in message["reactions"]:
        assert (
            reaction["senderId"],
            message["conversationId"],
        ) in writer.added_participants_cache
    assert (
        group_dm
        or (
            message["recipientId"],
            message["conversationId"],
        )
        in writer.added_participants_cache
    )
    # check that conversation record was added
    check_conversation(writer, message, group_dm)
    # check that message record was added
    assert writer.execute(
        "select sent_time, id, sender, content from messages where id=?",
        (int(message["id"]),),
    ).fetchone() == (
        message["createdAt"],
        int(message["id"]),
        int(message["senderId"]),
        message["text"],
    )
    # check that text search record was added
    first_word_match = re.search(r"(^|\s)(\w+)($|\s)", message["text"])
    if first_word_match:
        first_word = first_word_match.group(0).strip()
        print("test searching for word: ", first_word)
        assert writer.execute(
            f"""select id from messages_text_search where
            messages_text_search='{first_word}' and id=?;""",
            (int(message["id"]),),
        ).fetchone()
    else:  # pragma: no cover
        print("no searchable words found in text")
    # check that user records were added
    check_user(writer, message["senderId"])
    if not group_dm:
        check_user(writer, message["recipientId"])
    # check that participant records were added
    check_participant(writer, message["senderId"], message["conversationId"])
    if not group_dm:
        check_participant(writer, message["recipientId"], message["conversationId"])
