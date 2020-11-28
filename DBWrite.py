from sqlite3 import Connection
from pathlib import Path
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPClientError
from tornado.ioloop import IOLoop
import json
import asyncio
import JSONStream
from collections import deque


class SimpleTwitterAPIClient:
    """simple twitter api client for requesting user data.

    this api client uses a tornado AsynHTTPClient to make http requests; it queues
    http requests so that tornado is only performing 10 at a time, which prevents
    timeout errors from requests sitting in tornado's queue too long; it queues user
    ids that it will request data for until it has 100 or the queue is manually
    flushed; it retrieves twitter users' avatar image files as bytes automatically;
    and it returns data to its owner via callback functions. sends back None if no
    data is found for a user.

    Attributes:
        http_client: instance of tornado.httpclient.AsyncHTTPClient to make HTTP
            requests with.
        twitter_api_keys: dict holding at least a 'bearer_token' field to
            authenticate api requests with.
        queued_users: list of user ids that we want data for.
        found_users: maps user ids to callbacks which will receive an object
            representing the user or None if no data is available.
        queued_http_requests: contains coroutine objects corresponding to http
            requests, only the first 10 of which are live (being awaited) at a time; all
            the rest are awaiting the one in front of them before they start.

    How to use:
        >>> stac = SimpleTwitterAPIClient("api_keys.json")
        >>> def user_dict_handler(user_dict):
        ...     print(user_dict)
        >>> stac.queue_twitter_user_request("10101010", user_dict_handler)
        >>> stac.queue_twitter_user_request("01010101", user_dict_handler)
        ...
        >>> await stac.flush_queue()
    """

    def __init__(self, keyfile):
        """initializes instance variables and reads api keys from a json file.

        Arguments:
            keyfile: path to a json file containing at least the field
                'bearer_token'. api keys are obtained from twitter.
        """

        self.http_client = AsyncHTTPClient()

        with open(keyfile) as keys:
            self.twitter_api_keys = json.load(keys)

        self.queued_users = []

        self.found_users = {}

        self.queued_http_requests = deque()

    async def queue_http_request(self, url_or_req):
        """adds a http request to queued_http_requests and starts it once there are
        less than 10 active requests. keeps requests from timing out in tornado's
        request queue.

        Arguments:
            url_or_req: either a string containing a url or a
                tornado.httpclient.HTTPRequest object that will be passed to our http
                client's fetch method.
        """

        coroutine_object = self.http_client.fetch(url_or_req)
        self.queued_http_requests.append(coroutine_object)
        if len(self.queued_http_requests) > 10:
            await self.queued_http_requests[-2]
        resp = await coroutine_object
        self.queued_http_requests.popleft()
        return resp

    async def get_avatar(self, user_dict):
        """asynchronously retrieves an avatar based on user data from an api request
        and adds it to the user data in the 'avatar_bytes' field. meant to be run in
        parallel with other coroutines for efficiency.

        Arguments:
            user_dict: a dictionary meant to be loaded from json returned by an api
                request carried out in users_api_request.
        """

        try:
            print(f"saving avatar for user @{user_dict['screen_name']}")
            user_dict["avatar_bytes"] = (
                await self.queue_http_request(user_dict["profile_image_url_https"])
            ).body
        except HTTPClientError as e:
            print(repr(e))
            print(
                "warning: could not retrieve avatar from "
                + f'{user_dict["profile_image_url_https"]} for {user_dict["id"]}'
            )
            user_dict["avatar_bytes"] = bytes()

    async def users_api_request(self, users):
        """makes an api request for the users specified by the ids in the users
        argument; runs the requests for the avatars of those users in parallel; calls
        the callback function associated with each user id to deliver the data to
        this object's owner.

        Arguments:
            users: a list of user ids in string form.
        """
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
        except HTTPClientError as e:
            print(repr(e))
            print(f"warning: not able to retrieve user data for any ids in {users}")
            return

        print(f"retrieved data for {len(user_data)} twitter accounts")
        retrieved_users = set(x["id_str"] for x in user_data)

        avatar_reqs = []
        for user in user_data:
            avatar_reqs.append(self.get_avatar(user))
        await asyncio.gather(*avatar_reqs)

        for user in user_data:
            self.found_users[user["id_str"]](user)

        for user in set(users) - retrieved_users:
            self.found_users[user](None)

    async def flush_queue(self):
        """causes all currently queued requests for users' data to be acted upon;
        should be run and awaited before the owner of this object closes up shop.
        """
        if len(self.queued_users) == 0:
            print("nothing in twitter user request queue to act upon")
        else:
            print(
                f"requesting user data for {len(self.queued_users)} twitter accounts"
            )
            api_reqs = []
            while len(self.queued_users):
                users = self.queued_users[0:100]
                self.queued_users = self.queued_users[100:]
                api_reqs.append(self.users_api_request(users))
            await asyncio.gather(*api_reqs)

    def queue_twitter_user_request(self, user_id, callback):
        """adds a user id to the queue and registers a callback function that a dict
        of the user's data (including bytes containing an image file representing
        their avatar in 'avatar_bytes') will be passed to once it is retrieved.

        Arguments:
            user_id: the unique id of a twitter user.
            callback: a function that can accept a dict containing twitter api data
                and an image file for the user in the 'avatar_bytes' field.
        """
        # user ids can be stored as ints or strings; the str() cast is just so that
        # within this class, they're represented consistently
        self.queued_users.append(str(user_id))
        self.found_users[user_id] = callback
        if len(self.queued_users) == 100:
            asyncio.create_task(self.flush_queue())


