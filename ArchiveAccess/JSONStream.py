import ijson
from pprint import pprint
from pathlib import Path


class PrefixedJSON:
    """takes a .js file that assigns some json-formatted data to a global variable
    (like the twitter archive .js files do) and skips past the assignment so that the
    file can be used as pure json. compatible with the json and ijson modules.

    Attributes:
        filename: name/path of the file we're using.

    How to use:
        >>> with PrefixedJSON("file.js") as json_file:
        >>>     parser = ijson.parse(json_file)
    """

    def __init__(self, file):
        self.filename = file

    def __enter__(self):
        """prepares a file to be read as json.

        opens a file in bytes mode (for ijson compatibility/optimization purposes),
        reads data from it until it finds a character that can act as the start of
        some json data, then seeks backwards one byte so that that character is the
        next one that will be read.

        Returns:
            a prepared file object.
        """
        self.file = open(self.filename, "rb")
        byte = self.file.read(1)
        while byte != bytes("[", encoding="utf-8") and byte != bytes(
            "{", encoding="utf-8"
        ):
            byte = self.file.read(1)
        self.file.seek(-1, 1)
        return self.file

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.file.close()


class MessageStream:
    """turns twitter archive .js files containing dms into an iterable stream of
    messages and other conversation events.

    returns messageCreate and other channel event objects for either a group dm or
    individual dm .js file with the small modification of placing the conversation ids
    and event names in each event dict instead of having them outside (in the
    "conversationId" and "type" fields respectively). uses the ijson module to avoid
    loading the whole .js file into memory.

    Attributes:
        path: path to .js file that the messages are being obtained from
        ijson_events_processed: an ijson event is raised when ijson finds some data
            in the code; the number of processed events here serves as a progress
            indicator. ijson events are not to be confused with conversation events like
            messageCreate or the other ones this class yields, which contain a lot more
            data.
        ijson_events_total: the total number of ijson events reading this file will
            cause.

    How to use:
        >>> for message in MessageStream("messages.js"):
        >>>     save_in_database(message)
    """

    def __init__(self, path):
        """initializes the object and does a quick pre-count of how many ijson events
        we will have to process.

        Args:
            path: path to the .js file this object will glean conversation events from.
        """
        self.path = path
        self.ijson_events_processed = 0
        self.ijson_events_total = 0
        with PrefixedJSON(self.path) as temp:
            for _ in ijson.parse(temp):
                self.ijson_events_total += 1

    @property
    def percentage(self):
        "simplest way to see how much of the current file has been read"
        return self.ijson_events_processed / self.ijson_events_total * 100

    def __iter__(self):
        """gathers ijson events and yields dicts representing conversation events as
        they emerge.

        conversation events can be of the types messageCreate, joinConversation,
        participantsJoin, participantsLeave, or conversationNameUpdate; this method
        grabs each object representing one of these events, adds 'type' and
        'conversationId' fields to them based on context from elsewhere in the json
        data, and yields them.

        """
        with PrefixedJSON(self.path) as json_file:
            conversation_id = ""
            in_message = False
            message = {}
            current_dict = message

            event_types = [
                "messageCreate",
                "joinConversation",
                "participantsJoin",
                "participantsLeave",
                "conversationNameUpdate",
            ]

            for prefix, event, value in ijson.parse(json_file):
                if prefix == "item.dmConversation.conversationId":
                    conversation_id = value
                if prefix.startswith(
                    tuple(
                        "item.dmConversation.messages.item." + x + "."
                        for x in event_types
                    )
                ):
                    key = prefix.split(".")[-1]
                    in_message = True
                    message["type"] = prefix.split(".")[4]
                    if event == "start_array":
                        message[key] = []
                    elif event == "start_map":
                        array_name = prefix.split(".")[-2]
                        message[array_name].append({})
                        current_dict = message[array_name][-1]
                    elif event == "end_map":
                        current_dict = message
                    elif event in [
                        "string",
                        "null",
                        "boolean",
                        "integer",
                        "double",
                        "number",
                    ]:
                        if key == "item":
                            array_name = prefix.split(".")[-2]
                            message[array_name].append(value)
                        else:
                            current_dict[key] = value
                elif prefix == "item.dmConversation.messages.item" and in_message:
                    message["conversationId"] = conversation_id
                    yield message
                    message = {}
                    current_dict = message
                    in_message = False
                self.ijson_events_processed += 1


def prefix_finder(path):
    "returns all the prefixes ijson finds in a file; used for parser development"
    with PrefixedJSON(path) as json_file:
        prefixes = set()
        for p, _, _ in ijson.parse(json_file):
            prefixes.add(p)
    return prefixes


def dump(path):
    """prints all the data ijson finds in a file in ijson event form; Not Recommended
    for large files"""
    with PrefixedJSON(path) as json_file:
        for prefix, event, value in ijson.parse(json_file):
            print("prefix=" + prefix + ", event=" + event + ", value=" + str(value))


def test(path):
    """shady test function that prints the dicts that the parser outputs for a given
    file for manual review"""
    for message in (s := MessageStream(path)) :
        pprint(message, width=200)
        print(f"percentage: {s.percentage}")


if __name__ == "__main__":
    print("------------ Individual DMs Test ------------")
    test("./testdata/individual_dms_test.js")
    print()
    print("------------ Group DMs Test ------------")
    test("./testdata/group_dms_test.js")
