from ArchiveAccess.JSONStream import PrefixedJSON, MessageStream
import json
from ArchiveAccess.DBWrite import TwitterDataWriter
from ArchiveAccess.DBRead import TwitterDataReader
from ArchiveAccess.APIServer import ArchiveAPIServer
from pathlib import Path
from tornado.ioloop import IOLoop
import asyncio
import sys
import argparse
import traceback


async def main(data_path: Path, bearer_token: str):
    manifest_path = data_path / "manifest.js"
    with PrefixedJSON(manifest_path) as manifest_file:
        manifest = json.load(manifest_file)
    db_path = Path.cwd() / "db" / Path(manifest["userInfo"]["userName"] + ".db")
    if not db_path.exists():
        db_store = TwitterDataWriter(
            db_path,
            manifest["userInfo"]["userName"],
            manifest["userInfo"]["accountId"],
            bearer_token,
        )
        try:

            def process_file(file_dict, group_dm):
                print(f"processing file {file_dict['fileName']}")
                for message in (
                    s := MessageStream(
                        data_path / file_dict["fileName"].replace("data/", "")
                    )
                ) :
                    db_store.add_message(message, group_dm)
                    if db_store.added_messages % 1000 == 0:
                        print(
                            f"\r{db_store.added_messages:,} total messages added; "
                            + f"{s.percentage:.2f}% of the way through {file_dict['fileName']}",
                            end="",
                        )
                print(
                    f"\r{db_store.added_messages:,} total messages added; "
                    + f"{s.percentage:.2f}% of the way through {file_dict['fileName']}\n"
                )

            for individual_dm_file in manifest["dataTypes"]["directMessages"][
                "files"
            ]:
                process_file(individual_dm_file, False)

            print(
                "added {:,} direct messages from {:,} users across {:,} conversations\n".format(
                    dms := db_store.added_messages,
                    dm_users := db_store.added_users,
                    dm_convos := db_store.added_conversations,
                )
            )

            for group_dm_file in manifest["dataTypes"]["directMessagesGroup"][
                "files"
            ]:
                process_file(group_dm_file, True)

            print(
                "added {:,} group chat messages from {:,} more users across {:,} conversations\n".format(
                    db_store.added_messages - dms,
                    db_store.added_users - dm_users,
                    db_store.added_conversations - dm_convos,
                )
            )

            await db_store.finalize()
        except:
            traceback.print_exc()
            print("was not able to import messages :(")
            db_store.close()
            db_path.unlink()
            sys.exit(1)

        db_store.close()
    else:
        print("found database " + str(db_path))
    return db_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load messages from a Twitter data archive and display "
        "them via a web client."
    )
    parser.add_argument(
        "path_to_data",
        help=r'The path of the "data" folder from your unzipped Twitter data '
        r"archive. This will be something like ../twitterarchive/data or "
        r'"C:/Users/Jim/Downloads/Twitter Archive/data"',
    )
    parser.add_argument(
        "-b",
        "--bearer_token",
        help="A bearer token obtained from the Twitter developer portal; used to "
        "download data on the users that appear in this archive. This can be either "
        "the token itself or a path to a JSON file with a 'bearer_token' field. If "
        "this is not supplied, users will be identified only with numbers (although "
        "you can then go through and give them nicknames for the purposes of "
        "viewing the archive.)",
    )
    parser.add_argument(
        "-pw",
        "--password",
        help="A password that anyone who navigates to the web client will be "
        "required to enter.",
    )
    parser.add_argument(
        "-po",
        "--port",
        type=int,
        default=8008,
        help="The port that your data will be served from. If unsure, ignore this "
        "and just go to the localhost url that appears after starting the program "
        "to view your archive.",
    )
    args = parser.parse_args()

    db_path = ""
    data_path = args.path_to_data

    if Path(args.bearer_token).exists():
        with open(args.bearer_token) as key_file:
            bearer_token = json.load(key_file)["bearer_token"]
    else:
        bearer_token = args.bearer_token

    async def locate_or_create_db():
        global db_path
        db_path = await main(Path(data_path), bearer_token)

    IOLoop.current().run_sync(locate_or_create_db)

    reader = TwitterDataReader(db_path, data_path)
    server = ArchiveAPIServer(
        reader,
        Path(data_path) / "direct_messages_media",
        Path(data_path) / "direct_messages_group_media",
        port=args.port,
        password=args.password,
    )
    server.start()