class TwitterDataWriter(Connection):
    """creates a database containing group and individual direct messages and associated data.

    broadly, this class recieves a twitter account name and id, a series of messages
    and other conversation events through its add_message method, and turns the data
    into a sqlite3 database file that can be queried to obtain information about the
    recorded conversants and conversations in excrutiating detail. setup.sql contains
    the database schema that indicates the data that is preserved (and inferred.) note:
    does very little type casting or checking; sqlite3 is expected to do this based on
    each column of data's type affinity in the schema.

    Attributes:
        account: string name for the account that is being preserved; used as the
            filename for the resulting sqlite3 database file.
        account_id: twitter unique id for the account that is being preserved.
        added_users_cache: set of the ids of users we've added to the database.
        added_conversations_cache: set of the ids of conversations we've added to the
            database.
        added_participants_cache: set of (user_id, conversation_id) tuples
            corresponding to records of specific users' appearances in specific
            conversations that we've added to the database.
        api_client: instance of SimpleTwitterAPIClient that will be used to retrieve
            data for users given their ids for storage in the database.
        added_messages: tracks the number of messages or other conversation events
            that have been added to the database. intended to be used by this object's
            owner for progress reports
    """

    def __init__(self, account_name, account_id):
        """creates a database file for an archive for a specific account, initializes
        it with a sql script that creates tables within it, begins our overall sql
        transaction, and saves the id of the account being archived in the
        database."""
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

        # keeps python from automatically creating and ending database transactions
        # so that all of our inserts can be contained in one large one (faster)
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
        self.added_participants_cache = set()

        self.api_client = SimpleTwitterAPIClient("api_keys.json")

        self.added_messages = 0

    @property
    def added_conversations(self):
        """returns number of conversations that have been stored in the database;
        intended for progress-checking"""
        return len(self.added_conversations_cache)

    @property
    def added_users(self):
        """returns number of users that have been stored in the database;
        intended for progress-checking"""
        return len(self.added_users_cache)

    def save_user_data(self, user):
        """receives a dict containing data about a user from the twitter api and
        bytes containing an image file for the user's avatar and saves this
        information in the database. intended to be passed as a callback function
        to queue_twitter_user_request in the SimpleTwitterAPIClient class."""
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

    def add_user_if_necessary(self, user_id):
        """one-stop shop for adding a user record for a user id to the
        database; should be called whenever a user id is encountered.

        adds a mostly-empty row at first, but place the user id in the api client's
        queue with save_user_data as a callback function so that the row will be
        populated with data from the twitter api momentarily if it's available.
        """
        if user_id not in self.added_users_cache:
            if not self.execute(
                "select 1 from users where id=?;", (user_id,)
            ).fetchone():
                self.execute(
                    "insert into users (id, loaded_full_data) values(?, 0);",
                    (user_id,),
                )
                self.api_client.queue_twitter_user_request(
                    user_id, self.save_user_data
                )
                self.added_users_cache.add(user_id)

    def add_participant_if_necessary(
        self, user_id, conversation_id, start_time=None, end_time=None, added_by=None
    ):
        """one-stop shop for adding an record of a particular user appearing in a
        particular conversation to the database; should be called whenever a user id
        is encountered. adds a very simple record if no record of this participation
        exist yet and then, if start_time, end_time, or added_by are present, updates
        the existing record with this new information. missing information in any
        given participant record will be filled in when finalize() is called.

        Arguments:
            user_id: the usual one
            conversation_id: same
            start_time: timestamp in YYYY-MM-DDTHH:MM:SS.MMMZ format indicating the
                time at which this user was first seen in this conversation. we know this
                if we're processing a participantsJoin or joinConversation event.
            end_time: timestamp indicating the last time this user was seen in this
                conversation. we know this if we're processing a participantsLeave event.
            added_by: id of the user that added this participant to this
                conversation. we know this if we're processing a participantsJoin event.
        """
        if (
            user_id,
            conversation_id,
        ) not in self.added_participants_cache:
            self.execute(
                """insert or replace into participants
                            (participant, conversation)
                            values (?, ?);""",
                (user_id, conversation_id),
            )
            self.added_participants_cache.add((user_id, conversation_id))
        if start_time:
            self.execute(
                """update participants 
                    set start_time=? where participant=? and conversation=?;""",
                (start_time, user_id, conversation_id),
            )
        if end_time:
            self.execute(
                """update participants 
                    set start_time=? where participant=? and conversation=?;""",
                (end_time, user_id, conversation_id),
            )
        if added_by:
            self.execute(
                """update participants 
                    set added_by=? where participant=? and conversation=?;""",
                (added_by, user_id, conversation_id),
            )

    def add_conversation_if_necessary(
        self, conversation_id, group_dm, other_person, first_time=None, added_by=None
    ):
        """one-stop shop for adding a conversation record to the database. if
        first_time and added_by are present, we're processing a conversationJoin
        event and need to update the conversation record with that info (after
        creating it if necessary.) missing information in any given conversation
        record will be filled in when finalize() is called.
        """

        if conversation_id not in self.added_conversations_cache:
            self.execute(
                "insert into conversations (id, type, other_person) values (?, ?, ?);",
                (
                    conversation_id,
                    "group" if group_dm else "individual",
                    other_person,
                ),
            )
            self.added_conversations_cache.add(conversation_id)
        # either both should be present or neither
        assert (first_time and added_by) or (not first_time and not added_by)
        if first_time and added_by:
            self.execute(
                "update conversations set first_time=?, added_by=? where id=?;",
                (first_time, added_by, conversation_id),
            )

    def add_message(self, message, group_dm=False):
        """one-stop shop for adding a message or other conversation event to the
        database, with the above types of record as a consequence. aaaaaaaaa
        """

        recipient_id = (
            None
            if group_dm
            else (
                message["recipientId"]
                if message["senderId"] == str(self.account_id)
                else message["senderId"]
            )
        )
        self.add_conversation_if_necessary(
            message["conversationId"], group_dm, recipient_id
        )

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
                    self.add_participant_if_necessary(
                        user_id,
                        message["conversationId"],
                        start_time=message["createdAt"],
                        added_by=message["initiatingUserId"],
                    )
            else:
                for user_id in message["userIds"]:
                    self.add_user_if_necessary(user_id)
                    self.add_participant_if_necessary(
                        user_id,
                        message["conversationId"],
                        end_time=message["createdAt"],
                    )

        elif message["type"] == "joinConversation":
            self.add_conversation_if_necessary(
                message["conversationId"],
                group_dm,
                recipient_id,
                message["createdAt"],
                message["initiatingUserId"],
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
        """runs the script that creates the indexes; runs the script that infers data
        to put into the gaps in the participants and conversations tables; waits for
        the fetching of user data from the twitter api to be done; optimizes,
        shrinks, and closes the database."""
        self.commit()

        print("indexing data...")
        with open("indexes.sql") as index_script:
            self.executescript(index_script.read())
        with open("cache_conversation_stats.sql") as conversation_stats_script:
            self.executescript(conversation_stats_script.read())

        await self.api_client.flush_queue()

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
