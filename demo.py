from DemoData.readme_messages import readme
from DemoData.poetry_messages import poetry
from DemoData.demo_constants import DEMO_ACCOUNT_ID, DEMO_ACCOUNT_USERNAME
from pathlib import Path
from tornado.ioloop import IOLoop
from ArchiveAccess.DBWrite import TwitterDataWriter
from ArchiveAccess.DBRead import TwitterDataReader
from ArchiveAccess.APIServer import ArchiveAPIServer
import argparse
from typing import Final
import json

db_path: Final = Path.cwd() / "db" / (DEMO_ACCOUNT_USERNAME + ".db")


async def create_demo_db():
    db_store = TwitterDataWriter(
        db_path, DEMO_ACCOUNT_USERNAME, DEMO_ACCOUNT_ID, "", automatic_overwrite=True
    )
    for message in readme:
        db_store.add_message(message, True)
    print("readme messages added")

    for message in poetry:
        db_store.add_message(message, True)
    print("poetry messages added")

    await db_store.finalize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create and serve a demo of simulated messages."
    )
    parser.add_argument(
        "-b",
        "--bearer_token",
    )
    parser.add_argument(
        "-pw",
        "--password",
    )
    parser.add_argument(
        "-po",
        "--port",
        type=int,
        default=8008,
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["dev", "single_build", "no_build"],
        default="no_build",
    )

    args = parser.parse_args()

    if args.bearer_token and Path(args.bearer_token).exists():
        with open(args.bearer_token) as key_file:
            bearer_token = json.load(key_file)["bearer_token"]
    else:
        bearer_token = args.bearer_token or None

    media_path = Path.cwd() / "DemoData" / "media"

    IOLoop.current().run_sync(create_demo_db)

    reader = TwitterDataReader(db_path, media_path, media_path)
    server = ArchiveAPIServer(
        reader,
        media_path,
        media_path,
        build_mode=args.mode,
        port=args.port,
        password=args.password,
    )
    server.start()
