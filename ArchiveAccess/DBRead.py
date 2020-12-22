from __future__ import annotations

import sqlite3
from pprint import pprint
from typing import Union, Final, ClassVar
from collections.abc import Iterable, Callable
from collections import namedtuple
from dataclasses import dataclass, asdict
from os import PathLike
from contextlib import contextmanager

CONVERSATIONS_PER_PAGE: Final = 20
CONVERSATION_NAMES_PER_PAGE: Final = 50
MESSAGES_PER_PAGE: Final = 40

AVATAR_API_URL: Final = "/api/avatar/"
MEDIA_API_URL: Final = "/api/media/"

# todo: create these assets
INDIVIDUAL_DM_DEFAULT_URL: Final = "/api/assets/dm.svg"
GROUP_DM_DEFAULT_URL: Final = "/api/assets/group.svg"
USER_AVATAR_DEFAULT_URL: Final = "/api/assets/mysteryuser.svg"


@contextmanager
def set_row_mode(connection: sqlite3.Connection, row_factory: Callable) -> None:
    """Simple context manager to make a sqlite3 Connection temporarily return rows
    processed in a specific way and then switch back to using the row factory that it
    was previously using.

    Can be used just like this:

    >>> with set_row_mode(my_connection, UserRow):
    ...     return my_cursor.execute("select * from users;").fetchall()
    """
    prev_row_factory = connection.row_factory
    connection.row_factory = row_factory
    yield
    connection.row_factory = prev_row_factory


@dataclass(frozen=True)
class DBRow:

    db_select = "select 1"

    def serialize(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple):
        raise NotImplementedError


@dataclass(frozen=True)
class ArchivedUserSummary(DBRow):
    """Dataclass that stores some user data in a form friendly to the API, stores the
    select statement that will retrieve the data to construct this kind of object,
    and contains a factory method that can be called as a sqlite3 row factory
    function to construct an object of this type."""

    _source_fields: ClassVar = (
        "id",
        "nickname",
        "handle",
        "display_name",
        "avatar_extension",
        "loaded_full_data",
    )
    db_select: ClassVar = f"select {', '.join(_source_fields)} from users"

    id: str
    nickname: str
    handle: str
    display_name: str
    avatar_url: str

    @staticmethod
    def _get_formatted_tuple(row: tuple):
        return (
            str(row[0]),
            row[1] or "",
            row[2] if row[5] else str(row[0]),
            row[3] if row[-1] else "Mystery User",
            f"{AVATAR_API_URL}{row[0]}.{row[4]}"
            if row[5]
            else INDIVIDUAL_DM_DEFAULT_URL,
        )

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple) -> ArchivedUserSummary:
        """Converts a row fetched from the users table to an ArchivedUserSummary
        object that can be used in the web API.

        If Twitter profile data for the user was not able to be acquired, this method
        fills it in with default values; it also places a value in the avatar_url
        field based on the api url that will retrieve it. Also, it makes the user's
        64-bit int id a string to make it JavaScript-safe.
        """
        assert tuple(x[0] for x in cursor.description) == cls._source_fields
        return cls(*cls._get_formatted_tuple(row))


@dataclass(frozen=True)
class ArchivedUser(ArchivedUserSummary):
    _source_fields: ClassVar = ArchivedUserSummary._source_fields + (
        "number_of_messages",
        "bio",
        "notes",
    )
    # todo: figure out whether this actually needs to be re-declared in this subclass
    db_select: ClassVar = f"select {', '.join(_source_fields)} from users"

    number_of_messages: int
    bio: str
    notes: str

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple) -> ArchivedUser:
        assert tuple(x[0] for x in cursor.description) == cls._source_fields
        return cls(
            *(
                ArchivedUserSummary._get_formatted_tuple(row)
                + (row[6], row[7] or "", row[8] or "")
            )
        )


@dataclass(frozen=True)
class Conversation(DBRow):

    db_select: ClassVar = """select id, type, notes, number_of_messages,
    messages_from_you, first_time, last_time, num_participants, num_name_updates,
    created_by_me, other_person, added_by from conversations"""

    # todo: deal with non-passthrough values in a post_init stage?

    # pass-through values that are the same in the db and this class:
    id: str
    type: str
    notes: str
    number_of_messages: int
    messages_from_you: int
    first_time: str
    last_time: str
    num_participants: int
    num_name_updates: int
    # derived values:
    created_by_me: bool
    other_person: ArchivedUserSummary
    added_by: ArchivedUserSummary
    name: str
    image_url: str

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple) -> Conversation:

        pass_through_values = row[0:9]
        created_by_me = bool(row[9])

        with set_row_mode(cursor.connection, ArchivedUserSummary.from_row):
            other_person = (
                cursor.connection.get_users_by_id([row[10]])[0] if row[10] else {}
            )
            added_by = (
                cursor.connection.get_users_by_id([row[11]])[0] if row[11] else {}
            )

        if row[1] == "individual":
            name = (
                other_person.nickname
                or other_person.display_name + " (@" + other_person.handle + ")"
            )
            image_url = other_person.avatar_url
        else:
            image_url = GROUP_DM_DEFAULT_URL
            with set_row_mode(cursor.connection, None):
                last_name = cursor.connection.execute(
                    "select new_name from name_updates "
                    "where conversation=? "
                    "order by update_time desc limit 1;",
                    (row[0],),
                ).fetchone()
            if last_name:
                name = last_name[0]
            else:
                # todo: probably want this call as a method in the TwitterDataReader
                # connection class
                with set_row_mode(cursor.connection, None):
                    participant_rows = cursor.connection.execute(
                        "select nickname, display_name, participant from participants "
                        "join users on participants.participant=users.id "
                        "order by messages_sent desc limit 11;"
                    ).fetchall()
                participants = [
                    x[0] if x[0] else (x[1] if x[1] else f"@{x[2]}")
                    for x in participant_rows
                ]
                name = ", ".join(participants[0:9])
                if len(participants) == 11:
                    name += ", etc."
        return cls(
            *pass_through_values,
            created_by_me,
            other_person,
            added_by,
            name,
            image_url,
        )


