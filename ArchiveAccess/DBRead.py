from __future__ import annotations

import sqlite3
from pprint import pprint
from typing import Union, Final, ClassVar
from collections.abc import Iterable, Callable
from collections import defaultdict
from dataclasses import dataclass, asdict
from os import PathLike
from contextlib import contextmanager
from copy import deepcopy
import string
from pathlib import Path
from cv2 import (
    imread as open_image,
    VideoCapture as Video,
    IMREAD_COLOR as color_image,
    CAP_PROP_FRAME_HEIGHT as video_height,
    CAP_PROP_FRAME_WIDTH as video_width,
)

CONVERSATIONS_PER_PAGE: Final = 20
CONVERSATION_NAMES_PER_PAGE: Final = 50
MESSAGES_PER_PAGE: Final = 40
USERS_PER_PAGE: Final = 20

AVATAR_API_URL: Final = "/api/avatar/"
MEDIA_API_URL: Final = "/api/media/"

GROUP_DM_DEFAULT_URL: Final = "/assets/svg/group.svg"
USER_AVATAR_DEFAULT_URL: Final = "/assets/svg/mysteryuser.svg"

DEFAULT_DISPLAY_NAME: Final = "Mystery User"


@contextmanager
def set_row_mode(connection: sqlite3.Connection, row_factory: Callable) -> None:
    """Simple context manager to make a sqlite3 Connection temporarily return rows
    processed in a specific way and then switch back to using the row factory that it
    was previously using.

    Can be used just like this:

    >>> with set_row_mode(my_connection, UserRow.from_row):
    ...     return my_cursor.execute("select * from users;").fetchall()
    """
    prev_row_factory = connection.row_factory
    connection.row_factory = row_factory
    yield
    connection.row_factory = prev_row_factory


class WhereClause:
    """stupid-simple class for accumulating boolean expressions in sql as strings
    that concatenates them together with 'and's when formatted as a string."""

    def __init__(self):
        self.conditions = []

    def add(self, condition: str) -> None:
        if clean := condition.strip():
            self.conditions.append(clean)

    def __format__(self, params) -> str:
        if len(self.conditions):
            return "where " + " and ".join(f"({x})" for x in self.conditions)
        else:
            return ""


@dataclass(frozen=True)
class DBRow:

    """base class for dataclasses that store information taken from a database row.
    subclasses of this store some data in a form friendly to the API, store the
    select statement that will retrieve the data to construct this kind of object,
    and contain a factory method that can be called as a sqlite3 row factory function
    to construct an object of this type."""

    db_select = "select 1 from sqlite_master"

    def serialize(self) -> dict:
        return asdict(self) | {"schema": type(self).__name__}

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple):  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class ArchivedUserSummary(DBRow):
    """class that stores a limited amount of user data fetched from the database.
    intended to be used to accompany conversations or messages, not to be used as
    payloads in and of themselves."""

    _source_fields: ClassVar = (
        "id",
        "nickname",
        "handle",
        "display_name",
        "avatar_extension",
        "loaded_full_data",
        "id=(select id from me)",
    )

    db_select: ClassVar = f"select {', '.join(_source_fields)} from users"

    id: str
    nickname: str
    handle: str
    display_name: str
    avatar_url: str
    loaded_full_data: bool
    is_main_user: bool

    @staticmethod
    def _get_formatted_tuple(row: tuple):
        return (
            str(row[0]),
            row[1] or "",
            row[2] if row[5] else str(row[0]),
            row[3] if row[5] else DEFAULT_DISPLAY_NAME,
            f"{AVATAR_API_URL}{row[0]}.{row[4]}"
            if row[5]
            else USER_AVATAR_DEFAULT_URL,
            bool(row[5]),
            bool(row[6]),
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
    """subclass of ArchivedUserSummary that adds the remaining fields available in
    the database. intended to be used in payloads for database endpoints that return
    user data."""

    _source_fields: ClassVar = ArchivedUserSummary._source_fields + (
        "number_of_messages",
        "bio",
        "notes",
        "first_appearance",
        "last_appearance",
    )
    # todo: figure out whether this actually needs to be re-declared in this subclass
    db_select: ClassVar = f"select {', '.join(_source_fields)} from users"

    number_of_messages: int
    bio: str
    notes: str
    first_appearance: str
    last_appearance: str

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple) -> ArchivedUser:
        row_start = len(super()._source_fields)
        return cls(
            *(
                ArchivedUserSummary._get_formatted_tuple(row)
                + (
                    row[row_start],
                    row[row_start + 1] or "",
                    row[row_start + 2] or "",
                    *row[row_start + 3 :],
                )
            )
        )


