# Hackathon
Discord Tournament Management Bot

#### Description
The aim of this project was to create a Discord bot capable of managing a tournament, whether personal or popular. The bot was to be developed in 4 days.

### Features
Tournament creation and management
Participant registration
Score and match tracking
Results announcement
### Requirements
Python 3.8 or higher
Discord API key
Python libraries: discord.py, networkx, matplotlib
### Installation
1.clone the repository :
Copy code
git clone https://github.com/votre-utilisateur/votre-depot.git
cd your-depot

2.create a virtual environment and activate it:

Copy the code:
- python -m venv venv
- source venv/bin/activate # On Windows: venv\Scripts\activate

3) Install dependencies:

Copy the code :
- pip install -r requirements.txt

4.configure the bot with your Discord API key:

Open the config.json file and add your Discord API key:

Copy the code:

- {
    “DISCORD_TOKEN”: “your token”,
    “PANDASCORE_TOKEN”: “your token”.
}

### Usage
Launch the bot:

Copy the code:
- python bot_tournament.py
Invite the bot to your Discord server and start managing your tournament!

### Project structure
- bot_tournament.py : Main script for the Discord bot
- config.json: configuration file containing the Discord API key
- README.md: Project documentation

