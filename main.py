from ArchiveAccess.JSONStream import PrefixedJSON, MessageStream
import json
from ArchiveAccess.DBWrite import TwitterDataWriter
from pathlib import Path
from tornado.ioloop import IOLoop


async def main(manifest_path):
    base_path = Path(*Path(manifest_path).parts[:-2])
    with PrefixedJSON(manifest_path) as manifest_file:
        manifest = json.load(manifest_file)
    db_store = TwitterDataWriter(
        manifest["userInfo"]["userName"], manifest["userInfo"]["accountId"]
    )

    def process_file(file_dict, group_dm):
        print(f"processing file {file_dict['fileName']}")
        for message in (s := MessageStream(Path(base_path, file_dict["fileName"]))) :
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

    for individual_dm_file in manifest["dataTypes"]["directMessages"]["files"]:
        process_file(individual_dm_file, False)

    print(
        "added {:,} direct messages from {:,} users across {:,} conversations\n".format(
            dms := db_store.added_messages,
            dm_users := db_store.added_users,
            dm_convos := db_store.added_conversations,
        )
    )

    for group_dm_file in manifest["dataTypes"]["directMessagesGroup"]["files"]:
        process_file(group_dm_file, True)

    print(
        "added {:,} group chat messages from {:,} more users across {:,} conversations\n".format(
            db_store.added_messages - dms,
            db_store.added_users - dm_users,
            db_store.added_conversations - dm_convos,
        )
    )

    await db_store.finalize()


if __name__ == "__main__":

    async def test_run():
        await main("../data/manifest.js")

    IOLoop.current().run_sync(test_run)