@dataclass(frozen=True)
class ArchivedParticipant(ArchivedUserSummary):
    """Extends ArchivedUser to include information about the user's presence in a
    specific conversation. Note: the conversation's id must be specified as a
    SQL placeholder value when using the `db_select` field."""

    _source_fields: ClassVar = ArchivedUserSummary._source_fields + (
        "participants.conversation",
        "participants.messages_sent",
        "participants.start_time",
        "participants.end_time",
    )
    db_select: ClassVar = f"""select {', '.join(_source_fields)} from users 
            join participants on 
            participants.participant=users.id and
            participants.conversation=?"""

    conversation: str
    messages_in_conversation: int
    join_time: str
    leave_time: str

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple) -> ArchivedParticipant:
        row_start = len(super()._source_fields)
        return cls(
            *(ArchivedUserSummary._get_formatted_tuple(row) + row[row_start:])
        )


@dataclass(frozen=True)
class Conversation(DBRow):
    """dataclass representing a conversation record. contains ArchivedUserSummary
    objects instead of just IDs."""

    db_select: ClassVar = """select id, type, number_of_messages,
    messages_from_you, first_time, last_time, num_participants, num_name_updates,
    created_by_me, other_person, added_by, notes from conversations"""

    # todo: deal with non-passthrough values in a post_init stage?

    # pass-through values that are the same in the db and this class:
    id: str
    type: str
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
    notes: str

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple) -> Conversation:

        pass_through_values = row[0:8]
        created_by_me = bool(row[8])

        if row[9]:
            other_person = cursor.connection.get_users_by_id([row[9]])[0]
            cursor.connection.cache_user_conversation_dependency(row[9], row[0])
        else:
            other_person = None

        if row[10]:
            added_by = cursor.connection.get_users_by_id([row[10]])[0]
            cursor.connection.cache_user_conversation_dependency(row[10], 0)
        else:
            added_by = None

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
                        """select nickname, display_name, participant
                        from participants
                        join users on participants.participant=users.id
                        where conversation=?
                        order by messages_sent desc limit 6;""",
                        (row[0],),
                    ).fetchall()
                participants = []
                for x in participant_rows[0:5]:
                    participants.append(
                        x[0] if x[0] else (x[1] if x[1] else f"@{x[2]}")
                    )
                    cursor.connection.cache_user_conversation_dependency(
                        x[2], row[0]
                    )
                name = ", ".join(participants)
                if len(participant_rows) == 6:
                    name += ", etc."

        notes = row[11] or ""

        return cls(
            *pass_through_values,
            created_by_me,
            other_person,
            added_by,
            name,
            image_url,
            notes,
        )


@dataclass(frozen=True)
class MessageLike(DBRow):
    """Abstract class representing objects that can fit in the flow of a conversation
    as messages do. the following three properties must be implemented by
    subclasses in addition to the normal DBRow properties."""

    timestamp_field: ClassVar = ""
    """the field that will be used in database queries to filter rows by time"""

    @property
    def sort_by_timestamp(self) -> str:  # pragma: no cover
        """returns a string timestamp that objects of a type should be sorted by to
        integrate them into the conversation"""
        raise NotImplementedError

    @property
    def user_ids(self) -> Iterable[int]:  # pragma: no cover
        """returns a list of any user ids that are referenced in this object"""
        raise NotImplementedError

    @staticmethod
    def user_id_iterator(lists: Iterable[list[int]]) -> Iterable[int]:
        """pass in an iterator that yields iterables obtained from calling user_ids()
        on MessageLike objects, and receive a generator that will return all the
        unique ids across each list."""
        already_yielded = set()
        for x in lists:
            for y in x:
                if y not in already_yielded:
                    already_yielded.add(y)
                    yield y


