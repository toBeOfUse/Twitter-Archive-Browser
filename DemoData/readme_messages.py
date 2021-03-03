from DemoData.MessageFactory import MessageFactory
from DemoData.demo_constants import DEMO_ACCOUNT_ID, DEMO_ACCOUNT_USERNAME
from datetime import datetime

readme_factory = MessageFactory("1", datetime.now())

readme = [readme_factory.create_name_update(DEMO_ACCOUNT_ID, "Readme")]

readme_text = """
Hello! Welcome to the demo of the Twitter archive browser.

This app was created to bring the best capabilities of messaging apps like Discord to
DM archives, including conversation sorting and filtering, jumping around by date,
bi-directional infinite scrolling that remembers where you left off if you go forward
and back, bookmarkable links, and full-text search.

No information from your messages ever leaves your computer while using it; the
messages are stored in a local SQLite database. This solution may seem lightweight,
but it has been road-tested with accounts with more than a million messages without a
problem. The backend is written in Python and uses the Tornado library to serve
content via an API, and the frontend is built with React, Redux, and React Router.

This conversation just has these few messages to start things off; if you hit the
home button on the bottom left, you can view all of the prepared conversations and
their metadata. The demo consists of this, a very long conversation consisting of
collected excerpts of public-domain poetry to show how the browser works at scale,
and a few simulated DMs with popular Twitter accounts to show how the data of real
live accounts can be displayed alongside your archives.

Feel free to change around user nicknames and conversation notes to suit your fancy;
also note the conversation and user info pages that you can access and how you can
view and search all messages and messages from a specific user, in addition to
scrolling through conversations.
"""

for p in readme_text.split("\n\n"):
    readme.append(
        readme_factory.create_message(DEMO_ACCOUNT_ID, p.replace("\n", " ").strip())
    )

github_link = readme_factory.create_message(
    DEMO_ACCOUNT_ID,
    "View the source code on Github here: https://t.co/githublinkhere",
)

github_link["urls"] = [
    {
        "url": "https://t.co/githublinkhere",
        "expanded": "https://github.com/toBeOfUse/Twitter-Archive-Browser",
        "display": "github.com/toBeOfUse/twit…",
    }
]

readme.append(github_link)
