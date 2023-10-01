######################################################
# This script is used to add a new DAO to the database
######################################################

from prisma import Prisma
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

DISCOURSE_API_KEY = str(os.getenv("DISCOURSE_API_KEY"))
DISCOURSE_USERNAME = str(os.getenv("DISCOURSE_USERNAME"))

DAO_NAME = str(os.getenv("DAO_NAME"))
LAST_PROCESSED_POST_ID = int(os.getenv("LAST_PROCESSED_POST_ID", 1))
API_BASE_URL = str(os.getenv("API_BASE_URL"))


def main() -> None:
    db = Prisma()
    db.connect()

    existing_dao = db.dao.find_unique(where={"name": DAO_NAME})

    if existing_dao is not None:
        logger.info(f"DAO with name {DAO_NAME} already exists in the database")
        return

    new_dao = db.dao.create(
        {
            "name": DAO_NAME,
            "discourseApiKey": DISCOURSE_API_KEY,
            "discourseUsername": DISCOURSE_USERNAME,
            "lastProcessedPostId": LAST_PROCESSED_POST_ID,
            "apiBaseUrl": API_BASE_URL,
        }
    )

    assert new_dao is not None

    db.disconnect()


main()