@dataclass(frozen=True)
class NameUpdate(MessageLike):
    db_select: ClassVar = """select rowid, update_time, initiator, new_name, conversation
        from name_updates"""
    timestamp_field: ClassVar = "update_time"

    id: str
    update_time: str
    initiator: str
    new_name: str
    conversation: str

    @property
    def sort_by_timestamp(self) -> str:
        return self.update_time

    @property
    def user_ids(self) -> list[int]:
        return [int(self.initiator)]

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple) -> NameUpdate:
        return cls("update"+str(row[0]), *(str(x) for x in row[1:]))


@dataclass(frozen=True)
class ParticipantJoin(MessageLike):
    db_select: ClassVar = """select rowid, participant, added_by, conversation, start_time from
        participants"""
    timestamp_field: ClassVar = "start_time"

    id: str
    participant: str
    added_by: str
    conversation: str
    time: str

    @property
    def sort_by_timestamp(self) -> self:
        return self.time

    @property
    def user_ids(self) -> list[int]:
        return [int(self.participant), int(self.added_by)]

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple) -> ParticipantJoin:
        return cls(str(row[0]) + "join", *(str(x) for x in row[1:]))


@dataclass(frozen=True)
class ParticipantLeave(MessageLike):
    db_select: ClassVar = """select rowid, participant, conversation, end_time from
        participants"""
    timestamp_field: ClassVar = "end_time"

    id: str
    participant: str
    conversation: str
    time: str

    @property
    def sort_by_timestamp(self) -> self:
        return self.time

    @property
    def user_ids(self) -> list[int]:
        return [int(self.participant)]

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple) -> ParticipantJoin:
        return cls(str(row[0]) + "leave", *(str(x) for x in row[1:]))


@dataclass(frozen=True)
class Reaction(DBRow):
    db_select: ClassVar = (
        "select rowid, emotion, creation_time, creator from reactions"
    )

    id: int
    emotion: str
    creation_time: str
    creator: str

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple):
        return cls(row[0], row[1], row[2], str(row[3]))


@dataclass(frozen=True)
class Media(DBRow):
    db_select: ClassVar = "select id, type, message, filename, from_group_message, width, height from media"

    dm_media_path: ClassVar
    group_media_path: ClassVar

    id: str
    type: str
    src: str
    width: int
    height: int

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple):
        if not (row[5] and row[6]):
            file_path = str(
                (cls.group_media_path if row[4] else cls.dm_media_path)
                / (f"{row[2]}-{row[3]}")
            )
            if row[1] == "image":
                img = open_image(file_path, color_image)
                height, width, _ = img.shape
            else:
                vid = Video(file_path)
                height, width = vid.get(video_height), vid.get(video_width)
            cursor.connection.execute(
                "update media set width=?, height=? where id=?",
                (width, height, row[0]),
            )
            cursor.connection.commit()
        else:
            height, width = row[6], row[5]
        return cls(
            str(row[0]),
            row[1],
            f"{MEDIA_API_URL}{'group/' if row[4] else 'individual/'}{row[2]}-{row[3]}",
            width,
            height,
        )


