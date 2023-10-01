############################################################################################
# This approach fetches all posts from newest to oldest, storing them in the database in batches.

# This version is suitable for fetching all posts from a discourse forum when bootstrapping and empty database or when integrating a new discourse forum.

# Test result: Going over 5000 ids in 7 minutes -> 30k-ish ids (Aave's forum) in 42 minutes
# A future improvement could be running multiple instances of this script in parallel, each one fetching a different range of ids.
############################################################################################
import asyncio
from prisma import Prisma, types
import requests
from dotenv import load_dotenv
from prisma.models import Dao
from typing import List, Dict, Any, Optional
import logging
import time

logger = logging.getLogger(__name__)

# Set the logging level
logger.setLevel(logging.INFO)

# Create a console handler and set its level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter and add it to the console handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add the console handler to the logger
logger.addHandler(console_handler)

load_dotenv()

async def batch_insert_posts(db: Prisma, posts: List[Dict[str, Any]], dao: Dao) -> int:
    data_to_insert: List[types.PostCreateWithoutRelationsInput] = []
    for post in posts:
        data_to_insert.append({
            'body': post['raw'],
            'discourseId': post['id'],
            'topicDiscourseId': post['topic_id'],
            'author': post['username'],
            'createdAt': post['created_at'],
            'views': post['reads'],
            'daoId': dao.id
        })
    modified_rows_count = await db.post.create_many(data=data_to_insert, skip_duplicates=True)
    logger.info(f'Batch inserted {modified_rows_count} posts in the db')
    return modified_rows_count
    

# def fetch_discourse_posts(discourse_api_key: str, discourse_username: str, api_base_url: str, before_query_param: Optional[int] = None) -> List[Dict[str, Any]]:
#     response = requests.get(
#         api_base_url + '/posts.json' + ('?before=' + str(before_query_param) if before_query_param != None else ''),
#         headers={
#             'User-Api-Key': discourse_api_key,
#             'Api-Username': discourse_username
#         }
#     )
#     logger.info(f'Response: {response.status_code}: {response.reason}')
#     posts = response.json()['latest_posts']
#     logger.info(f'Fetched {len(posts)} posts withe before_query_param={before_query_param}')
#     if (len(posts) > 0):
#         logger.info(f'Post ids range: {posts[-1]["id"]} - {posts[0]["id"]}')

#     return posts


def fetch_discourse_posts(discourse_api_key: str, discourse_username: str, api_base_url: str, before_query_param: Optional[int] = None, max_retries: int = 8) -> List[Dict[str, Any]]:
    
    # Calculate the delay for exponential backoff
    def get_delay(attempt: int) -> float:
        # This will return 2^0, 2^1, 2^2,... seconds
        return 2 ** attempt

    attempt = 0
    while attempt < max_retries:
        try:
            response = requests.get(
                api_base_url + '/posts.json' + ('?before=' + str(before_query_param) if before_query_param != None else ''),
                headers={
                    'User-Api-Key': discourse_api_key,
                    'Api-Username': discourse_username
                }
            )
            response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
            
            posts = response.json()['latest_posts']
            logger.info(f'Fetched {len(posts)} posts with before_query_param={before_query_param}')
            if len(posts) > 0:
                logger.info(f'Post ids range: {posts[0]["id"]} - {posts[-1]["id"]}')
            
            attempt = 0  # Reset the attempt counter on a successful API call
            
            return posts

        except requests.HTTPError as e:
            logger.error(f'Error fetching posts, attempt {attempt + 1}: {e}')
            attempt += 1
            if attempt < max_retries:
                delay = get_delay(attempt)
                logger.info(f'Retrying in {delay} seconds...')
                time.sleep(delay)
            else:
                break

    # If we've exhausted all retries and still haven't succeeded, raise an exception
    raise Exception(f"Unable to fetch data from the API after {max_retries} attempts.")


async def main() -> None:
    db = Prisma()

    try:
        logger.info("Attempting to connect to the database...")
        await db.connect()
        logger.info("Connected to the database successfully")

        logger.info("Fetching daos from the database...")
        daos = await db.dao.find_many()

        logger.info("Bootstrapping discourse data for all daos...")
        for dao in daos:
            logger.info(f'Updating discourse data for dao: {dao.name}')

            #Set the before query param to the latest post id on Discourse
            posts = fetch_discourse_posts(dao.discourseApiKey, dao.discourseUsername, dao.apiBaseUrl, None)
            before_query_param: int = posts[0]['id']
            
            # The API returns up to 30 results, but sometimes there is no data in an interval of 30 ids.
            # For this reason we try to fetch data until we get 10 consecutive empty responses.
            no_data_count = 0
            while no_data_count < 10:
                posts = fetch_discourse_posts(dao.discourseApiKey, dao.discourseUsername, dao.apiBaseUrl, before_query_param)
                if (len(posts) > 0):
                    no_data_count = 0
                    await batch_insert_posts(db, posts, dao)
                    before_query_param = posts[-1]['id'] - 1
                else:
                    no_data_count += 1
                    before_query_param -= 30

        logger.info("Done bootstrapping discourse data for all daos")
    except Exception as e:
        logger.error(f'Error while bootstrapping discourse data: {e}')
    finally:                                            
        await db.disconnect()
    
if __name__ == '__main__':
    asyncio.run(main())
