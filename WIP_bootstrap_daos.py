############################################################################################
# This is a version more suited for fetching all posts from a discourse forum
# It fetches all posts in chronological order, storing them in the database in batches.
# This approach minimizes the number of database connections, making the whole update faster
############################################################################################
import asyncio
from prisma import Prisma, types
import requests
from dotenv import load_dotenv
from prisma.models import Dao
from typing import List, Dict, Any
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

async def insert_or_update_posts(db: Prisma, posts: List[Dict[str, Any]] , dao: Dao) -> int:
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
                    #Insert here any fields you want to be updated
                    'views': post['reads']
                }
            } 
        )
        modified_rows_count += 1

    logger.info('Inserted or Updated ' + str(modified_rows_count) + ' rows in the db')
    return modified_rows_count

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
    modified_rows_count = await db.post.create_many(data=data_to_insert)
    logger.info('Batch inserted ' + str(modified_rows_count) + ' rows in the db')
    return modified_rows_count
    

def fetch_discourse_posts(discourse_api_key: str, discourse_username: str, api_base_url: str, pagination_index: str) -> List[Dict[str, Any]]:
    response = requests.get(
        api_base_url + '/posts.json?before=' + pagination_index, 
        headers={
            'User-Api-Key': discourse_api_key,
            'Api-Username': discourse_username
        }
    )
    posts = response.json()['latest_posts']
    logger.info('Fetched ' + str(len(posts)) + ' posts')
    if (len(posts) > 0):
        logger.info('Post ids are between ' + str(posts[-1]['id']) + ' and ' + str(posts[0]['id']))

    return posts

async def main() -> None:
    db = Prisma()
    await db.connect()

    daos = await db.dao.find_many()
    # Add to the database all posts that are not already in there
    for dao in daos:
        logger.info('Updating discourse data for dao: ' + dao.name)

        pagination_index = dao.paginationIndex
        no_new_data_count = 0
        old_posts = []

        # Fetch up to 20 results at a time (this is the API limit) in chronological order, starting from the last pagination index stored in the db
        # The loop stops when the same data gets fetched over multiple consecutive iterations
        while (no_new_data_count < 5):
            logger.info("Pagination index: " + str(pagination_index))

            posts = fetch_discourse_posts(str(dao.discourseApiKey), str(dao.discourseUsername), str(dao.apiBaseUrl), str(pagination_index))
            latest_post_in_db = await db.post.find_first(where={'daoId': dao.id, 'discourseId': {'lte': pagination_index}}, order={'discourseId': 'desc'})

            
            #TODO: Filter out discourse posts with their id lte latest_post_in_db.discourseId
            filtered_posts = []
            
            await batch_insert_posts(db, filtered_posts, dao)

            if (posts == old_posts):
                no_new_data_count += 1
            else:
                no_new_data_count = 0

            old_posts = posts
            pagination_index += 20
            
            logger.info('\n')

            await db.dao.update(where={'id': dao.id}, data={'paginationIndex': pagination_index})
            # time.sleep(3)

    await db.disconnect()
    
if __name__ == '__main__':
    asyncio.run(main())
