from sqlite3 import Connection
from pathlib import Path
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPClientError
from tornado.ioloop import IOLoop
import json
import asyncio
import JSONStream
from collections import deque


# simple api client that requests user data. call queue_twitter_user_request
# synchronously with an id and then await the future it returns to get data for that
# id; call flush_queue before your program ends to ensure that your
# queue_twitter_user_request calls will in fact complete.
class SimpleTwitterAPIClient:
    def __init__(self, keyfile):
        self.http_client = AsyncHTTPClient()

        with open(keyfile) as keys:
            self.twitter_api_keys = json.load(keys)

        # list of user ids (max 100)
        self.queued_users = []

        # maps user ids to futures whose results will be set to an object
        # representing the user or None if no data is available
        self.found_users = {}

        # contains coroutine objects corresponding to http requests, only the first
        # 10 of which are live (being awaited) at a time; all the rest are awaiting
        # the one in front of them before they start
        self.queued_http_requests = deque()

    # used to send http requests that will be queued to avoid timeouts due to traffic
    # jams.
    async def queue_http_request(self, url_or_req):
        coroutine_object = self.http_client.fetch(url_or_req)
        self.queued_http_requests.append(coroutine_object)
        if len(self.queued_http_requests) > 10:
            await self.queued_http_requests[-2]
        resp = await coroutine_object
        self.queued_http_requests.popleft()
        return resp

    async def users_api_request(self, users):
        users_string = ",".join(str(x) for x in users)
        url = f"https://api.twitter.com/1.1/users/lookup.json?user_id={users_string}"
        req = HTTPRequest(
            url,
            "GET",
            {"Authorization": f"Bearer {self.twitter_api_keys['bearer_token']}"},
        )
        try:
            resp = await self.queue_http_request(req)
            user_data = json.loads(str(resp.body, encoding="utf-8"))
            print(f"retrieved data for {len(user_data)} twitter accounts")
            for user in user_data:
                try:
                    print(f"saving avatar for user @{user['screen_name']}")
                    user["avatar_bytes"] = (
                        await self.queue_http_request(
                            user["profile_image_url_https"]
                        )
                    ).body
                except HTTPClientError as e:
                    print(repr(e))
                    print(
                        "warning: could not retrieve avatar from "
                        + f'{user["profile_image_url_https"]} for {user["id"]}'
                    )
                    user["avatar_bytes"] = bytes()
                self.found_users[user["id_str"]].set_result(user)
            for user in users:
                if not self.found_users[user].done():
                    self.found_users[user].set_result(None)
        except HTTPClientError as e:
            print(repr(e))
            print(f"warning: not able to retrieve user data for any ids in {users}")

    # synchronously flushes the queue
    def flush_queue(self):
        for i in range(0, len(self.queued_users), 100):
            users = self.queued_users[i : i + 100]
            self.queued_users = self.queued_users[i:]
            asyncio.create_task(self.users_api_request(users))

    # adds given user id to the queue, flushes the queue if there are 100 users in
    # it, returns a future that will resolve to the result of the user id request
    # (either a twitter api formatted dict or None if no data is available) after the
    # queue is flushed
    def queue_twitter_user_request(self, user):
        self.queued_users.append(user)
        self.found_users[user] = asyncio.get_event_loop().create_future()
        if len(self.queued_users) == 100:
            self.flush_queue()
        return self.found_users[user]


