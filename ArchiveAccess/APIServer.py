from tornado.web import RequestHandler, Application, StaticFileHandler
from tornado.template import Template, Loader
from tornado.ioloop import IOLoop
from ArchiveAccess.DBRead import TwitterDataReader, DBRow
from typing import Union, Iterable
from mimetypes import guess_type
from pathlib import Path
import json
import subprocess
import re
import secrets
from time import perf_counter


class ServeFrontend(RequestHandler):
    def initialize(
        self,
        reader: TwitterDataReader,
        titles: dict,
        db_owner: str,
        tokens: Union[set, None],
    ):
        self.db = reader
        self.titles = titles
        self.db_owner = db_owner
        self.authenticated_tokens = tokens

    def get(self, path):
        if (
            self.authenticated_tokens
            and self.get_cookie("Authentication") not in self.authenticated_tokens
        ):
            self.render(
                "index.html",
                title="Twitter Data Archive",
                image="",
                description="",
            )
            return

        description = self.db_owner + "'s Twitter archive"
        image = None
        if self.request.path in self.titles:
            title = self.titles[self.request.path]
        elif m := re.match(r"/user/(info|messages)/(\d+)", self.request.path):
            id = int(m[2])
            users = self.db.get_users_by_id([int(id)])
            if users:
                user = users[0]
                title = (
                    ("Messages from " if m[1] == "messages" else "")
                    + (user.nickname if user.nickname else ("@" + user.handle))
                    + (" - User Info" if m[1] == "info" else "")
                )
        elif m := re.match(
            r"/conversation/(info|messages)/((?:\d|-)+)", self.request.path
        ):
            conversation = self.db.get_conversation_by_id(m[2])
            title = conversation.name + (
                " - Conversation Info" if m[1] == "info" else ""
            )
        else:
            title = "Twitter Data Archive"

        if m := re.search(r"/messages/(?:(?:\d|-)+)/(\d+)", self.request.path):
            message = self.db.get_message_by_id(int(m[1]))
            if message["results"]:
                user = next(
                    x
                    for x in message["users"]
                    if str(x.id) == message["results"][0].sender
                )
                message = message["results"][0]
                description = (
                    message.content + " - " + (user.nickname or "@" + user.handle)
                )
                if any(x.type == "image" for x in message.media):
                    protocol = (
                        "https://"
                        if self.request.headers.get("X-Forwarded-Proto") == "https"
                        else "http://"
                    )
                    image = (
                        protocol
                        + self.request.host
                        + next(x for x in message.media if x.type == "image").src
                    )

        self.render(
            "index.html",
            title=title,
            image=image,
            description=description,
        )


class Authenticator(RequestHandler):
    def initialize(self, token_store, password):
        self.token_store: set = token_store
        self.password: str = password

    def post(self):
        if (
            str(self.request.body, "utf-8") == self.password
            or self.get_cookie("Authentication") in self.token_store
        ):
            new_token = secrets.token_urlsafe(32)
            self.token_store.add(new_token)
            self.set_cookie("Authentication", new_token, expires_days=365)
            self.finish()
        elif not self.password:
            self.set_status(200)
            self.finish()
        else:
            self.set_status(403, "missing or incorrect password")
            self.finish()


class ArchiveAPIServer:

    handlers = []

    def __init__(
        self,
        reader: TwitterDataReader,
        individual_media_path: str,
        group_media_path: str,
        port: int,
        password: str = "",
    ):
        self.port = port
        db_owner = "@" + reader.get_main_user().handle
        authenticated_tokens = set()
        initializer = {
            "reader": reader,
            "group_media": group_media_path,
            "individual_media": individual_media_path,
            "require_password": bool(password),
            "tokens": authenticated_tokens,
        }
        assets_handler = (
            r"/assets/(.*)",
            StaticFileHandler,
            {"path": "./frontend/assets/"},
        )
        with open("./frontend/routes.json") as routes:
            titles = json.load(routes)
        frontend_handler = (
            r"^(?!/assets/|/api/|/frontend/)/(.*)$",
            ServeFrontend,
            {
                "reader": reader,
                "titles": titles,
                "db_owner": db_owner,
                "tokens": authenticated_tokens if password else None,
            },
        )
        authenticator = (
            "/api/authenticate",
            Authenticator,
            {"token_store": authenticated_tokens, "password": password},
        )
        self.application = Application(
            [assets_handler, frontend_handler, authenticator]
            + [x + (initializer,) for x in self.handlers],
            compress_response=True,
            static_path="./frontend/assets/",
            template_path="./frontend/",
            static_hash_cache=False,
        )

    def start(self):
        subprocess.Popen(
            "npx webpack --watch --stats minimal",
            shell=True,
        )
        print("starting server at http://localhost:" + str(self.port))
        self.application.listen(self.port)
        IOLoop.current().start()


def handles(url):
    def register_handler(handler_class):
        ArchiveAPIServer.handlers.append((url, handler_class))

    return register_handler


