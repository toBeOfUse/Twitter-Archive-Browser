import sqlite3

CONVERSATIONS_PER_PAGE = 20
MESSAGES_PER_PAGE = 50


class TwitterDataReader(sqlite3.Connection):
    def __init__(self, db_filename):
        super(TwitterDataReader, self).__init__(db_filename)
        self.row_factory = sqlite3.Row

    def conversation_to_dict(self, c):
        d = dict(c)
        cur = self.cursor()
        if d["type"] == "individual":
            d["name"] = (
                d["other_persons_nickname"]
                or d["other_persons_name"]
                or f"mystery user @{d['other_person']}"
            )
            d["image"] = f"/api/avatars/{d['other_person']}"
        else:
            # todo: set image
            last_name = cur.execute(
                "select new_name from name_updates "
                "order by update_time desc limit 1;"
            ).fetchone()
            if last_name:
                d["name"] = last_name[0]
            else:
                participant_rows = cur.execute(
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

    base_conversation_select = """
                    select conversations.*, display_name as other_persons_name,
                    nickname as other_persons_nickname from conversations
                    left join users on conversations.other_person=users.id """

    def get_conversations_by_time(self, page_number, asc=True):
        return [
            self.conversation_to_dict(x)
            for x in (
                self.execute(
                    self.base_conversation_select
                    + f"order by {'first_time asc' if asc else 'last_time desc'} "
                    f"limit {CONVERSATIONS_PER_PAGE} "
                    f"offset {CONVERSATIONS_PER_PAGE * page_number};"
                ).fetchall()
            )
        ]

    def get_conversations_by_message_count(
        self, page_number, group=False, asc=False
    ):
        sort = "number_of_messages asc" if asc else "number_of_messages desc"
        return [
            self.conversation_to_dict(x)
            for x in (
                self.execute(
                    self.base_conversation_select
                    + f"where type='{'group' if group else 'individual'}' "
                    f"order by {sort} "
                    f"limit {CONVERSATIONS_PER_PAGE} "
                    f"offset {CONVERSATIONS_PER_PAGE*page_number};"
                ).fetchall()
            )
        ]
