"""these tests sequentially add messages to a test database and check that the
corresponding records were added"""

from ArchiveAccess.DBWrite import TwitterDataWriter
from pytest import fixture
from collections import deque
from typing import Final
import re

MAIN_USER_ID: Final = 3330610905


@fixture(scope="module")
def writer() -> TwitterDataWriter:
    return TwitterDataWriter("test", 3330610905, automatic_overwrite=True)


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
        )
    )


def test_db_initial_state(writer: TwitterDataWriter):
    assert writer.account == "test"
    assert writer.account_id == 3330610905
    assert writer.execute("select * from me;").fetchone()[0] == 3330610905


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

    # check media; check if group conversation records are created correctly; check
    # if participant records are updated with join and leave events; check if name
    # update records are created. >:(


def message_add_with_checks(
    writer: TwitterDataWriter, message: dict, group_dm: bool = False
):
    old_added_messages = writer.added_messages
    old_added_users = writer.added_users
    new_users = 0
    if (not group_dm) and message["recipientId"] not in writer.added_users_cache:
        new_users += 1
    if message["senderId"] not in writer.added_users_cache:
        new_users += 1
    writer.add_message(message, group_dm)
    # check that cache was updated
    assert writer.added_messages == old_added_messages + 1
    assert writer.added_users == old_added_users + new_users
    assert (not group_dm) or message["recipientId"] in writer.added_users_cache
    assert message["senderId"] in writer.added_users_cache
    assert (
        message["senderId"],
        message["conversationId"],
    ) in writer.added_participants_cache
    assert (not group_dm) or (
        message["recipientId"],
        message["conversationId"],
    ) in writer.added_participants_cache
    # check that conversation record was added
    other_person = (
        None
        if group_dm
        else (
            set((int(message["recipientId"]), int(message["senderId"])))
            - set((MAIN_USER_ID,))
        ).pop()
    )
    assert writer.execute(
        """select * from conversations where id=?;""",
        (message["conversationId"],),
    ).fetchone() == (
        message["conversationId"],
        "individual",
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
            f"""select rowid from messages_text_search where
            messages_text_search='{first_word}' and rowid=?;""",
            (int(message["id"]),),
        ).fetchone()
    else:
        print("no searchable words found in text")
    # check that user records were added
    assert writer.execute(
        "select * from users where id=?",
        (int(message["senderId"]),),
    ).fetchone() == (
        int(message["senderId"]),
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
    if not group_dm:
        assert writer.execute(
            "select * from users where id=?",
            (
                int(
                    message["recipientId"],
                ),
            ),
        ).fetchone() == (
            int(message["recipientId"]),
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
    # check that participant records were added
    assert writer.execute(
        "select * from participants where participant=? and conversation=?;",
        (message["senderId"], message["conversationId"]),
    ).fetchone() == (
        int(message["senderId"]),
        message["conversationId"],
        None,
        None,
        None,
        None,
    )
    if not group_dm:
        assert writer.execute(
            "select * from participants where participant=? and conversation=?;",
            (message["recipientId"], message["conversationId"]),
        ).fetchone() == (
            int(message["recipientId"]),
            message["conversationId"],
            None,
            None,
            None,
            None,
        )
