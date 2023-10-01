# discourse-digger

Discourse digger is a cron job able to fetch discourse posts for multiple DAOs on a daily basis and store them in a database.

#### Design decisions: 
- used insert_or_update queries to facilitate updates and prevent storing duplicates in the db
- store the last value of the before_query_parameter (necessary for pagination) in the database after every fetch
- fetch posts in chronological order

#### Pros:
- Fetching posts in chronological order makes it easy to prevent data gaps
- By setting the lastProcessedId of a DAO to 1 we can fetch the latest discourse data for the posts we already store (i.e number of reads, likes or quotes)
- Maintaining the lastProcessedId offers a seamless update experience if the process is interrupted for any reasons (a runtime error or network issues). The process can be easily resumed later on the next execution of the cron job


> Performance Test result: Processed over 5000 ids in 10 minutes -> 30k-ish ids (Aave's whole forum) in 60 minutes, costing under $0.1 to fully store all Aave's discourse posts

### Prerequisites
- Docker

### How to run
1. Create your own .env file from .env.template and fill it in
2. Run `docker-compose build && docker-compose up`


### Assumptions
This script is meant to gather data which would be later manipulated by a data analyst. 

>Assumption 1: The data analyst might want to include new data points in the future, therefore the database might need to be extended and/or rebuilt from scratch.

Until the MVP stage is reached, the database is likely to suffer plenty of structural changes. For this reason it's important to be able to rebuild it from scratch fast and cheap.

`src/rebuild_db.py` is a script we can use to quickly rebuild the development database when needed.

>Performance Test result: Fetched all Aave's data in around 42 minutes down from an hour.

This is still very slow. The process could be reduced to only a few minutes by running multiple instances in parallel, each one fetching a different range of ids.


> Assumption 2: Discourse API keys authorize read-only access. Assuming this, the API key for each DAO is stored in the database in plain text.


### Scalability, extensions and improvements

1. #### Database

The database structure has been designed to allow integrating multiple DAOs and extending the dataset to other Discourse data (i.e. topics), or on-chain/Snapshot governance data. Posts, Topics and Proposals can be easily linked through the unique composite field daoId_topicId.

2. #### Logging and Alerts

In the future, services like Axiom could process all logging data. They make it easier to trace errors and set up instant alerts for crucial events through webhooks.


3. #### Readability, code structure and naming consistency

As the project expands, adopting a modular structure is advisable to ensure a clean and maintainable codebase. At this juncture, I suggest three modules:

1. `discourse_provider` module: Handles all API interactions.
2. `repository` module: Manages all database interactions.
3. `config` module: Initializes the logger and loads environment variables.

By compartmentalizing these functions into dedicated modules, we enhance readability. This arrangement allows the main cronjob file to focus on high-level business logic, while neatly abstracting away the underlying implementation details.













