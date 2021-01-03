"""these tests make sure that the MessageStream class accurately loads message and
message-like objects as dicts from the individual dms test .js file with the addition
of the type and conversaationId fields."""

from ArchiveAccess.JSONStream import MessageStream
from pytest import fixture


@fixture(scope="module")
def messages():
    source = MessageStream("./tests/fixtures/individual_dms_test.js")
    assert source.percentage == 0
    messages = [x for x in source]
    assert source.percentage == 100
    return messages


def test_read_message(messages):
    assert messages[0] == {
        "recipientId": "4196983835",
        "reactions": [],
        "urls": [],
        "text": "Enim occaecat ipsum nisi tempor consectetur.",
        "mediaUrls": [],
        "senderId": "846137120209190912",
        "id": "901565800758300677",
        "createdAt": "2017-08-26T22:03:31.928Z",
        "conversationId": "846137120209190912-4196983835",
        "type": "messageCreate",
    }, "first and simplest message failed to be accurately read"


def test_read_message_with_link(messages):
    assert messages[1] == {
        "recipientId": "846137120209190912",
        "reactions": [],
        "urls": [
            {
                "url": "https://t.co/yaddayadda",
                "expanded": "https://twitter.com/gerardway/status/746063088525271040?s=20",
                "display": "twitter.com/gerardway/stat…",
            }
        ],
        "text": "Irure Lorem nulla esse do fugiat aliqua reprehenderit proident eiusmod deserunt ea nisi. https://t.co/yaddayadda",
        "mediaUrls": [],
        "senderId": "4196983835",
        "id": "881820364548038659",
        "createdAt": "2017-07-03T10:22:13.090Z",
        "conversationId": "846137120209190912-4196983835",
        "type": "messageCreate",
    }, "message with link was not read correctly"


def test_read_message_with_media(messages):
    assert messages[2] == {
        "recipientId": "4196983835",
        "reactions": [],
        "urls": [
            {
                "url": "https://t.co/5IAkjDt0A2",
                "expanded": "https://twitter.com/messages/media/885513042674552835",
                "display": "pic.twitter.com/5IAkjDt0A2",
            }
        ],
        "text": " https://t.co/5IAkjDt0A2",
        "mediaUrls": [
            "https://ton.twitter.com/dm/885513042674552835/885513033925242880/ntkMMdTy.jpg"
        ],
        "senderId": "846137120209190912",
        "id": "885513042674552835",
        "createdAt": "2017-07-13T14:55:36.588Z",
        "conversationId": "846137120209190912-4196983835",
        "type": "messageCreate",
    }, "message with media was not read correctly"


def test_message_with_reaction(messages):
    assert messages[3] == {
        "recipientId": "4196983835",
        "reactions": [
            {
                "senderId": "4196983835",
                "reactionKey": "funny",
                "eventId": "1320946773276291073",
                "createdAt": "2020-10-27T04:33:47.424Z",
            }
        ],
        "urls": [
            {
                "url": "https://t.co/5IAkjDt0A2",
                "expanded": "https://twitter.com/messages/media/885513042674552835",
                "display": "pic.twitter.com/5IAkjDt0A2",
            }
        ],
        "text": " https://t.co/5IAkjDt0A2",
        "mediaUrls": [
            "https://ton.twitter.com/dm/885513042674552835/885513033925242880/ntkMMdTy.jpg"
        ],
        "senderId": "846137120209190912",
        "id": "885513042674552835",
        "createdAt": "2017-07-14T14:55:36.588Z",
        "conversationId": "846137120209190912-4196983835",
        "type": "messageCreate",
    }, "message with reaction was not read correctly"


def test_message_with_reactions(messages):
    assert messages[4] == {
        "recipientId": "4196983835",
        "reactions": [
            {
                "senderId": "4196983835",
                "reactionKey": "funny",
                "eventId": "1320946773276291073",
                "createdAt": "2020-10-22T04:33:47.424Z",
            },
            {
                "senderId": "846137120209190912",
                "reactionKey": "heart",
                "eventId": "1320946773276291073",
                "createdAt": "2020-10-27T04:33:47.424Z",
            },
        ],
        "urls": [
            {
                "url": "https://t.co/5IAkjDt0A2",
                "expanded": "https://twitter.com/messages/media/885513042674552835",
                "display": "pic.twitter.com/5IAkjDt0A2",
            }
        ],
        "text": " https://t.co/5IAkjDt0A2",
        "mediaUrls": [
            "https://ton.twitter.com/dm/885513042674552835/885513033925242880/ntkMMdTy.jpg"
        ],
        "senderId": "846137120209190912",
        "id": "885513042674552835",
        "createdAt": "2017-07-15T14:55:36.588Z",
        "conversationId": "846137120209190912-4196983835",
        "type": "messageCreate",
    }, "message with multiple reactions not read correctly"


def test_new_conversation(messages):
    assert messages[5] == {
        "recipientId": "4196983835",
        "reactions": [],
        "urls": [],
        "text": "Enim occaecat ipsum nisi tempor consectetur.",
        "mediaUrls": [],
        "senderId": "846137120209190912",
        "id": "901565800758300677",
        "createdAt": "2017-08-26T22:03:31.928Z",
        "conversationId": "846137120209190912-41969838356",
        "type": "messageCreate",
    }, "message from second conversation not read correctly"
