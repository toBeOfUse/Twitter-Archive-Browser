from DemoData.MessageFactory import MessageFactory
from datetime import datetime
from DemoData.demo_constants import DEMO_ACCOUNT_ID, VERIFIED_ACCOUNT, SETH_ACCOUNT

VERIFIED_ACCOUNT["generator"] = MessageFactory(
    "3", datetime(2015, 6, 1), recipients=(VERIFIED_ACCOUNT["id"], DEMO_ACCOUNT_ID)
)

SETH_ACCOUNT["generator"] = MessageFactory(
    "4", datetime(2017, 6, 1), recipients=(SETH_ACCOUNT["id"], DEMO_ACCOUNT_ID)
)


def account_message_gen():
    for account in [VERIFIED_ACCOUNT, SETH_ACCOUNT]:
        yield account["generator"].create_message(
            DEMO_ACCOUNT_ID,
            "This is a simulated DM conversation with the "
            + account["handle"]
            + " account to show how DMs with specific users can be displayed.",
        )
        for i in range(1, 51):
            yield account["generator"].create_message(
                account["id"] if i % 2 == 1 else DEMO_ACCOUNT_ID, f"Message {i}"
            )


accounts = account_message_gen()