class APIRequestHandler(RequestHandler):
    """abstract base class"""

    def initialize(
        self,
        reader: TwitterDataReader,
        group_media: str,
        individual_media: str,
        require_password: bool,
        tokens: set,
    ):
        self.db = reader
        self.group_media = group_media
        self.individual_media = individual_media
        self.require_password = require_password
        self.tokens = tokens

    def prepare(self):
        super().prepare()
        if (
            self.require_password
            and self.get_cookie("Authentication") not in self.tokens
        ):
            self.set_status(403, "Not authenticated >:(")
            self.finish()

    @classmethod
    def recursive_serialize(cls, item):
        if isinstance(item, DBRow):
            return item.serialize()
        elif isinstance(item, list):
            return [(x.serialize() if isinstance(x, DBRow) else x) for x in item]
        elif isinstance(item, dict):
            for key in item:
                item[key] = cls.recursive_serialize(item[key])
            return item
        else:
            return item

    @classmethod
    def process_chunk(cls, chunk):
        serialized_chunk = cls.recursive_serialize(chunk)
        if isinstance(chunk, list):
            return {"results": serialized_chunk}
        return serialized_chunk

    def write(self, chunk: Union[str, bytes, dict, DBRow, list, None] = None):
        return super().write(self.process_chunk(chunk))

    def finish(self, chunk: Union[str, bytes, dict, DBRow, list, None] = None):
        return super().finish(self.process_chunk(chunk))

    def get_query_argument(self, name, *args):
        if name == "page":
            page = int(super().get_query_argument(name, *args))
            if page == 0:
                self.set_status(404, "page numbers start from 1")
            return page
        else:
            return super().get_query_argument(name, *args)

    def arguments(self, *args):
        return tuple(self.get_query_argument(x, None) for x in args)


@handles(r"/api/login")
@handles(r"/api/conversations")
class AllConversationsHandler(APIRequestHandler):
    def get(self):
        types = self.get_query_argument("types").split("-")
        group = "group" in types
        individual = "individual" in types
        assert (
            len([x for x in types if x not in ("", "group", "individual")]) == 0
        ), "conversation types are limited to 'group' and 'individual'"
        method, page_number = self.arguments("first", "page")
        if (asc := method == "oldest") or method == "newest":
            self.finish(
                self.db.get_conversations_by_time(
                    page_number, asc, group, individual
                )
            )
        elif (by_me := method == "mostusedbyme") or method == "mostused":
            self.finish(
                self.db.get_conversations_by_message_count(
                    page_number, group, individual, by_me
                )
            )


@handles(r"/api/conversations/withuser")
class ConversationsByUserHandler(APIRequestHandler):
    def get(self):
        user_id, page_number = self.arguments("id", "page")
        self.finish(self.db.get_conversations_by_user(user_id, page_number))


@handles(r"/api/conversation")
class ConversationByID(APIRequestHandler):
    def get(self):
        self.finish(self.db.get_conversation_by_id(self.get_query_argument("id")))


@handles(r"/api/conversation/names")
class ConversationNames(APIRequestHandler):
    def get(self):
        conversation, order, page = self.arguments("conversation", "first", "page")
        assert order in ("oldest", "newest"), "malformed 'first' query argument"
        self.finish(
            self.db.get_conversation_names(conversation, order == "oldest", page)
        )


@handles(r"/api/conversation/notes")
class SetConversationNotes(APIRequestHandler):
    def post(self):
        id = self.get_query_argument("id")
        new_notes = str(self.request.body, "utf-8")
        self.db.set_conversation_notes(id, new_notes)
        self.set_status(200)
        self.finish(None)


@handles(r"/api/messages/random")
class RandomMessages(APIRequestHandler):
    def get(self):
        self.finish(self.db.get_random_messages())


@handles(r"/api/messages")
class Messages(APIRequestHandler):
    def get(self):
        started_at = perf_counter()
        conversation, user = self.arguments("conversation", "byuser")
        after, before, at, message = self.arguments(
            "after", "before", "at", "message"
        )
        if message:
            at = self.db.get_message_timestamp_by_id(int(message))
        search = self.get_query_argument("search", None)
        self.finish(
            self.db.traverse_messages(conversation, user, after, before, at, search)
        )
        print(f"request for messages took {(perf_counter()-started_at/1000):.0f} ms")


@handles(r"/api/message")
class SingleMessage(APIRequestHandler):
    def get(self):
        self.finish(self.db.get_message_by_id(int(self.get_query_argument("id"))))


@handles(r"/api/users")
class Users(APIRequestHandler):
    def get(self):
        conversation, page = self.arguments("conversation", "page")
        self.finish(self.db.get_users_by_message_count(page, conversation))


@handles(r"/api/user")
class SingleUser(APIRequestHandler):
    def get(self):
        self.finish(
            self.db.get_users_by_id([int(self.get_query_argument("id"))], False)[0]
        )


@handles(r"/api/globalstats")
class SingleUser(APIRequestHandler):
    def get(self):
        self.finish(self.db.get_global_stats())


@handles(r"/api/user/nickname")
class UserNickname(APIRequestHandler):
    def post(self):
        id = self.get_query_argument("id")
        self.db.set_user_nickname(id, str(self.request.body, "utf-8"))
        self.set_status(200)
        self.finish()


@handles(r"/api/user/notes")
class UserNotes(APIRequestHandler):
    def post(self):
        id = self.get_query_argument("id")
        self.db.set_user_notes(id, str(self.request.body, "utf-8"))
        self.set_status(200)
        self.finish()


@handles(r"/api/media/(group|individual)/(.+)")
class Media(APIRequestHandler):
    def get(self, type, filename):
        file_location = (
            Path(self.group_media if type == "group" else self.individual_media)
            / filename
        )
        self.set_header("Content-Type", guess_type(self.request.path)[0])
        if Path(file_location).exists():
            with open(file_location, "rb") as media:
                while True:
                    data = media.read(5000000)
                    if not data:
                        break
                    self.write(data)
        else:
            self.set_status(404)
        self.finish()


@handles(r"/api/avatar/(\d+)\.[A-Za-z]+")
class AvatarRequestHandler(APIRequestHandler):
    def get(self, id):
        avatar = self.db.get_user_avatar(int(id))
        self.set_header("Content-Type", guess_type("a." + avatar[1])[0])
        self.finish(avatar[0])