######################################################
# This script is used to add a new DAO to the database
######################################################

import asyncio
from prisma import Prisma
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

################################################################
# Edit .env and set the following variables 
################################################################
DAO_NAME = 'Aave'
PAGINATION_INDEX = 1
API_BASE_URL = 'https://governance.aave.com'
DISCOURSE_API_KEY = str(os.getenv('DISCOURSE_API_KEY'))
DISCOURSE_USERNAME = str(os.getenv('DISCOURSE_USERNAME'))

async def main() -> None:
    db = Prisma()
    await db.connect()

    dao = await db.dao.create({
        'name': DAO_NAME,
        'discourseApiKey': DISCOURSE_API_KEY,
        'discourseUsername': DISCOURSE_USERNAME,
        'paginationIndex': PAGINATION_INDEX,
        'apiBaseUrl': API_BASE_URL
    })

    assert dao is not None

    await db.disconnect()
    

asyncio.run(main())
