import sqlite3
from pathlib import Path


class TwitterDataWriter(sqlite3.Connection):
    def __init__(self, account_name):
        filename = account_name+".db"
        if Path(filename).exists():
            raise RuntimeError("database for this account already exists")
        super(TwitterDataWriter, self).__init__(account_name+".db")
        self.account = account_name
        with open("setup.sql") as setup:
            self.executescript(setup.read())
        # keep track of some records that we've just added so we don't have to check if they're there in the
        # database every time a message references them
        self.added_users_cache = set()
        self.added_conversations_cache = set()
        self.commit()

    def add_message(self, message, group_dm=False):
        pass

    def commit(self):
        # todo: update self-created conversation start times and hence null participant start times
        self.execute("VACUUM")
        super(TwitterDataWriter, self).commit()
        self.added_users_cache = set()
        self.added_conversations_cache = set()
