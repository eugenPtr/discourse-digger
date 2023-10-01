# discourse-digger

Discourse digger is a script which fetches discourse posts for multiple DAOs and stores them in a database.

This repo contains two different implementations which can be used for different purposes.

The performance of both implementations has been tested by deploying a PostgreSQL db and the two scripts to the cloud, then observing the time needed to fetch and store data from Aave's discourse.

#### `implementation_1.py`

This approach fetches all posts from newest to oldest, storing them in the database in batches.

This version is suitable for fetching all posts from a discourse forum when bootstrapping and empty database or when integrating a new discourse forum.

>Test result: Going over 5000 ids in 7 minutes -> 30k-ish ids (Aave's whole forum) in 42 minutes

A future improvement could be running multiple instances of this script in parallel, each one fetching a different range of ids.

#### `implementation_2.py`

This approach maintains the latest pagination index in the database, enabling fetching data in chronological order (that is from oldest to newest). 

Although slower than the other approach, this one is more robust and is suitable to run as a cron job in production.

In the event of runtime errors, this implementation is able to resume fetching data from where it left off when the cron job will run next.

Another advantage is that it enables syncing our db to the latest state of the Discourse data. Why would that be needed? Let's say we want to know the latest figures of when a post has been liked or quoted. To achieve this we simply need to set the pagination index to a lower value.

> Test result: Going over 5000 ids in 10 minutes -> 30k-ish ids (Aave's whole forum) in 60 minutes

### Prerequisites
- Create an account on the discourse server you want to fetch data from
- Use the following website to generate an API Key
https://observablehq.com/@beanow/generate-user-api-key-for-discourse


### How to set up
1. Run `pip3 install -r requirements.txt` to install dependencies
2. create your own .env file from .env.template and fill it in
3. Run `prisma db push` to create the db schema in the db connected to the script
4. Open `dao_seed.py` and set the variables below the imports
5. Run `python3 dao_seed.py` in order to add a DAO to the database

### How to run
- You can use `pyright` to run a static type check
- Run either `python3 implementation_1.py` or `python3 implementation_2.py` to start fetching posts from discourse
- If you'd like to deploy any of the two implementations to a server / cloud platform using Docker, copy the desired implementation into `main.py` for the Docker image to be created

### Assumptions and design decisions
This script is meant to gather data which would be later manipulated by a data analyst. 

>Assumption 1: The data analyst might want to include new data points in the future, therefore the database might need to be extended and/or rebuilt from scratch.

Until the MVP stage is reached, the database is likely to suffer plenty of structural changes. For this reason it's important to be able to rebuild it from scratch fast and cheap.

> Assumption 2: Discourse API keys authorize read-only access. Assuming this, the API key for each DAO is stored in the database in plain text.


### Scalability, extensions and improvements

1. Database
- The database structure allows integrating multiple DAOs and extending the dataset to include other Discourse data, such as topics, or onchain/Snapshot governance data. Posts, Topics and Proposals can be easily linked through the unique composite field daoId_topicId which can be referenced by each table.

2. Logging and Alerts
- In the future, services like Axiom could process all logging data. They make it easier to trace errors and set up instant alerts for crucial events through webhooks.

3. Scheduling
- A sensible next step would be to make implementation_2.py part of a cron job that would run every X minutes/hours

4. Readability, code structure and naming consistency
- You might notice that both implementations use the same function to fetch posts from discourse. This should be extracted into a separate module to remove code duplication
- Another aspect is that the pagination_index and before_query_parameter refer to the same thing. This was me playing with different names in different scripts and a future version should use consistent naming. 
- The variable names and overall code readability can and should be improved. Although this time I chose to focus on implementing and testing different algorithms that get the job done efficiently, I value code cleanliness a lot and I am not satisfied with the current looks of it.













