import sqlite3
from pathlib import Path
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPClientError
from tornado.ioloop import IOLoop
import json
import asyncio
import JSONStream


# this class is intended to be used once to create and populate the database in one clean sweep; it has
# limited protections against adding duplicate records and the like.
class TwitterDataWriter(sqlite3.Connection):
    def __init__(self, account_name):
        filename = account_name+".db"
        if Path(filename).exists():
            raise RuntimeError("database for this account already exists")
        super(TwitterDataWriter, self).__init__(account_name+".db")
        self.account = account_name
        with open("setup.sql") as setup:
            self.executescript(setup.read())
        self.commit()

        # keep track of some records that we've just added so we don't have to check if they're there in the
        # database every time a message references them
        self.added_users_cache = set()
        self.added_conversations_cache = set()
        # contains tuples of the form (user_id, conversation_id)
        self.added_particpants_cache = set()

        self.http_client = AsyncHTTPClient()
        with open("api_keys.json") as keys:
            self.twitter_api_keys = json.load(keys)
        self.queued_users = []
        self.queued_requests = []

    # asynchronously look up users' data by their ids, add said data to the db
    async def send_twitter_user_request(self, users):
        url = "https://api.twitter.com/1.1/users/lookup.json?user_id=" + \
            ",".join(str(x) for x in users)
        req = HTTPRequest(
            url, "GET", {"Authorization": "Bearer "+self.twitter_api_keys["bearer_token"]})
        try:
            resp = await self.http_client.fetch(req)
            user_data = json.loads(str(resp.body, encoding="utf-8"))
            for user in user_data:
                try:
                    avatar = (await self.http_client.fetch(user["profile_image_url_https"])).body
                except HTTPClientError as e:
                    print(repr(e))
                    print("warning: could not retrieve avatar from " +
                          user["profile_image_url_https"] + " for "+user["id"])
                    avatar = bytes()
                self.execute("""update users 
                    set loaded_full_data=1, handle=?, display_name=?, bio=?, avatar=? where id=?;""",
                             (user["screen_name"], user["name"], user["description"], avatar, user["id"]))
        except HTTPClientError as e:
            print(repr(e))
            print("warning: no active users retrieved for "+str(users))

    # store user ids until 50 accumulate; then, schedule a task that will request the data for those ids and
    # add it to the database, then store the task in self.queued_requests so it can be awaited to ensure it
    # finishes before program exit. call with last_call=True to force it to act on all available user ids
    # without waiting for the 50th
    def queue_twitter_user_request(self, user, last_call=False):
        if user:  # user may be None if this is a last_call
            self.queued_users.append(user)
        if len(self.queued_users) >= 50 or (last_call and len(self.queued_users) > 0):
            self.queued_requests.append(
                asyncio.create_task(
                    self.send_twitter_user_request(self.queued_users))
            )
            self.queued_users = []

    def add_user_if_necessary(self, user_id):
        if user_id not in self.added_users_cache:
            if not self.execute("select 1 from users where id=?;", (user_id,)).fetchone():
                self.execute(
                    "insert into users (id, loaded_full_data) values(?, 0);", (user_id, ))
                self.queue_twitter_user_request(user_id)
                self.added_users_cache.add(user_id)

    def add_message(self, message, group_dm=False):
        if message["conversationId"] not in self.added_conversations_cache:
            self.execute("insert into conversations (id, type) values (?, ?);",
                         (message["conversationId"], "group" if group_dm else "individual"))
            self.added_conversations_cache.add(message["conversationId"])

        if message["type"] == "messageCreate":
            self.add_user_if_necessary(message["senderId"])
            if not group_dm:
                self.add_user_if_necessary(message["recipientId"])

            self.execute("""insert into messages (id, sent_time, sender, conversation, content)
                            values (?, ?, ?, ?, ?);""",
                         (message["id"], message["createdAt"], message["senderId"],
                          message["conversationId"], message["text"]))

            for reaction in message["reactions"]:
                self.add_user_if_necessary(reaction["senderId"])
                self.execute("""insert into reactions (emotion, creation_time, creator, message)
                                values (?, ?, ?, ?);""", (reaction["reactionKey"],
                                                          reaction["createdAt"], reaction["senderId"], message["id"]))

            for url in message["mediaUrls"]:
                if not url.startswith("https://ton.twitter.com/dm/"):
                    raise RuntimeError("Unsupported media url format: "+url)
                else:
                    message_id, attachment_id, filename = tuple(
                        url[27:].split("/"))
                    self.execute("""insert into media (id, orig_url, filename, message)
                                    values (?, ?, ?, ?);""", (attachment_id, url, filename, message_id))

            for link in message["urls"]:
                self.execute("""insert into links (orig_url, url_preview, twitter_shortened_url, message)
                                values (?, ?, ?, ?);""",
                             (link["expanded"], link["display"], link["url"], message["id"]))

        elif message["type"] == "conversationNameUpdate":
            self.add_user_if_necessary(message["initiatingUserId"])
            self.execute("""insert into name_updates (update_time, initiator, new_name, conversation)
                            values (?, ?, ?, ?);""", (message["createdAt"], message["initiatingUserId"],
                                                      message["name"], message["conversationId"]))

    async def finalize(self):
        # todo: update self-created conversation start times and hence null participant start times
        self.queue_twitter_user_request(None, last_call=True)
        await asyncio.gather(*self.queued_requests)
        self.execute("PRAGMA optimize;")
        self.commit()
        self.execute("VACUUM")
        self.added_users_cache = set()
        self.added_conversations_cache = set()


async def writer_test():
    if (prev_db := Path("test.db")).exists():
        prev_db.unlink()
    if (prev_journal := Path("test.db-journal")).exists():
        prev_journal.unlink()
    db = TwitterDataWriter("test")
    for message in JSONStream.message_stream("./testdata/individual_dms_test.js"):
        db.add_message(message, group_dm=False)
    for message in JSONStream.message_stream("./testdata/group_dms_test.js"):
        db.add_message(message, group_dm=True)
    await db.finalize()


if __name__ == "__main__":
    # using asyncio.run results in tornado raising an exception :(
    IOLoop.current().run_sync(writer_test)
