import discord 
import requests
import datetime
import asyncio
import time
import json

with open('config.json') as f:
    config = json.load(f)

BOT_TOKEN = config['DISCORD_TOKEN']
PANDASCORE_TOKEN = config['PANDASCORE_TOKEN'] 

indicator = ">"
channels = {}

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    global indicator
    if message.author == client.user:
        return

    print(f'command executed by {message.author}.')
    print(f'content: {message.content}')

    if message.content.startswith(indicator + 'help'):
        embed = discord.Embed(title="Commands", color=0xFF00FF)
        if message.content.startswith(indicator + 'help'):
            embed.add_field(name=f"`{indicator}help`", value="Display this help message.", inline=False)
            embed.add_field(name=f"`{indicator}search` **`<game name>`**", value="Search for eSport matches for the specified game.", inline=False)
        if message.author.guild_permissions.administrator:
            embed.add_field(name=f"`{indicator}setindicator` **`<new indicator>`**", value="Change the command indicator (admin only).", inline=False)
            embed.add_field(name=f"`{indicator}setchannel` **`<game name>`**", value="Set the current channel to receive updates for the specified game (admin only).", inline=False)
            embed.add_field(name=f"`{indicator}unsetchannel` **`<game name>`**", value="Unset the channel for the specified game (admin only).", inline=False)
        await message.channel.send(embed=embed)

    if message.content.startswith(indicator + 'setchannel'):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You don't have the necessary permissions to use this command.")
            return
        game_name = message.content.split(' ', 1)[1]
        channels[game_name] = message.channel.id
        await message.channel.send(f'Set this channel ({message.channel.name}) for updates on {game_name}.')

    if message.content.startswith(indicator + 'unsetchannel'):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You don't have the necessary permissions to use this command.")
            return
        game_name = message.content.split(' ', 1)[1]
        if game_name in channels:
            del channels[game_name]
            await message.channel.send(f'Unset this channel for updates on {game_name}.')
        else:
            await message.channel.send(f'No channel set for {game_name}.')

    if message.content.startswith(indicator + 'setindicator'):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You don't have the necessary permissions to use this command.")
            return
        new_indicator = message.content.split(' ', 1)[1]
        indicator = new_indicator
        await message.channel.send(f'Command indicator changed to: {indicator}')

    if message.content.startswith(indicator + 'search'):
        game_name = message.content.split(' ', 1)[1]
        await message.channel.send(f'Searching for {game_name}...')
        results = search_game(game_name)
        await message.channel.send(results)

def search_game(game_name):
    url = f"https://api.pandascore.co/videogames?search[name]={game_name}&token={PANDASCORE_TOKEN}"
    response = requests.get(url)
    games = response.json()
    
    if len(games) == 0:
        return "No games found."
    else:
        game_id = games[0]['id']
        match_url = f"https://api.pandascore.co/matches?filter[videogame_id]={game_id}&token={PANDASCORE_TOKEN}"
        match_response = requests.get(match_url)
        matches = match_response.json()
        
        if len(matches) == 0:
            return f"No matches currently in progress for {games[0]['name']}."
        else:
            match_info = f"Current matches for {games[0]['name']}:\n"
            for match in matches:
                match_info += f"- {match['name']} (Status: {match['status']})\n"
            return match_info
        
async def search_and_send_games(game_name):
    url = f"https://api.pandascore.co/videogames?search[name]={game_name}&token={PANDASCORE_TOKEN}"
    response = requests.get(url)
    games = response.json()

    if len(games) == 0:
        return "No games found."
    else:
        game_id = games[0]['id']
        match_url = f"https://api.pandascore.co/matches?filter[videogame_id]={game_id}&token={PANDASCORE_TOKEN}"
        match_response = requests.get(match_url)
        matches = match_response.json()

        if len(matches) == 0:
            return f"No matches currently in progress for {games[0]['name']}."
        else:
            match_info = f"Current matches for {games[0]['name']}:\n"
            for match in matches:
                match_info += f"- {match['name']} (Status: {match['status']})\n"

            if game_name in channels:
                channel_id = channels[game_name]
                channel = client.get_channel(channel_id)
                if channel:
                    await channel.send(match_info)
                else:
                    return "Error: Channel not found."
            return match_info

client.run(BOT_TOKEN)