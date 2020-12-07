import sqlite3
from pprint import pprint

CONVERSATIONS_PER_PAGE = 20
MESSAGES_PER_PAGE = 40

AVATAR_API_URL = "/api/avatar/"

# todo: create this
INDIVIDUAL_DM_DEFAULT_URL = "/api/assets/dm.svg"
GROUP_DM_DEFAULT_URL = "/api/assets/group.svg"


class TwitterDataReader(sqlite3.Connection):
    """Provides an interface to the database, providing an interface between the
    server that will create the API endpoints and the database."""

    def __init__(self, db_path):
        """Takes in the path to a database created by DBWrite and opens it it for
        querying.

        The sqlite3.Row class is used to allow for dictionary-like column
        value retrieval.
        """
        super(TwitterDataReader, self).__init__(db_path)
        self.row_factory = sqlite3.Row

    def user_to_spec(self, user_row: sqlite3.Row) -> dict:
        """Takes in a sqlite3.Row object fetched from the users table and returns a
        dict that can be used in the web API.

        If Twitter profile data for the user was not able to be acquired, this method
        fills it in with default values; it also places a value in the avatar_url
        field based on the api url that will retrieve it. Also, it filters out the
        internal-use columns loaded_full_data and avatar_extension from the final
        dict and makes the user's 64-bit int id a string to make it JavaScript-safe.

        Because this method does not rely on any optional fields, it can be used for
        both full-data and sidecar requests.
        """
        user = dict(user_row)
        if not user["loaded_full_data"]:
            user["display_name"] = "Mystery User"
            user["handle"] = f"{user['id']}"
            user["avatar_url"] = INDIVIDUAL_DM_DEFAULT_URL
        else:
            user[
                "avatar_url"
            ] = f"{AVATAR_API_URL}{user['id']}.{user['avatar_extension']}"
        del user["loaded_full_data"]
        del user["avatar_extension"]
        user["id"] = str(user["id"])

    def get_user_by_id(self, id: int, sidecar: bool = True) -> dict:
        """Uses an id to retrieve a user record from the database and returns a fully
        hydrated dict.

        Uses :func:`~DBRead.TwitterDataReader.user_to_spec` to hydrate the user
        objects. "Sidecar" objects are defined as those that accompany conversation
        or messages and don't contain the full data for a user; non-sidecar user
        dicts contain the bio, notes, and number_of_messages fields.
        """
        extra_cols = ", bio, notes, number_of_messages " if not sidecar else " "
        user = dict(
            self.execute(
                """select id, loaded_full_data, handle, display_name,
                    nickname, avatar_extension"""
                + extra_cols
                + "from users where id=?;",
                (id,),
            ).fetchone()
        )
        return self.user_to_spec(user)

    def conversation_to_spec(
        self, conversation_row: sqlite3.Row, other_person: dict
    ) -> dict:
        """Takes in a sqlite3.Row object fetched from the conversations table and
        returns a hydrated dict that can be used in the web API.

        The returned dict will have a "name" and "image_url" field and will have
        string versions of the 64-bit integer fields "other_person" and "added_by".

        Arguments:
            other_person: hydrated dict corresponding to the id in the conversation's
                "other_person" column, if it exists.
        """
        d = dict(conversation_row)
        if d["type"] == "individual":
            d["name"] = (
                other_person["nickname"]
                or other_person["display_name"]
                + " (@"
                + other_person["handle"]
                + ")"
            )
            d["image_url"] = other_person["avatar_url"]
        else:
            d["image_url"] = GROUP_DM_DEFAULT_URL
            last_name = self.execute(
                "select new_name from name_updates "
                "where conversation=? "
                "order by update_time desc limit 1;",
                (d["id"],),
            ).fetchone()
            if last_name:
                d["name"] = last_name[0]
            else:
                participant_rows = self.execute(
                    "select nickname, display_name, participant from participants "
                    "join users on participants.participant=users.id "
                    "order by messages_sent desc limit 11;"
                ).fetchall()
                participants = [
                    x[0] if x[0] else (x[1] if x[1] else f"@{x[2]}")
                    for x in participant_rows
                ]
                d["name"] = ", ".join(participants[0:9])
                if len(participants) == 11:
                    d["name"] += ", etc."
        d["other_person"] = str(d["other_person"])
        d["added_by"] = str(d["added_by"])
        return d

    def get_conversations(
        self, group: bool, individual: bool, order_by: str, page_number: int
    ) -> list[dict]:
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
        """
        result = {"results": [], "users": []}
        if group and individual:
            where = ""
        elif group:
            where = "where type='group'"
        elif individual:
            where = "where type='individual'"
        else:
            return []
        for r in self.execute(
            "select * from conversations"
            + f" {order_by} "
            + f" {where} "
            + f"limit {CONVERSATIONS_PER_PAGE} "
            f"offset {CONVERSATIONS_PER_PAGE * (page_number-1)};"
        ).fetchall():
            other_person = (
                self.get_user_by_id(r["other_person"]) if r["other_person"] else None
            )
            adder = self.get_user_by_id(r["added_by"]) if r["added_by"] else None
            conversation = self.conversation_to_spec(r, other_person)
            result["results"].append(conversation)
            result["users"] += [x for x in (other_person, adder) if x is not None]
        return result

    def get_conversations_by_time(
        self,
        page_number: int,
        asc: bool = True,
        group: bool = True,
        individual: bool = True,
    ) -> list[dict]:
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
    ) -> list[dict]:
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


if __name__ == "__main__":
    source = TwitterDataReader("test.db")
    pprint(source.get_conversations_by_time(1))
    pprint(source.get_conversations_by_message_count(1))
