# discourse-digger

Discourse digger is a script which fetches discourse posts for multiple DAOs and stores them in a database

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
- Run `main.py` to start fetching posts from discourse

### Assumptions and design decisions
This script is meant to gather data which would be later manipulated by a data analyst. 

>Assumption 1: The data analyst might want to include new data points in the future, therefore the database might need to be extended and/or rebuilt from scratch.

Until the MVP stage is reached, the database is likely to suffer plenty of changes. For this reason it's important to be able to rebuild it from scratch fast and cheap.

The main script (`main.py`) was able to fetch and store all the posts from Aave's Discourse (around 30k posts on Sept 29th 2023) in around 1 hour, costing less than $0.50. The test was made having deployed a Postgresql db and the script to Railway.

The current implementation prioritizes robustness over speed. In case a spontaneous error arises during execution, it is able to resume fetching data in the next run of the cron job, without skipping any of it. To facilitate this, posts are fetched in chronological order and a pagination index is maintained in the database.

> Design choice 1: Fetch and store posts in chronological order, maintaining a pagination index in the database, in order to overcome database or API failures.

Another advantage of this approach is that we can reset the pagination index back to 1 if we want to update all the posts with the latest edits, number of views, etc.

In order to speed up bootstraping the discord data for a DAO, an alternative approach could be used. By fetching posts in reverse chronological order and storing data in batches could reduce the bootstrapping time required for Aave (one of the DAOs with the highest activity on Discourse) to 20 minutes.

The two implementations could go hand in hand: the latter could be run on demand to rebuild the db from scratch / add data for a new DAO, while the former could continously run in production to fetch the latest data in a reliable manner.

> Assumption 2: Discourse API keys authorize read-only access. Assuming this, the API key for each DAO is stored in the database in plain text.




### Scalability, extensions and improvements

1. Database
- The database structure allows integrating multiple DAOs and extending the dataset to include other Discourse data, such as topics, or onchain/Snapshot governance data. Posts, Topics and Proposals can be easily linked through the unique composite field daoId_topicId which can be referenced by each table.

2. Logging and Alerts
- In the future, all the logging data could be consumed by services like Axiom, which facilitate tracing errors and setting up alerts through webhooks for critical events you'd want to know about as soon as they occur.

3. Scheduling
- Although this isn't included in the script, a sensible next step would be to schedule these tasks to run every X minutes / hours











