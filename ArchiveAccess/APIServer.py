from tornado.web import RequestHandler, Application
from tornado.ioloop import IOLoop
from ArchiveAccess.DBRead import TwitterDataReader, DBRow
from typing import Union

query_string = r"\?.+"


class ArchiveAPIServer:

    handlers = []

    def __init__(
        self,
        reader: TwitterDataReader,
        group_media_path: str,
        individual_media_path: str,
    ):
        self.group_media_path = group_media_path
        self.individual_media_path = individual_media_path
        self.db = reader
        initializer = {"reader": self.db}
        self.application = Application([x + (initializer,) for x in self.handlers])

    def start(self):
        print("starting server on port 8008")
        self.application.listen(8008)
        IOLoop.current().start()


def handles(url):
    def register_handler(handler_class):
        ArchiveAPIServer.handlers.append((url, handler_class))

    return register_handler


class APIRequestHandler(RequestHandler):
    """abstract base class"""

    def initialize(self, reader: TwitterDataReader):
        self.db = reader

    def prepare(self):
        super().prepare()
        # TODO: check authentication; maybe using an access_level_required parameter
        # passed to initialize

    @staticmethod
    def serialize_chunk(chunk: Union[str, bytes, dict, DBRow, list, None]):
        if isinstance(chunk, DBRow):
            return chunk.serialize()
        elif isinstance(chunk, list):
            return {
                "results": [
                    (x.serialize() if isinstance(x, DBRow) else x) for x in chunk
                ]
            }
        else:
            return chunk

    def write(self, chunk: Union[str, bytes, dict, DBRow, list, None] = None):
        return super().write(self.serialize_chunk(chunk))

    def finish(self, chunk: Union[str, bytes, dict, DBRow, list, None] = None):
        return super().finish(self.serialize_chunk(chunk))


@handles(r"/api/conversations")
class AllConversationsHandler(APIRequestHandler):
    def get(self):
        types = self.get_query_argument("types").split("-")
        group = "group" in types
        individual = "individual" in types
        method = self.get_query_argument("first")
        page_number = int(self.get_query_argument("page"))
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
        user_id = self.get_query_argument("id")
        page_number = int(self.get_query_argument("page"))
        self.finish(self.db.get_conversations_by_user(user_id, page_number))


@handles(r"/api/conversation")
class ConversationByID(APIRequestHandler):
    def get(self):
        self.finish(self.db.get_conversation_by_id(self.get_query_argument("id")))


@handles(r"/api/")
@handles(r"/api/avatar/\d+\.[A-Za-z]+")
class AvatarRequestHandler(APIRequestHandler):
    def get(self):
        id = int(self.request.path.split("/")[-1].split(".")[0])
        avatar = self.db.get_user_avatar(id)
        self.set_header("Content-Type", "image/" + avatar[1].replace("jpg", "jpeg"))
        self.finish(avatar[0])
