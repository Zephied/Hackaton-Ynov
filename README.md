# Discord Bot README

## Description
This Discord bot provides information on eSports matches, teams, and players using the PandaScore API. It supports commands for searching games, teams, and players, setting/unsetting channels to receive game updates, and changing command prefixes.

### Prerequisites
Python 3.6+
discord.py
aiohttp
requests
sqlite3

* [![Python][Python]][Python-url]
* [![Discord][Discord]][Discord-url]
* [![aiohttp][aiohttp]][aiohttp-url]
* [![requests][requests]][requests-url]
* [![sqlite3][sqlite3]][sqlite3-url]


### Setup

**Install the required libraries:**

_sh_
```
pip install discord.py aiohttp request
```

**Create a config.json file in the root directory with the following structure:**

_json_
```
{
    "DISCORD_TOKEN": "your_discord_bot_token",
    "PANDASCORE_TOKEN": "your_pandascore_api_token"
}
```
**Create and initialize the SQLite database :**

 _sql_ 
```
-- database.sqlite
CREATE TABLE SERVER_DATA (
    serverid INTEGER PRIMARY KEY,
    prefix TEXT
);
`
CREATE TABLE GAME_DATA (
    serverid INTEGER,
    channelid INTEGER,
    game TEXT,
    PRIMARY KEY (serverid, channelid, game)
);
```
**Running the Bot**
**Run the bot script using Python:**

_sh_
```
python bot.p
```

### Commands

**General Commands**

<prefix>help: **Display the help message with all available commands.**
<prefix>search <game name>: **Search for eSport matches for the specified game.**
<prefix>team <team name>: **Search for eSport teams for the specified team name.**
<prefix>player <player name>: **Search for eSport players for the specified player name.**


**Admin Commands**

<prefix>setprefix <new prefix>: **Change the command prefix (admin only).**
<prefix>setchannel: **Set the current channel to receive updates for a specified game (admin only).**
<prefix>unsetchannel: **Unset the channel for a specified game (admin only).**

### Code Overview

**Initialization:**

1) Loads configuration from config.json.
2) Connects to the SQLite database.
3) Sets up the Discord bot with required intents.

**Event Handlers:**

on_ready: **Confirms bot connection to Discord.**
on_message: **Handles incoming messages and executes corresponding commands.**

## Commands Implementation :

help: **Provides a list of commands and their descriptions.**

setprefix: **Changes the command prefix for the server.**

setchannel and unsetchannel: **Manage channels for receiving game updates.**

search: **Searches for eSport matches based on the game name.**

team: **Searches for teams based on the team name.**

player: **Searches for players based on the player name.**


## Helper Functions :

search_game: **Searches for games using the PandaScore API.**

get_supported_games: **Fetches the list of supported games from PandaScore API.**

get_match_info: **Retrieves match information for a specific game.**

send_match_updates: **Sends match updates to the specified channel.**

check_match_updates: **Periodically checks for match updates.**

search_team: **Searches for teams using the PandaScore API.**

search_player: **Searches for players using the PandaScore API.**

**UI Components:**

GameSelect: **Dropdown for selecting a game to receive updates.**

GameUnselect: **Dropdown for unselecting a game to stop receiving updates.**

VoteButton: **Button for voting on match predictions.**

## Info

**Make sure the bot has the necessary permissions in your Discord server, especially for reading messages, sending messages, and managing channels.
Ensure that your config.json file contains valid tokens for the Discord bot and PandaScore API.**



[Python]: https://img.shields.io/badge/Python-grey?style=for-the-badge&logo=python&logoColor=blue
[Python-url]: https://www.python.org/

[Discord]: https://img.shields.io/badge/Discord-black?style=for-the-badge&logo=discord&logoColor=lightgrey
[Discord-url]: https://discord.com/

[aiohttp]: https://img.shields.io/badge/aiohttp-blue?style=for-the-badge&logo=aiohttp&logoColor=white
[aiohttp-url]: https://docs.aiohttp.org/en/stable/


[requests]: https://img.shields.io/badge/Requests-skyblue?style=for-the-badge&logo=python&logoColor=yellow
[requests-url]: https://pypi.org/project/requests/

[sqlite3]: https://img.shields.io/badge/SQLite-purple?style=for-the-badge&logo=sqlite&logoColor=blue
[sqlite3-url]: https://www.sqlite.org/index.html