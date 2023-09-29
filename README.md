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