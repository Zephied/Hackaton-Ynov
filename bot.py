import discord
import requests
import datetime
import asyncio
import time


BOT_TOKEN = ""
PANDASCORE_TOKEN = ""
indicator = ">"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(indicator + 'help'):
        await message.channel.send('Commands: \n>help\n>search <game name>')

    if message.content.startswith(indicator + 'search'):
        game_name = message.content.split(' ', 1)[1]
        await message.channel.send(f'Searching for {game_name}...')
        await message.channel.send(search_game(game_name))