########################################################################################################################
# This script is used to bootstrap a new DAO with all discourse posts up to BEFORE_POST_ID
########################################################################################################################

import asyncio
from prisma import Prisma
import requests
import os
from dotenv import load_dotenv
from prisma.models import Dao
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

load_dotenv()

################################################################
# Edit .env and change the following variables 
################################################################
DAO_NAME = 'Aave'
BEFORE_POST_ID = 36300
DISCOURSE_API_KEY = str(os.getenv('DISCOURSE_API_KEY'))
DISCOURSE_USERNAME = str(os.getenv('DISCOURSE_USERNAME'))

async def insert_or_update_posts(db: Prisma, posts: List[Dict[str, Any]] , dao: Dao) -> int:
    modified_rows = 0
    for post in posts:
        post_id = post['id']
        topic_id = post['topic_id']
        username = post['username']
        post_body = post['raw']
        post_reads = post['reads']
        post_date = post['created_at']
        try:
            await db.post.upsert(
                where={
                    'daoId_discourseId': {
                        'daoId': dao.id,
                        'discourseId': post_id
                    }
                },
                data={
                    'create': {
                        'body': post_body,
                        'discourseId': post_id,
                        'topicDiscourseId': topic_id,
                        'author': username,
                        'createdAt': post_date,
                        'views': post_reads,
                        'dao': {'connect': {'id': dao.id}}},
                    'update': {
                        #Insert any fields that need to be updated here
                        'views': post_reads
                    }
                } 
            )
            modified_rows += 1
        except Exception as e:
            logger.error(f'Error inserting post {post_id} - {e}')
    return modified_rows

async def main() -> None:
    db = Prisma()
    await db.connect()

    dao = await db.dao.create({
        'name': DAO_NAME,
        'discourseApiKey': DISCOURSE_API_KEY,
        'discourseUsername': DISCOURSE_USERNAME
    })

    assert dao is not None
    
    print('Bootstrapping discourse data for dao: ' + dao.name)

    headers = {
    'User-Api-Key': str(dao.discourseApiKey),
    'Api-Username': str(dao.discourseUsername)
    }
    
    before_query_param = BEFORE_POST_ID

    # Fetch all posts before the specified post id
    while True:
        print("Before query param: " + str(before_query_param))

        response = requests.get('https://governance.aave.com/posts.json?before=' + str(before_query_param), headers=headers)
        posts = response.json()['latest_posts']
        print("Fetched " + str(len(posts)) + " posts")
        if len(posts) == 0:
            print("Job done!")
            break

        modified_rows = await insert_or_update_posts(db, posts, dao)
        print("Modified " + str(modified_rows) + " rows")
        
        before_query_param = posts[len(posts)-1]['id'] - 1
        

    await db.disconnect()
    

asyncio.run(main())
