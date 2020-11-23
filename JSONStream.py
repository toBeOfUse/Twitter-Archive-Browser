import ijson
from pprint import pprint
from pathlib import Path


# opens file, skips past twitter's `window.YTD.yaddayadda = ` prefix
class PrefixedJSON:
    def __init__(self, file):
        self.filename = file

    def __enter__(self):
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


# returns messageCreate and other channel event objects for either a group dm or
# individual dm .js file with the small modification of placing the conversation ids
# and event names in each message instead of having them outside (in the
# "conversationId" and "type" fields respectively)
class MessageStream:
    def __init__(self, path):
        self.path = path
        self.percentage = 0
        # this pre-scan casues a performance pause but is the only way to get a
        # percentage progress report that i can think of, and that makes the rest of
        # it go faster
        self.number_of_events = 0
        with PrefixedJSON(self.path) as temp:
            for _ in ijson.parse(temp):
                self.number_of_events += 1

    def __iter__(self):
        with PrefixedJSON(self.path) as json_file:
            conversation_id = ""
            in_message = False
            message = {}
            current_dict = message
            handled_events = 0

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
                    self.percentage = handled_events / self.number_of_events * 100
                    yield message
                    message = {}
                    current_dict = message
                    in_message = False
                handled_events += 1


# returns all the prefixes ijson finds in a file; useful for parser development
def prefix_finder(path):
    with PrefixedJSON(path) as json_file:
        prefixes = set()
        for p, _, _ in ijson.parse(json_file):
            prefixes.add(p)
    return prefixes


# prints all the data ijson finds in a file, parsed; Not Recommended for large files
def dump(path):
    with PrefixedJSON(path) as json_file:
        for prefix, event, value in ijson.parse(json_file):
            print("prefix=" + prefix + ", event=" + event + ", value=" + str(value))


# shady test function that prints parser results for manual review
def test(path):
    for message in (s := MessageStream(path)) :
        pprint(message, width=200)
        print(f"percentage: {s.percentage}")


if __name__ == "__main__":
    print("------------ Individual DMs Test ------------")
    test("./testdata/individual_dms_test.js")
    print()
    print("------------ Group DMs Test ------------")
    test("./testdata/group_dms_test.js")
