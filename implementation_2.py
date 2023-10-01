###################################################################################################################################################################################################################
#This approach maintains the latest pagination index in the database, enabling fetching data in chronological order (that is from oldest to newest). 
#Although slower than the other approach, this one is more robust and is suitable to run as a cron job in production.
#
#In the event of runtime errors, this implementation is able to resume fetching data from where it left off when the cron job will run next.
#
#Another advantage is that it enables syncing our db to the latest state of the Discourse data. 
# Why would that be needed? 
# Let's say we want to know the latest figures of when a post has been liked or quoted. To achieve this we simply need to set the pagination index to a lower value.
#
#Test result: Going over 5000 ids in 10 minutes -> 30k-ish ids (Aave's whole forum) in 60 minutes
####################################################################################################################################################################################################################
import asyncio
from prisma import Prisma
import requests
from dotenv import load_dotenv
from prisma.models import Dao
from typing import List, Dict, Any, Optional
import time
import logging
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

async def insert_or_update_posts(db: Prisma, posts: List[Dict[str, Any]], dao: Dao) -> int:
    try:
        modified_rows_count = 0
        for post in posts:
            await db.post.upsert(
                where={
                    'daoId_discourseId': {
                        'daoId': dao.id,
                        'discourseId': post['id']
                    }
                },
                data={
                    'create': {
                        'body': post['raw'],
                        'discourseId': post['id'],
                        'topicDiscourseId': post['topic_id'],
                        'author': post['username'],
                        'createdAt': post['created_at'],
                        'views': post['reads'],
                        'dao': {'connect': {'id': dao.id}}},
                    'update': {
                        # Insert here any fields you want to be updated
                        'body': post['raw'],
                        'views': post['reads']
                    }
                }
            )
            modified_rows_count += 1

        logger.info('Inserted or Updated ' + str(modified_rows_count) + ' rows in the db')
        return modified_rows_count
    except Exception as e:
        logger.error(f'Error while inserting/updating posts: {str(e)}')
        raise e

    

# def fetch_discourse_posts(discourse_api_key: str, discourse_username: str, api_base_url: str, pagination_index: str) -> List[Dict[str, Any]]:
#     try:
#         response = requests.get(
#             api_base_url + '/posts.json?before=' + pagination_index,
#             headers={
#                 'User-Api-Key': discourse_api_key,
#                 'Api-Username': discourse_username
#             }
#         )
#         response.raise_for_status()  # Raise an exception if the response status code indicates an error

#         posts = response.json()['latest_posts']
#         logger.info('Fetched ' + str(len(posts)) + ' posts')
#         if len(posts) > 0:
#             logger.info('Post ids are between ' + str(posts[-1]['id']) + ' and ' + str(posts[0]['id']))

#         return posts
#     except requests.exceptions.RequestException as e:
#         logger.error(f'Error while fetching discourse posts: {str(e)}')
#         raise e

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

    ## TODO: Put the logic below inside a cron job that runs every X minutes/hours
    ## If an exception is thrown, the cron job would be executed again later and resume from where it left off.
    try:
        await db.connect()

        logger.info('Starting to fetch discourse data...')

        daos = await db.dao.find_many()
        for dao in daos:
            logger.info(f'Updating discourse data for dao: {dao.name}')

            pagination_index = dao.paginationIndex
            no_new_data_count = 0
            old_posts = []

            # Fetch up to 30 results at a time (this is the API limit) in chronological order, starting from the last pagination index stored in the db
            # The loop stops when the same data gets fetched over multiple consecutive iterations.
            while no_new_data_count < 5:
                logger.info(f"Pagination index: {pagination_index}") # This is useful for debugging

                # Fetch posts with id < pagination_index
                posts = fetch_discourse_posts(str(dao.discourseApiKey), str(dao.discourseUsername), str(dao.apiBaseUrl), pagination_index)

                if posts == old_posts:
                    no_new_data_count += 1
                else:
                    no_new_data_count = 0

                # Insert new posts or update existing ones
                await insert_or_update_posts(db, posts, dao)

                old_posts = posts
                pagination_index += 30

                logger.info('\n')

                # Update the pagination index in the db. This is useful in case the script crashes and needs to be restarted.
                await db.dao.update(where={'id': dao.id}, data={'paginationIndex': pagination_index})
        
        logger.info('Fetching discourse data finished successfully!')
    except Exception as e:
        logger.error(f'Error in main function: {str(e)}')
    finally:
        await db.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