@dataclass(frozen=True)
class Reaction(DBRow):
    db_select: ClassVar = "select emotion, creation_time, creator from reactions"

    emotion: str
    creation_time: str
    creator: str

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple):
        return cls(row[0], row[1], str(row[2]))


@dataclass(frozen=True)
class Media(DBRow):
    db_select: ClassVar = "select id, type, message, filename from media"

    id: str
    type: str
    filename: str

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple):
        return cls(row[0], row[1], f"{row[2]}-{row[3]}")


@dataclass(frozen=True)
class MessageLike(DBRow):
    @property
    def sort_by_timestamp(self):
        raise NotImplementedError


@dataclass(frozen=True)
class Message(MessageLike):
    db_select: ClassVar = (
        """select sent_time, conversation, content, sender, id from messages"""
    )

    sent_time: str
    conversation: str
    content: str
    sender: str
    id: str
    reactions: list[Reaction]
    media_urls: list[Media]
    html_content: str

    @property
    def sort_by_timestamp(self) -> str:
        return self.sent_time

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple):
        with set_row_mode(cursor.connection, Reaction.from_row):
            reactions = cursor.connection.execute(
                Reaction.db_select + "where message=?;", [row[4]]
            ).fetchall()

        with set_row_mode(cursor.connection, Media.from_row):
            media = cursor.connection.execute(
                Media.db_select + "where message=?;", [row[4]]
            ).fetchall()

        with set_row_mode(cursor.connection, sqlite3.Row):
            link_rows = cursor.connection.execute(
                """select orig_url, url_preview, twitter_shortened_url
                    from links where message=?""",
                (message_row["id"],),
            ).fetchall()
            html_content = message_row["content"]
            for link in link_rows:
                if link["orig_url"].startswith(
                    "https://twitter.com/messages/media/"
                ) and link["url_preview"].startwith("pic.twitter.com/"):
                    html_content.replace(link["twitter_shortened_url"], "")
                else:
                    html_content.replace(
                        link["twitter_shortened_url"],
                        f'<a href="{link["orig_url"]}">{link["url_preview"]}</a>',
                    )
        return cls(
            *row[0:3],
            str(row[3]),
            str(row[4]),
            reactions,
            media,
            html_content.strip(),
        )


