AN OVERVIEW OF THE PROJECT AND ITS WORKING:

The project uses two databases: MySQL and MongoDB. The SQL architecture consists of 2 tables: users and matches.

The users table stores the following fields: uid, name, elo, is_online, wins, losses, and draws.
The matches table stores: match_id, winner_uid, loser_uid, result, as well as the ELO ratings of both players before and after the game, along with the timestamp of when the game was played.

MongoDB is used to store the binary data of images scraped from the Assignment 2 websites where an image was extractable. The scripts main.py and scraper.py are used to collect and store this data.

Once server.py starts, it initiates the extraction process using MongoDB. The browser then activates the webcam, and the find_closest_match function in the blackbox module is used to identify a match with a tolerance of 0.7. If a match is found, a session cookie is set and the user is marked as online in the SQL database.

All online users from MySQL are present in the lobby when they are on the page. When a user is challenged, a WebSocket room is created using the 2 IDs of the players. This game is then isolated from the remaining players.

If a player leaves the game, the other player is awarded a forfeit. If the game ends, the players can choose to rematch or leave. Reloading the page returns the user to the lobby to play another match against an online opponent.

The system also assumes the same user cannot log in a second time and will not allow them to do so.

The leaderboard reflects the current ELO ratings of the users stored in MySQL.

migration.sql is included only for updating an already existing sql database from previous phases. It is not needed if running schema.sql for the first time.


HOW TO SET UP THE DATABASE:


STEP 0: GETTING THE REPOSITORIES

STEP 0 A: Cloning the repo 

```
git clone <your-repo-link>
cd <repo-folder>
```

STEP 0 B: Run

```
uv sync
```




STEP 1 : PRE-REQUISITES:

STEP 1 A: Install MYSQL (IF NOT):

```
sudo apt install mysql-server
```

STEP 1 B: To start MYSQL:

```
sudo systemctl start mysql
```




STEP 2: To access MySQL, type in terminal:

```
sudo mysql 
```




STEP 3: CREATE THE DATABASE: 

```
CREATE DATABASE project_db;
```

NOTE: Ensure it matches .env however you name it. 




STEP 4: CREATE USER:

One way to do so:

```
CREATE USER 'project_user'@'localhost' IDENTIFIED BY'xxxxxx';
GRANT ALL PRIVILEGES ON project_db.* TO 'project_user'@'localhost';
FLUSHPRIVILEGES;
```

Another way to do so:

```
user: root
password: yourpassword
```




STEP 5: EXIT MYSQL:

to exit:

```
exit;
```




STEP 6: RUNNING THE SCHEMA FILE: 
Ensures you have all the required tables and columns

```
mysql -u project_user -p project_db < schema.sql
```

IF USING ROOT:

```
mysql -u root -p project_db < schema.sql
```




STEP 7: VERIFYING THE SETUP:

STEP 7A: Login:

```
mysql -u project_user -p
```

STEP 7B:

```
USE project_db;
SHOW TABLES;
```

You should be able to see:
users
matches

STEP 7C: Checking structure

```
DESCRIBE users;
```

You should get:
uid
name
is_online
elo_rating
wins
losses
draws


```
DESCRIBE matches;
```

You should get:
```
id
winner_uid
loser_uid  
result
winner_elo_before
loser_elo_before
winner_elo_after
loser_elo_after  
played_at 
```

STEP 8: SETTING UP MONGO DB:

    1. Create a cluster on MongoDB Atlas
    2. Add your IP to Network Access
    3. Copy your connection string 




STEP 9: CONFIGURING .env :

Edit the .env file by adding:
```
MYSQL_HOST=localhost
MYSQL_USER=project_user
MYSQL_PASSWORD=xxxxxxxx
MYSQL_DB=project_db

MONGO_URI=<your-mongodb-uri>
MONGO_DB=iss_images
MONGO_COLLECTION=profile_pictures
```


STEP 10: START BACKEND BY RUNNING:
```
uv sync
uv run python main.py
uv run uvicorn server:app --reload
```
