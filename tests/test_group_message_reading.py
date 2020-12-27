"""these tests make sure that the MessageStream class accurately loads message and
message-like objects as dicts from the group dms test .js file with the addition of
the type and conversaationId fields."""

from ArchiveAccess.JSONStream import MessageStream


def test_read():
    global messages
    messages = [x for x in MessageStream("./tests/fixtures/group_dms_test.js")]
    assert len(
        messages
    ), "messages were not able to be loaded from the group dms test file"


def test_normal_message_read():
    assert messages[0] == {
        "reactions": [],
        "urls": [],
        "text": "Praesent facilisis vitae sapien a porttitor. Vivamus maximus lacinia fringilla.",
        "mediaUrls": [],
        "senderId": "31239408",
        "id": "700928388131790851",
        "createdAt": "2016-02-20T06:22:05.085Z",
        "type": "messageCreate",
        "conversationId": "convo_you_were_added_to",
    }, "first message not read correctly"


def test_participants_leave():
    assert messages[1] == {
        "userIds": ["18393773"],
        "createdAt": "2016-02-20T05:35:33.497Z",
        "type": "participantsLeave",
        "conversationId": "convo_you_were_added_to",
    }


def test_participants_join():
    assert messages[2] == {
        "initiatingUserId": "16573941",
        "userIds": ["5162861"],
        "createdAt": "2016-02-09T01:38:06.141Z",
        "type": "participantsJoin",
        "conversationId": "convo_you_were_added_to",
    }


def test_name_update():
    assert messages[3] == {
        "initiatingUserId": "16573941",
        "name": "yawntastic",
        "createdAt": "2016-02-08T18:43:50.249Z",
        "type": "conversationNameUpdate",
        "conversationId": "convo_you_were_added_to",
    }


def test_being_added():
    assert messages[4] == {
        "initiatingUserId": "3307595502",
        "participantsSnapshot": [
            "813286",
            "101",
            "18393773",
            "90420314",
            "1588486417",
            "5162861",
            "4196983835",
            "16573941",
            "31239408",
        ],
        "createdAt": "2015-12-20T10:51:37.176Z",
        "type": "joinConversation",
        "conversationId": "convo_you_were_added_to",
    }


def test_new_conversation():
    assert messages[5] == {
        "userIds": ["84279963"],
        "createdAt": "2016-02-20T05:35:33.497Z",
        "conversationId": "convo_you_created",
        "type": "participantsLeave",
    }