# this class is intended to be used once to create and populate the database in one clean sweep; it has
# limited protections against adding duplicate records and the like.
class TwitterDataWriter(Connection):
    def __init__(self, account_name, account_id):
        filename = account_name + ".db"
        if Path(filename).exists():
            if (
                input(
                    "database for this account name already exists. overwrite? (y/n) "
                ).lower()
                == "y"
            ):
                if (prev_db := Path(filename)).exists():
                    prev_db.unlink()
                if (prev_journal := Path(filename + "-journal")).exists():
                    prev_journal.unlink()
            else:
                raise RuntimeError(f"Database for {account_name} already exists")
        super(TwitterDataWriter, self).__init__(filename)
        self.account = account_name

        self.isolation_level = None

        with open("setup.sql") as setup:
            self.executescript(setup.read())
        self.commit()

        self.execute("begin")

        self.execute("insert into me (id) values (?);", (account_id,))
        self.account_id = account_id

        # keep track of some records that we've just added so we don't have to check
        # if they're there in the database every time a message references them
        self.added_users_cache = set()
        self.added_conversations_cache = set()
        # contains tuples of the form (user_id, conversation_id)
        self.added_particpants_cache = set()

        self.api_client = SimpleTwitterAPIClient("api_keys.json")
        # holds task objects that represent retrieving asynchronously user info from
        # the twitter api
        self.queued_tasks = []

        self.added_messages = 0

    @property
    def added_conversations(self):
        return len(self.added_conversations_cache)

    @property
    def added_users(self):
        return len(self.added_users_cache)

    # asynchronously look up users' data by their ids, add said data to the db
    async def save_user_data(self, user_future):
        user = await user_future
        if user:
            self.execute(
                """update users 
                    set loaded_full_data=1, handle=?, display_name=?, bio=?, 
                    avatar=? where id=?;""",
                (
                    user["screen_name"],
                    user["name"],
                    user["description"],
                    user["avatar_bytes"],
                    user["id"],
                ),
            )

    def get_user_data(self, user_id):
        f = self.api_client.queue_twitter_user_request(user_id)
        self.queued_tasks.append(asyncio.create_task(self.save_user_data(f)))

    def add_user_if_necessary(self, user_id):
        if user_id not in self.added_users_cache:
            if not self.execute(
                "select 1 from users where id=?;", (user_id,)
            ).fetchone():
                self.execute(
                    "insert into users (id, loaded_full_data) values(?, 0);",
                    (user_id,),
                )
                self.get_user_data(user_id)
                self.added_users_cache.add(user_id)

    def add_participant_if_necessary(
        self, user_id, conversation_id, start_time=None, added_by=None
    ):
        if (user_id, conversation_id) not in self.added_conversations_cache:
            self.execute(
                """insert into participants
                            (participant, conversation, start_time, added_by)
                            values (?, ?, ?, ?);""",
                (user_id, conversation_id, start_time, added_by),
            )
            self.added_conversations_cache.add((user_id, conversation_id))

    def add_message(self, message, group_dm=False):
        if message["conversationId"] not in self.added_conversations_cache:
            self.execute(
                "insert into conversations (id, type, other_person) values (?, ?, ?);",
                (
                    message["conversationId"],
                    "group" if group_dm else "individual",
                    None
                    if group_dm
                    else (
                        message["recipientId"]
                        if message["senderId"] == str(self.account_id)
                        else message["senderId"]
                    ),
                ),
            )
            self.added_conversations_cache.add(message["conversationId"])

        if message["type"] == "messageCreate":
            participant_ids = [message["senderId"]] + (
                [message["recipientId"]] if not group_dm else []
            )
            for user_id in participant_ids:
                self.add_user_if_necessary(user_id)
                self.add_participant_if_necessary(user_id, message["conversationId"])

            self.execute(
                """insert into messages (id, sent_time, sender, conversation, content)
                            values (?, ?, ?, ?, ?);""",
                (
                    message["id"],
                    message["createdAt"],
                    message["senderId"],
                    message["conversationId"],
                    message["text"],
                ),
            )

            for reaction in message["reactions"]:
                self.add_user_if_necessary(reaction["senderId"])
                self.execute(
                    """insert into reactions (emotion, creation_time, creator, message)
                                values (?, ?, ?, ?);""",
                    (
                        reaction["reactionKey"],
                        reaction["createdAt"],
                        reaction["senderId"],
                        message["id"],
                    ),
                )

            for url in message["mediaUrls"]:
                url_prefixes = {
                    "image": "https://ton.twitter.com/dm/",
                    "gif": "https://video.twimg.com/dm_gif/",
                    "video": "https://video.twimg.com/dm_video/",
                }
                try:
                    type, url_comps = next(
                        (x, url[len(y) :].split("/"))
                        for x, y in url_prefixes.items()
                        if url.startswith(y)
                    )
                except StopIteration:
                    print(
                        f"Unsupported media url format {url} found in message {message}"
                    )
                    raise RuntimeError(f"unsupported url format {url}")

                if type == "image":
                    message_id, media_id, filename = url_comps
                    assert (
                        message_id == message["id"]
                    )  # honestly just out of curiosity
                elif type == "gif":
                    media_id, filename = url_comps
                elif type == "video":
                    media_id, _, _, filename = url_comps
                self.execute(
                    """insert into media (id, orig_url, filename, message, type)
                                    values (?, ?, ?, ?, ?);""",
                    (media_id, url, filename, message["id"], type),
                )

            for link in message["urls"]:
                self.execute(
                    """insert into links (orig_url, url_preview, twitter_shortened_url, message)
                                values (?, ?, ?, ?);""",
                    (link["expanded"], link["display"], link["url"], message["id"]),
                )

        elif message["type"] == "conversationNameUpdate":
            self.add_user_if_necessary(message["initiatingUserId"])
            self.execute(
                """insert into name_updates (update_time, initiator, new_name, conversation)
                            values (?, ?, ?, ?);""",
                (
                    message["createdAt"],
                    message["initiatingUserId"],
                    message["name"],
                    message["conversationId"],
                ),
            )

        elif (
            message["type"] == "participantsJoin"
            or message["type"] == "participantsLeave"
        ):
            if message["type"] == "participantsJoin":
                self.add_user_if_necessary(message["initiatingUserId"])
            for user_id in message["userIds"]:
                self.add_user_if_necessary(user_id)
                self.add_participant_if_necessary(user_id, message["conversationId"])
                if message["type"] == "participantsJoin":
                    self.execute(
                        """update participants
                                    set start_time=?, added_by=?
                                    where participant=? and conversation=?;""",
                        (
                            message["createdAt"],
                            message["initiatingUserId"],
                            user_id,
                            message["conversationId"],
                        ),
                    )
                else:
                    self.execute(
                        """update participants 
                                    set end_time=? where participant=? and conversation=?;""",
                        (message["createdAt"], user_id, message["conversationId"]),
                    )

        elif message["type"] == "joinConversation":
            self.execute(
                "update conversations set first_time=?, added_by=?, created_by_me=0 where id=?;",
                (
                    message["createdAt"],
                    message["initiatingUserId"],
                    message["conversationId"],
                ),
            )
            for user_id in message["participantsSnapshot"]:
                self.add_user_if_necessary(user_id)
                self.add_participant_if_necessary(
                    user_id,
                    message["conversationId"],
                    start_time=message["createdAt"],
                )

        self.added_messages += 1

    async def finalize(self):
        self.commit()

        print("indexing data...")
        with open("indexes.sql") as index_script:
            self.executescript(index_script.read())
        with open("cache_conversation_stats.sql") as conversation_stats_script:
            self.executescript(conversation_stats_script.read())

        self.api_client.flush_queue()
        await asyncio.gather(*self.queued_tasks)

        self.execute("pragma optimize;")

        self.commit()

        print("smallifying database size...")
        self.execute("vacuum")

        self.close()


async def writer_test():
    if (prev_db := Path("test.db")).exists():
        prev_db.unlink()
    if (prev_journal := Path("test.db-journal")).exists():
        prev_journal.unlink()
    db = TwitterDataWriter("test", 846137120209190912)
    for message in JSONStream.MessageStream("./testdata/individual_dms_test.js"):
        db.add_message(message, group_dm=False)
    for message in JSONStream.MessageStream("./testdata/group_dms_test.js"):
        db.add_message(message, group_dm=True)
    await db.finalize()


if __name__ == "__main__":
    # using asyncio.run results in tornado raising an exception :(
    IOLoop.current().run_sync(writer_test)
