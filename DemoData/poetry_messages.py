from DemoData.MessageFactory import MessageFactory
from datetime import datetime
from DemoData.demo_constants import DEMO_ACCOUNT_ID, DICKINSON_ID, ELIOT_ID, POE_ID
from random import choice

poetry_factory = MessageFactory("2", datetime(2010, 1, 1), minutes_apart=5)


def poetry_gen():
    yield poetry_factory.create_name_update(DICKINSON_ID, "Poetry Slam")
    yield poetry_factory.create_message(
        DEMO_ACCOUNT_ID,
        "Welcome to the poetry slam! This conversation contains many intermixed"
        " stanzas from poetry in the public domain, to show how conversations with"
        " many messages will be displayed. Note that you can click on participant's"
        " names to view their info pages, change their nicknames, and view the"
        " messages that they specifically sent.",
    )
    yield poetry_factory.create_message(
        DICKINSON_ID,
        'Text of poems by Emily Dickinson taken from "Poems: Three Series, '
        'Complete", obtained via Project Gutenberg.',
    )
    yield poetry_factory.create_message(
        ELIOT_ID,
        'Text of poems by T. S. Eliot taken from "Poems", obtained via Project'
        " Gutenberg.",
    )
    yield poetry_factory.create_message(
        POE_ID,
        'Text of poems by Edgar Allan Poe taken from "The Complete Poetical'
        ' Works of Edgar Allan Poe", obtained via Project Gutenberg.',
    )
    with open("./DemoData/dickinson.txt", encoding="utf-8") as dickinson_file:
        with open("./DemoData/eliot.txt", encoding="utf-8") as eliot_file:
            with open("./DemoData/poe.txt", encoding="utf-8") as poe_file:
                active_files = set(
                    [
                        (DICKINSON_ID, dickinson_file),
                        (ELIOT_ID, eliot_file),
                        (POE_ID, poe_file),
                    ]
                )
                stanza = ""
                while len(active_files):
                    chosen_file = choice(tuple(active_files))
                    while True:
                        line = chosen_file[1].readline()
                        if not line:
                            active_files.remove(chosen_file)
                            if stanza.strip():
                                yield poetry_factory.create_message(
                                    chosen_file[0], stanza.strip()
                                )
                            stanza = ""
                            break
                        elif line.strip():
                            stanza += line.strip() + "\n"
                        elif stanza.strip():
                            if len(stanza) > 6:
                                yield poetry_factory.create_message(
                                    chosen_file[0], stanza.strip()
                                )
                            stanza = ""
                            break


poetry = poetry_gen()