class TwitterDataReader(sqlite3.Connection):
    """Provides an interface between the server that will create the API endpoints
    and the database."""

    def __init__(self, db_path: PathLike):
        """Takes in the path to a database created by DBWrite and opens it it for
        querying.

        The sqlite3.Row class is used to allow for dictionary-like column
        value retrieval.
        """
        super(TwitterDataReader, self).__init__(db_path)
        self.row_factory = sqlite3.Row

    def get_users_by_id(
        self, user_ids: Iterable[int], sidecar: bool = True
    ) -> list[Union[ArchivedUserSummary, ArchivedUser]]:
        """Uses ids to retrieve user records from the database.

        "Sidecar" objects are defined as those that accompany conversation
        or messages and don't contain the full data for a user; non-sidecar user
        dicts contain the bio, notes, and number_of_messages fields.
        """
        user_class = ArchivedUserSummary if sidecar else ArchivedUser

        with set_row_mode(self, user_class.from_row):
            return self.execute(
                user_class.db_select
                + f" where id in ({', '.join(['?' for _ in range(len(user_ids))])});",
                user_ids,
            ).fetchall()

    def get_conversations(
        self,
        group: bool,
        individual: bool,
        order_by: str,
        page_number: int = 1,
        where: str = "",
        placeholders: Iterable = [],
    ) -> list[Conversation]:
        """Generalized conversation record retrieval method.

        Arguments:
            group: boolean indicating whether to retrieve records for group
                conversations.
            individual: boolean indicating whether to retrieve records for individual
                conversations.
            order_by: order by clause in sql indicating how to sort the results.
                examples: "order by first_time asc", "order by number_of_messages desc"
            page_number: indicates what page we are on. page numbers start at 1;
                pages contain `CONVERSATIONS_PER_PAGE` conversations.
            where: optional string containing sql statements that will be
                added to the default where conditions with an "and".
            placeholders: optional iterable containing values corresponding to any ?s
                in the previous two sql strings
        """
        if group and individual:
            type_clause = "where 1=1"
        elif group:
            type_clause = "where type='group'"
        elif individual:
            type_clause = "where type='individual'"
        else:
            return []
        where_clause = type_clause + " and (" + where + ")" if where else type_clause
        placeholders = list(placeholders) + [
            CONVERSATIONS_PER_PAGE,
            CONVERSATIONS_PER_PAGE * (page_number - 1),
        ]
        with set_row_mode(self, Conversation.from_row):
            return self.execute(
                Conversation.db_select + f" {where_clause} "
                f" {order_by} "
                f"limit ? "
                f"offset ?;",
                placeholders,
            ).fetchall()

    def get_conversations_by_time(
        self,
        page_number: int,
        asc: bool = True,
        group: bool = True,
        individual: bool = True,
    ) -> list[ConversationRow]:
        """Retrieves `CONVERSATIONS_PER_PAGE` conversations ordered by when their most
        or least recent messages were sent. Most of the arguments are passed on to
        :func:`~DBRead.TwitterDataReader.get_conversations`, except for:

        Arguments:
            asc: If this boolean is True, conversations are sorted based on their
                oldest message, with the oldest first; if it's False, conversations are
                sorted by their newest message, with the newest first.

        """
        order_by = f"order by {'first_time asc' if asc else 'last_time desc'}"
        return self.get_conversations(group, individual, order_by, page_number)

    def get_conversations_by_message_count(
        self,
        page_number: int,
        group: bool = True,
        individual: bool = True,
        by_me: bool = False,
    ) -> list[ConversationRow]:
        """Retrieves `CONVERSATIONS_PER_PAGE` conversations ordered by how many
        messages were sent in them or by how many messages were sent in them by you.
        Most of the arguments are passed on to
        :func:`~DBRead.TwitterDataReader.get_conversations`, except for:

        Arguments:
            by_me: if this is true, then conversations with the most messages sent by
                you are presented first; if it's false, the conversations with the most
                messages period are presented first.
        """
        order_by = (
            f"order by {'number_of_messages' if by_me else 'messages_from_you'} desc"
        )
        return self.get_conversations(group, individual, order_by, page_number)

    def get_conversations_by_user(
        self, user_id: Union[str, int], page_number: int
    ) -> list[ConversationRow]:

        order_by = """"order by
                (select messages_sent from participants
                where conversation=conversations.id)
                desc"""
        exists_clause = f"""exists(
                select 1 from participants
                where participant=? and conversation=conversations.id
            )"""
        return self.get_conversations(
            True, True, order_by, page_number, exists_clause, (user_id,)
        )

    def get_conversation_by_id(self, conversation_id: str) -> ConversationRow:
        """Retrieves the record for a specific conversation with a specific id."""
        c = self.get_conversations(True, True, "", 1, "id=?", [conversation_id])[0]
        return c

    def get_conversation_names(
        self, conversation_id: str, oldest_first=True, page_number: int = 1
    ) -> dict[str, list[dict]]:
        """Gets the records for CONVERSATION_NAMES_PER_PAGE names that a conversation
        has had."""
        names = [
            dict(x, initiator=str(x["initiator"]))
            for x in self.execute(
                f"""select * from name_updates
                where conversation=?
                order by update_time {'asc' if oldest_first else 'desc'}
                limit ? offset ?;""",
                (
                    conversation_id,
                    CONVERSATION_NAMES_PER_PAGE,
                    CONVERSATION_NAMES_PER_PAGE * (page_number - 1),
                ),
            )
        ]
        users = self.get_users_by_id([x["initiator"] for x in names])
        return {"results": names, "users": users}

    def set_conversation_notes(self, conversation_id: str, notes: str) -> None:
        """Updates a conversation's notes field. hooray"""
        self.execute(
            "update conversations set notes=? where id=?;", (conversation_id, notes)
        )

    def get_messages(self, where: str, placeholders: Iterable):
        with set_row_mode(self, Message.from_row):
            message_rows = self.execute(
                f"""{Message.db_select}
                    where {where}
                    order by sent_time asc
                    limit {MESSAGES_PER_PAGE};"""
            ).fetchall()
        users = self.get_users_by_id([m["sender"] for m in message_rows])
        return {"results": messages, "users": users}

    def get_messages_by_conversation(
        self, conversation_id: str, after: str = "", before: str = "", at: str = ""
    ):
        pass

    def search_messages(self, where: str, placeholders: Iterable, query: str):
        pass

    def get_user_avatar(self, id: Union[int, str]) -> bytes:
        """Retrieves user avatar image file as bytes."""
        return self.execute(
            "select avatar from users where id=?;", (id,)
        ).fetchone()[0]


if __name__ == "__main__":
    source = TwitterDataReader("./db/test.db")
    pprint(source.get_conversations_by_time(1))
    pprint(source.get_conversations_by_message_count(1))
