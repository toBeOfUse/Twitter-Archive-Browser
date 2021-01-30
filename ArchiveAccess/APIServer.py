from tornado.web import RequestHandler, Application, StaticFileHandler
from tornado.ioloop import IOLoop
from ArchiveAccess.DBRead import TwitterDataReader, DBRow
from typing import Union, Iterable
from mimetypes import guess_type
from pathlib import Path
import subprocess

query_string = r"\?.+"


class DevStaticFileHandler(StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header(
            "Cache-Control", "no-store, no-cache, must-revalidate, max-age=0"
        )


class ServeFrontend(RequestHandler):
    def get(self, path):
        with open("./frontend/assets/html/index.html") as page:
            self.finish(page.read())


class ArchiveAPIServer:

    handlers = []

    def __init__(
        self,
        reader: TwitterDataReader,
        individual_media_path: str,
        group_media_path: str,
    ):
        self.db = reader
        initializer = {
            "reader": self.db,
            "group_media": group_media_path,
            "individual_media": individual_media_path,
        }
        assets_handler = (
            r"/(assets/.*)",
            DevStaticFileHandler,
            {"path": "./frontend/"},
        )
        source_handler = (
            r"/(frontend/.*)",
            DevStaticFileHandler,
            {"path": "./"},
        )
        frontend_handler = (r"^(?!/assets/|/api/|/frontend/)/(.*)$", ServeFrontend)
        self.application = Application(
            [assets_handler, source_handler, frontend_handler]
            + [x + (initializer,) for x in self.handlers],
            compress_response=True,
        )

    def start(self):
        subprocess.Popen(
            "npx webpack --watch --stats minimal",
            shell=True,
        )
        print("starting server on port 8008")
        self.application.listen(8008)
        IOLoop.current().start()


def handles(url):
    def register_handler(handler_class):
        ArchiveAPIServer.handlers.append((url, handler_class))

    return register_handler


class APIRequestHandler(RequestHandler):
    """abstract base class"""

    def initialize(
        self, reader: TwitterDataReader, group_media: str, individual_media: str
    ):
        self.db = reader
        self.group_media = group_media
        self.individual_media = individual_media

    def prepare(self):
        super().prepare()
        # TODO: check authentication; maybe using an access_level_required parameter
        # passed to initialize

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


@handles(r"/api/conversations")
class AllConversationsHandler(APIRequestHandler):
    def get(self):
        types = self.get_query_argument("types").split("-")
        group = "group" in types
        individual = "individual" in types
        assert (
            len([x for x in types if x not in ("group", "individual")]) == 0
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
        conversation, user = self.arguments("conversation", "byuser")
        after, before, at = self.arguments("after", "before", "at")
        search = self.get_query_argument("search", None)
        self.finish(
            self.db.traverse_messages(conversation, user, after, before, at, search)
        )


@handles(r"/api/message")
class SingleMessage(APIRequestHandler):
    def get(self):
        self.finish(self.db.get_message(int(self.get_query_argument("id"))))


@handles(r"/api/users")
class Users(APIRequestHandler):
    def get(self):
        conversation, page = self.arguments("conversation", "page")
        self.finish(self.db.get_users_by_message_count(page, conversation))


@handles(r"/api/user")
class SingleUser(APIRequestHandler):
    def get(self):
        self.finish(
            self.db.get_users_by_id([self.get_query_argument("id")], False)[0]
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
            self.group_media if type == "group" else self.individual_media
        ) + filename
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