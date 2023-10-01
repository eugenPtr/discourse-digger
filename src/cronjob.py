###################################################################################################################################################################################################################
# This approach maintains the latest last processed post id in the database, enabling fetching data in chronological order (that is from oldest to newest).
# Although slower than the other approach, this one is more robust and is suitable to run as a cron job in production.
#
# In the event of runtime errors, this implementation is able to resume fetching data from where it left off when the cron job will run next.
#
# Another advantage is that it enables syncing our db to the latest state of the Discourse data.
# Why would that be needed?
# Let's say we want to know the latest figures of when a post has been liked or quoted. To achieve this we simply need to set the last processed post id to a lower value.
#
# Test result: Going over 5000 ids in 10 minutes -> 30k-ish ids (Aave's whole forum) in 60 minutes
####################################################################################################################################################################################################################
from prisma import Prisma
import requests
from dotenv import load_dotenv
from prisma.models import Dao
from typing import List, Dict, Any, Optional
import time
import schedule
import logging
import os

logger = logging.getLogger(__name__)

# Set the logging level
logger.setLevel(logging.INFO)

# Create a console handler and set its level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter and add it to the console handler
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# Add the console handler to the logger
logger.addHandler(console_handler)

load_dotenv()

def insert_or_update_posts(
    db: Prisma, posts: List[Dict[str, Any]], dao: Dao
) -> int:
    try:
        modified_rows_count = 0
        for post in posts:
            db.post.upsert(
                where={
                    "daoId_discourseId": {"daoId": dao.id, "discourseId": post["id"]}
                },
                data={
                    "create": {
                        "body": post["raw"],
                        "discourseId": post["id"],
                        "topicDiscourseId": post["topic_id"],
                        "author": post["username"],
                        "createdAt": post["created_at"],
                        "views": post["reads"],
                        "dao": {"connect": {"id": dao.id}},
                    },
                    "update": {
                        # Insert here any fields you want to be updated
                        "body": post["raw"],
                        "views": post["reads"],
                    },
                },
            )
            modified_rows_count += 1

        logger.info(
            "Inserted or Updated " + str(modified_rows_count) + " rows in the db"
        )
        return modified_rows_count
    except Exception as e:
        logger.error(f"Error while inserting/updating posts: {str(e)}")
        raise e

def fetch_discourse_posts(
    discourse_api_key: str,
    discourse_username: str,
    api_base_url: str,
    before_query_param: Optional[int] = None,
    max_retries: int = 8,
) -> List[Dict[str, Any]]:
    # Calculate the delay for exponential backoff
    def get_delay(attempt: int) -> float:
        # This will return 2^0, 2^1, 2^2,... seconds
        return 2**attempt

    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(
                api_base_url
                + "/posts.json"
                + (
                    "?before=" + str(before_query_param)
                    if before_query_param != None
                    else ""
                ),
                headers={
                    "User-Api-Key": discourse_api_key,
                    "Api-Username": discourse_username,
                },
            )
            response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

            posts = response.json()["latest_posts"]
            logger.info(
                f"Fetched {len(posts)} posts with before_query_param={before_query_param}"
            )
            if len(posts) > 0:
                logger.info(f'Post ids range: {posts[0]["id"]} - {posts[-1]["id"]}')

            attempt = 0  # Reset the attempt counter on a successful API call

            return posts

        except requests.HTTPError as e:
            logger.error(f"Error fetching posts, attempt {attempt + 1}: {e}")
            attempt += 1
            if attempt < max_retries:
                delay = get_delay(attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                break

    # If we've exhausted all retries and still haven't succeeded, raise an exception
    raise Exception(f"Unable to fetch data from the API after {max_retries} attempts.")


def main() -> None:
    db = Prisma()

    ## If an exception is thrown, the cron job would be executed again later and resume from where it left off.
    try:
        logger.info("Connecting to the database...")
        db.connect()
        logger.info("Connected to the database successfully!")

        logger.info("Starting to fetch discourse data...")

        daos = db.dao.find_many()
        for dao in daos:
            logger.info(f"Updating discourse data for dao: {dao.name}")

            last_processed_post_id = dao.lastProcessedPostId
            no_new_data_count = 0
            old_posts = []

            # Fetch up to 30 results at a time (this is the API limit) in chronological order, starting from the last last processed post id stored in the db
            # The loop stops when the same data gets fetched over multiple consecutive iterations.
            while no_new_data_count < 5:
                logger.info(
                    f"Pagination index: {last_processed_post_id}"
                )  # This is useful for debugging

                # Fetch posts with id < last_processed_post_id
                posts = fetch_discourse_posts(
                    str(dao.discourseApiKey),
                    str(dao.discourseUsername),
                    str(dao.apiBaseUrl),
                    last_processed_post_id,
                )

                if posts == old_posts:
                    no_new_data_count += 1
                else:
                    no_new_data_count = 0

                # Insert new posts or update existing ones
                insert_or_update_posts(db, posts, dao)

                old_posts = posts
                last_processed_post_id += 30

                logger.info("\n")

                # Update the last processed post id in the db. This is useful in case the script crashes and needs to be restarted.
                db.dao.update(
                    where={"id": dao.id}, data={"lastProcessedPostId": last_processed_post_id}
                )

        logger.info("Fetching discourse data finished successfully!")
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
    finally:
        db.disconnect()


schedule.every().day.at(str(os.getenv("TASK_SCHEDULED_TIME"))).do(main) # type: ignore
logger.info("Starting cron job...")

while True:
    schedule.run_pending()
    time.sleep(1)