@dataclass(frozen=True)
class Message(MessageLike):
    db_select_fields: ClassVar = (
        """select sent_time, conversation, content, sender, id from """
    )
    timestamp_field: ClassVar = "sent_time"

    db_select: ClassVar = db_select_fields + "messages"
    db_select_for_search: ClassVar = db_select_fields + "messages_text_search"

    sent_time: str
    conversation: str
    content: str
    sender: str
    id: str
    reactions: list[Reaction]
    media: list[Media]
    html_content: str

    @property
    def sort_by_timestamp(self) -> str:
        return self.sent_time

    @property
    def user_ids(self) -> list[int]:
        return [int(self.sender)] + [int(x.creator) for x in self.reactions]

    @classmethod
    def from_row(cls, cursor: sqlite3.Cursor, row: tuple):
        with set_row_mode(cursor.connection, Reaction.from_row):
            reactions = cursor.connection.execute(
                Reaction.db_select + " where message=? order by creation_time;",
                [row[4]],
            ).fetchall()

        with set_row_mode(cursor.connection, Media.from_row):
            media = cursor.connection.execute(
                Media.db_select + " where message=?;", [row[4]]
            ).fetchall()

        with set_row_mode(cursor.connection, sqlite3.Row):
            link_rows = cursor.connection.execute(
                """select orig_url, url_preview, twitter_shortened_url
                    from links where message=?""",
                (row[4],),
            ).fetchall()
            html_content = row[2].replace("\n", "<br />")
            for link in link_rows:
                if link["orig_url"].startswith(
                    "https://twitter.com/messages/media/"
                ) and link["url_preview"].startswith("pic.twitter.com/"):
                    html_content = html_content.replace(
                        link["twitter_shortened_url"], ""
                    )
                else:
                    html_content = html_content.replace(
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

    def __init__(
        self, db_path: PathLike, dm_media_path: Pathlike, group_media_path: Pathlike
    ):
        """Takes in the path to a database created by DBWrite and opens it for
        querying."""
        super(TwitterDataReader, self).__init__(
            db_path, uri=("mode=memory" in str(db_path))
        )
        self.row_factory = sqlite3.Row
        self.users_cache: dict[int, ArchivedUserSummary] = {}
        self.conversations_cache: dict[str, Conversation] = {}

        # this object maps user ids to the ids of any conversation that depends on
        # them through the added_by, other_person, or name fields. this is so that
        # the right items can be invalidated from the conversation cache when user
        # data is changed.
        self.user_data_in_conversations: dict[int, set[str]] = defaultdict(set)

        Media.dm_media_path = dm_media_path
        Media.group_media_path = group_media_path

    def cache_user_conversation_dependency(self, user: int, conversation: str):
        """called in the Conversation.from_row method to register the fact that the
        conversation object being instantiated depends on the data of a user; this is
        used for cache invalidation when the user's data changes"""
        self.user_data_in_conversations[user].add(conversation)

    def get_main_user(self):
        with set_row_mode(self, ArchivedUser.from_row):
            return self.execute(
                ArchivedUser.db_select + " where id=(select id from me);"
            ).fetchone()

    def get_users_by_id(
        self, user_ids: Iterable[int], sidecar: bool = True
    ) -> list[Union[ArchivedUserSummary, ArchivedUser]]:
        """Uses ids to retrieve user records from the database.

        "Sidecar" objects are defined as those that accompany messages and don't
        contain the full data for a user; they are represented by ArchivedUserSummary
        objects.
        """
        user_class = ArchivedUserSummary if sidecar else ArchivedUser

        # to make sure that it isn't an unordered type like a set, for the below
        user_ids = list(user_ids)

        users = []
        uncached_ids = []

        if sidecar:
            for user_id in user_ids:
                if user_id in self.users_cache:
                    users.append(self.users_cache[user_id])
                else:
                    uncached_ids.append(user_id)
        else:
            uncached_ids = user_ids

        with set_row_mode(self, user_class.from_row):
            uncached_users = self.execute(
                user_class.db_select
                + f" where id in ({', '.join(['?' for _ in range(len(uncached_ids))])});",
                user_ids,
            ).fetchall()
            if sidecar:
                for user in uncached_users:
                    self.users_cache[user.id] = user
            return users + uncached_users

    def get_users_by_message_count(
        self, page_number: int, conversation_id: str = None
    ):
        if conversation_id:
            with set_row_mode(self, ArchivedParticipant.from_row):
                return self.execute(
                    ArchivedParticipant.db_select
                    + " order by participants.messages_sent desc limit ? offset ?;",
                    (
                        conversation_id,
                        USERS_PER_PAGE,
                        (page_number - 1) * USERS_PER_PAGE,
                    ),
                ).fetchall()
        else:
            with set_row_mode(self, ArchivedUser.from_row):
                return self.execute(
                    ArchivedUser.db_select
                    + " order by number_of_messages desc limit ? offset ?;",
                    (USERS_PER_PAGE, (page_number - 1) * USERS_PER_PAGE),
                ).fetchall()

    def set_user_nickname(self, user_id: Union[str, int], new_nickname: str) -> list:
        self.execute(
            "update users set nickname=? where id=?;",
            (new_nickname[0:50], int(user_id)),
        )
        for conversation in self.user_data_in_conversations[int(user_id)]:
            self.conversations_cache.pop(conversation, None)
        self.users_cache.pop(int(user_id), None)
        self.commit()
        return list(self.user_data_in_conversations[int(user_id)])

    def set_user_notes(self, user_id: Union[str, int], new_notes: str) -> None:
        """this does not invalidate anything in the conversations cache because
        nothing in a conversation object uses the user's notes, currently"""
        self.execute(
            "update users set notes=? where id=?;",
            (new_notes, int(user_id)),
        )
        self.users_cache.pop(int(user_id), None)
        self.commit()

    def get_user_avatar(self, id: Union[int, str]) -> bytes:
        """Retrieves user avatar image file as bytes."""
        return self.execute(
            "select avatar, avatar_extension from users where id=?;", (id,)
        ).fetchone()

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
        type_clause = WhereClause()
        if group and individual:
            pass
        elif group:
            type_clause.add("type='group'")
        elif individual:
            type_clause.add("type='individual'")
        else:
            return []
        type_clause.add(where)
        placeholders = list(placeholders) + [
            CONVERSATIONS_PER_PAGE,
            CONVERSATIONS_PER_PAGE * (page_number - 1),
        ]
        with set_row_mode(self, Conversation.from_row):
            return self.execute(
                Conversation.db_select + f" {type_clause} "
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
    ) -> list[Conversation]:
        """Retrieves `CONVERSATIONS_PER_PAGE` conversations ordered by when their most
        or least recent messages were sent. Most of the arguments are passed on to
        `ArchiveAccess.DBRead.TwitterDataReader.get_conversations`, except for:

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
    ) -> list[Conversation]:
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
            f"order by {'messages_from_you' if by_me else 'number_of_messages'} desc"
        )
        return self.get_conversations(group, individual, order_by, page_number)

    def get_conversations_by_user(
        self, user_id: Union[str, int], page_number: int
    ) -> list[Conversation]:
        """returns the conversations that a specific user has appeared in, sorted by
        the number of messages they have sent in each conversation highest to
        lowest."""

        order_by = """order by
                (select messages_sent from participants
                where participant=? and conversation=conversations.id)
                desc"""
        where_clause = f"""id in (select conversation from participants where
                        participant=?)"""
        return self.get_conversations(
            True, True, order_by, page_number, where_clause, (user_id, user_id)
        )

    def get_conversation_by_id(self, conversation_id: str) -> Conversation:
        """Retrieves the record for a specific conversation with a specific id."""
        if conversation_id in self.conversations_cache:
            return self.conversations_cache[conversation_id]
        else:
            c = self.get_conversations(True, True, "", 1, "id=?", [conversation_id])[
                0
            ]
            self.conversations_cache[conversation_id] = c
            return c

    def get_conversations_by_id(
        self, conversation_ids: Iterable[str]
    ) -> list[Conversation]:
        # this might be slightly faster using an in clause like get_user_by_id; not
        # sure
        return [self.get_conversation_by_id(x) for x in conversation_ids]

    def get_conversation_names(
        self, conversation_id: str, oldest_first=True, page_number: int = 1
    ) -> list[NameUpdate]:
        """Gets the records for CONVERSATION_NAMES_PER_PAGE names that a conversation
        has had."""
        with set_row_mode(self, NameUpdate.from_row):
            names = self.execute(
                f"""{NameUpdate.db_select}
                where conversation=?
                order by update_time {'asc' if oldest_first else 'desc'}
                limit ? offset ?;""",
                (
                    conversation_id,
                    CONVERSATION_NAMES_PER_PAGE,
                    CONVERSATION_NAMES_PER_PAGE * (page_number - 1),
                ),
            ).fetchall()
        users = self.get_users_by_id(
            MessageLike.user_id_iterator((x.user_ids for x in names))
        )
        return {"results": names, "users": users}

    def set_conversation_notes(self, conversation_id: str, notes: str) -> None:
        """Updates a conversation's notes field. hooray"""
        self.execute(
            "update conversations set notes=? where id=?;", (notes, conversation_id)
        )
        self.conversations_cache.pop(conversation_id, None)
        self.commit()

    @staticmethod
    def parse_search(query):
        # all punctuation is meaningless to fts5 and needs to be sanitized except for
        # matched pairs of double quotes, which create phrases. to preserve these,
        # the search query is split on "s before sanitization; if there are an odd
        # number of elements after splitting, then we can join everything together on
        # " again; if there are an even number, then there was an unmatched ", which
        # we will arbitrarily decide was the last one and exclude. TODO: move tests
        # for this into main test package
        escaper = str.maketrans({x: " " for x in string.punctuation})
        search_comps = query.split('"')
        parsed_search = ""
        if len(search_comps) % 2 == 1:
            parsed_search = '"'.join(x.translate(escaper) for x in search_comps)
        else:
            parsed_search = '"'.join(
                x.translate(escaper) for x in search_comps[:-1]
            ) + search_comps[-1].translate(escaper)
        return parsed_search.replace('""', '" "')

    def traverse_messages(
        self,
        conversation="",
        user="",
        after: str = "",
        before: str = "",
        at: str = "",
        search: str = "",
    ) -> dict[str, list]:

        # these should probably be global variables somewhere. idk

        zeroes_time_string = "0000-00-00T00:00:00.000Z"
        nines_time_string = "9999-99-99T99:99:99.999Z"

        assert (
            after or before or at
        ), """time for messages must be specified (remember, you can use 'beginning'
            or 'end' for the after and before parameters, respectively)"""

        assert (bool(after) ^ bool(before)) or (
            bool(before) ^ bool(at)
        ), "traversing messages is unidirectional"

        assert (
            after == "beginning"
            or before == "end"
            or zeroes_time_string <= (after or before or at) <= nines_time_string
        )

        where = WhereClause()
        placeholders = []
        if conversation:
            where.add("conversation=?")
            placeholders.append(conversation)
        if user:
            where.add("sender=?")
            placeholders.append(int(user))

        if search:
            where.add(
                "messages_text_search MATCH '" + self.parse_search(search) + "'"
            )
            select = Message.db_select_for_search
        else:
            select = Message.db_select

        at_last_page = False
        at_first_page = False

        with set_row_mode(self, Message.from_row):
            if at:
                first_where = where
                second_where = deepcopy(where)
                first_where.add("sent_time <= ?")
                second_where.add("sent_time > ?")

                # `at` must be the last added placeholder so it can work for both
                # versions of the where clause
                placeholders.append(at)

                batch_size = int(MESSAGES_PER_PAGE / 2)

                first_batch = self.execute(
                    f"""{select}
                    {first_where}
                    order by sent_time desc
                    limit {batch_size};""",
                    placeholders,
                ).fetchall()

                if len(first_batch) < batch_size:
                    at_first_page = True

                second_batch = self.execute(
                    f"""{select}
                    {second_where}
                    order by sent_time asc
                    limit {batch_size};""",
                    placeholders,
                ).fetchall()

                if len(second_batch) < batch_size:
                    at_last_page = True

                messages = first_batch + second_batch

            else:

                if before:
                    sort = "sent_time desc"
                    if before != "end":
                        where.add("sent_time < ?")
                        placeholders.append(before)
                elif after:
                    sort = "sent_time asc"
                    if after != "beginning":
                        where.add("sent_time > ?")
                        placeholders.append(after)
                messages = self.execute(
                    f"""{select}
                        {where}
                        order by {sort}
                        limit {MESSAGES_PER_PAGE};""",
                    placeholders,
                ).fetchall()

                if len(messages) < MESSAGES_PER_PAGE:
                    if after:
                        at_last_page = True
                    elif before:
                        at_first_page = True

        if not search:  # conversation events not included in searches

            if after == "beginning" or at_first_page:
                sequence_start = zeroes_time_string
            else:
                sequence_start = after or min(x.sort_by_timestamp for x in messages)

            if before == "end" or at_last_page:
                sequence_end = nines_time_string
            else:
                sequence_end = before or max(x.sort_by_timestamp for x in messages)

            with set_row_mode(self, NameUpdate.from_row):
                name_where = WhereClause()
                name_placeholders = []
                if conversation:
                    name_where.add("conversation=?")
                    name_placeholders.append(conversation)
                if user:
                    name_where.add("initiator=?")
                    name_placeholders.append(user)
                name_where.add(f"{NameUpdate.timestamp_field} > ?")
                name_placeholders.append(sequence_start)
                name_where.add(f"{NameUpdate.timestamp_field} < ?")
                name_placeholders.append(sequence_end)
                messages += self.execute(
                    NameUpdate.db_select + f" {name_where};", name_placeholders
                )

            joining_where = WhereClause()
            joining_leaving_placeholders = []
            if conversation:
                joining_where.add("conversation=?")
                joining_leaving_placeholders.append(conversation)
            if user:
                joining_where.add("participant=?")
                joining_leaving_placeholders.append(user)
            leaving_where = deepcopy(joining_where)
            leaving_where.add("end_time > ? and end_time < ?")
            joining_where.add("start_time > ? and start_time < ?")
            joining_leaving_placeholders += [sequence_start, sequence_end]

            with set_row_mode(self, ParticipantJoin.from_row):
                messages += self.execute(
                    ParticipantJoin.db_select + f" {joining_where};",
                    joining_leaving_placeholders,
                ).fetchall()
            with set_row_mode(self, ParticipantLeave.from_row):
                messages += self.execute(
                    ParticipantLeave.db_select + f" {leaving_where};",
                    joining_leaving_placeholders,
                )

        messages.sort(key=lambda x: x.sort_by_timestamp)

        users = self.get_users_by_id(
            MessageLike.user_id_iterator((x.user_ids for x in messages))
        )
        conversations = self.get_conversations_by_id(
            set(x.conversation for x in messages)
        )

        return {"results": messages, "users": users, "conversations": conversations}

    def get_message_by_id(self, id: int) -> dict[str, list]:
        with set_row_mode(self, Message.from_row):
            message = self.execute(
                Message.db_select + " where id=?;", (id,)
            ).fetchone()
            users = self.get_users_by_id(set(message.user_ids))
            return {
                "results": [message],
                "users": users,
                "conversation": [self.get_conversation_by_id(message.conversation)],
            }

    def get_message_timestamp_by_id(self, id: int) -> str:
        result = self.execute(
            "select sent_time from messages where id=?;", (id,)
        ).fetchone()
        if result:
            return result[0]

    def get_random_messages(self) -> dict[str, list]:
        with set_row_mode(self, Message.from_row):
            messages = self.execute(
                Message.db_select
                + " where id IN (SELECT id FROM messages ORDER BY RANDOM() LIMIT ?);",
                (MESSAGES_PER_PAGE,),
            ).fetchall()
            users = self.get_users_by_id(
                MessageLike.user_id_iterator((x.user_ids for x in messages))
            )
            return {"results": messages, "users": users}

    def get_global_stats(self) -> dict:
        if not hasattr(self, "global_stats_cache"):
            with set_row_mode(self, sqlite3.Row):
                self.global_stats_cache = dict(
                    self.execute(
                        """select 
                        (select count() from conversations) as number_of_conversations,
                        (select count() from users) as number_of_users,
                        (select count() from messages) as number_of_messages,
                        (select min(first_time) from conversations) as earliest_message,
                        (select max(last_time) from conversations) as latest_message;
                    """
                    ).fetchone()
                )
        return self.global_stats_cache


if __name__ == "__main__":  # pragma: no cover
    source = TwitterDataReader("./db/test.db")
    pprint(source.get_conversations_by_time(1))
    pprint(source.get_conversations_by_message_count(1))
    pprint([x.serialize() for x in source.get_conversations_by_user(4196983835, 1)])
