import asyncio
from prisma import Prisma
import requests
import json
import os
import sys
from dotenv import load_dotenv
from prisma.models import Dao
from typing import List, Dict, Any

load_dotenv()

async def insert_or_update_posts(db: Prisma, posts: List[Dict[str, Any]] , dao: Dao) -> int:
    modified_rows = 0
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
                    #Insert any fields that need to be updated here
                    'views': post['reads']
                }
            } 
        )
        modified_rows += 1
    return modified_rows

async def main() -> None:
    db = Prisma()
    await db.connect()

    daos = await db.dao.find_many()
    # Add to the database all posts that are not already in there
    for dao in daos:
        print('Updating discourse data for dao: ' + dao.name)

        latest_post_in_db = await db.post.find_first(order={'discourseId': 'desc'})
        latest_post_discourse_id = 0 if latest_post_in_db == None else latest_post_in_db.discourseId

        headers = {
        'User-Api-Key': str(dao.discourseApiKey),
        'Api-Username': str(dao.discourseUsername)
        }
        response = requests.get('https://governance.aave.com/posts.json', headers=headers)
        posts = response.json()['latest_posts']
        modified_rows = await insert_or_update_posts(db, posts, dao)
        
        print("Latest post id fetched from discourse:" + str(posts[0]['id']))
        before_query_param = posts[len(posts)-1]['id'] - 1

        # Fetch all posts until reaching the latest post in the database or until there are no more posts
        while latest_post_discourse_id < before_query_param and len(posts) > 0:
            print("Fetched " + str(len(posts)) + " posts")
            print("Modified " + str(modified_rows) + " rows");
            print("Before query param: " + str(before_query_param))
            response = requests.get('https://governance.aave.com/posts.json?before=' + str(before_query_param), headers=headers)
            posts = response.json()['latest_posts']
            modified_rows = await insert_or_update_posts(db, posts, dao)
            
            before_query_param = posts[len(posts)-1]['id'] - 1

    await db.disconnect()
    
if __name__ == '__main__':
    asyncio.run(main())
