from DemoData.MessageFactory import MessageFactory
from datetime import datetime
from DemoData.demo_constants import DEMO_ACCOUNT_ID, VERIFIED_ACCOUNT, SETH_ACCOUNT

VERIFIED_ACCOUNT["generator"] = MessageFactory(
    "3", datetime(2015, 6, 1), recipients=(VERIFIED_ACCOUNT["id"], DEMO_ACCOUNT_ID)
)

SETH_ACCOUNT["generator"] = MessageFactory(
    "4", datetime(2017, 6, 1), recipients=(SETH_ACCOUNT["id"], DEMO_ACCOUNT_ID)
)


def account_message_gen(account):
    yield account["generator"].create_message(
        DEMO_ACCOUNT_ID,
        "This is a simulated DM conversation with the "
        + account["handle"]
        + " account to show how DMs with specific users can be displayed.",
    )
    if account is SETH_ACCOUNT:
        seth_gif = SETH_ACCOUNT["generator"].create_message(
            SETH_ACCOUNT["id"], "https://t.co/sethgif"
        )
        seth_gif["urls"] = [
            {
                "url": "https://t.co/sethgif",
                "expanded": "https://twitter.com/messages/media/1",
                "display": "pic.twitter.com/kuJj6jjLhJ",
            }
        ]
        seth_gif["mediaUrls"] = ["https://video.twimg.com/dm_gif/1/seth.mp4"]
        seth_gif["id"] = "1000000000000"
        yield seth_gif
    for i in range(1, 51):
        yield account["generator"].create_message(
            account["id"] if i % 2 == 1 else DEMO_ACCOUNT_ID, f"Message {i}"
        )


verified_messages = list(account_message_gen(VERIFIED_ACCOUNT))

seth_messages = list(account_message_gen(SETH_ACCOUNT))

accounts = verified_messages + seth_messages