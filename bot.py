import discord 
import asyncio
import json
import aiohttp
import sqlite3

with open('config.json') as f:
    config = json.load(f)

conn = sqlite3.connect('database.sqlite')
c = conn.cursor()

BOT_TOKEN = config['DISCORD_TOKEN']
PANDASCORE_TOKEN = config['PANDASCORE_TOKEN'] 

channels = {}
f = {}
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

    server_ids = [row[0] for row in c.execute('SELECT serverid FROM SERVER_DATA').fetchall()]
    if message.guild.id not in server_ids:
        c.execute('INSERT INTO SERVER_DATA (serverid, prefix) VALUES (?, ?)', (message.guild.id, indicator))
        conn.commit()
    print(f'command received from {message.guild.id}.\ncommand executed by {message.author}.\ncommand executed in {message.channel}.\ncommand content: {message.content}')

    indicator = c.execute('SELECT prefix FROM SERVER_DATA WHERE serverid = ?', (message.guild.id,)).fetchone()[0]
    if message.content.startswith(indicator + 'help'):
        embed = discord.Embed(title="Commands", color=0xFF00FF)
        embed.add_field(name=f"`{indicator}help`", value="Display this help message.", inline=False)
        embed.add_field(name=f"`{indicator}search` **`<game name>`**", value="Search for eSport matches for the specified game.", inline=False)
        if message.author.guild_permissions.administrator:
            embed.add_field(name=f"`{indicator}setindicator` **`<new indicator>`**", value="Change the command indicator (admin only).", inline=False)
            embed.add_field(name=f"`{indicator}setchannel`", value="Set the current channel to receive updates for the specified game (admin only).", inline=False)
            embed.add_field(name=f"`{indicator}unsetchannel`", value="Unset the channel for the specified game (admin only).", inline=False)
        await message.channel.send(embed=embed)

    elif message.content.startswith(indicator + 'setchannel'):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You don't have the necessary permissions to use this command.")
            return

        supported_games = await get_supported_games()
        view = discord.ui.View()
        view.add_item(GameSelect(supported_games))
        await message.channel.send('Select a game to receive updates on:', view=view)

    elif message.content.startswith(indicator + 'unsetchannel'):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You don't have the necessary permissions to use this command.")
            return
        game_name = message.content.split(' ', 1)[1]
        if game_name in channels:
            del channels[game_name]
            await message.channel.send(f'Unset this channel for updates on {game_name}.')
        else:
            await message.channel.send(f'No channel set for {game_name}.')

    elif message.content.startswith(indicator + 'setindicator'):
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You don't have the necessary permissions to use this command.")
            return
        new_indicator = message.content.split(' ', 1)[1]
        indicator = new_indicator
        c.execute('UPDATE SERVER_DATA SET prefix = ? WHERE serverid = ?', (indicator, message.guild.id))
        conn.commit()
        await message.channel.send(f'Command indicator changed to: {indicator}')

    elif message.content.startswith(indicator + 'search'):
        game_name = message.content.split(' ', 1)[1]
        await message.channel.send(f'Searching for {game_name}...')
        results = await search_game(game_name)
        await message.channel.send(results)

async def search_game(game_name):
    url = f"https://api.pandascore.co/videogames?search[name]={game_name}&token={PANDASCORE_TOKEN}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            games = await response.json()
    
    if len(games) == 0:
        return "No games found."
    game_id = games[0]['id']
    match_url = f"https://api.pandascore.co/matches?filter[videogame_id]={game_id}&token={PANDASCORE_TOKEN}"
    async with aiohttp.ClientSession() as session:
        async with session.get(match_url) as match_response:
            matches = await match_response.json()
    if len(matches) == 0:
        return f"No matches currently in progress for {games[0]['name']}."
    match_info = f"Current matches for {games[0]['name']}:\n"
    for match in matches:
        match_info += f"- {match['name']} (Status: {match['status']})\n"
    return match_info
        
async def get_supported_games():
    url = f"https://api.pandascore.co/videogames?token={PANDASCORE_TOKEN}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            games = await response.json()
    return [game['name'] for game in games]

class GameSelect(discord.ui.Select):
    def __init__(self, games):
        options = [discord.SelectOption(label=game, value=game) for game in games]
        super().__init__(placeholder='Select a game', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        game_name = self.values[0]
        server_id = interaction.guild.id
        channel_id = interaction.channel.id

        conn = sqlite3.connect('database.sqlite')
        c = conn.cursor()

        c.execute('INSERT INTO GAME_DATA(serverid, channelid, game)VALUES (?, ?, ?)', (server_id, channel_id, game_name))

        conn.commit()
        conn.close()

        await interaction.response.send_message(f'Set this channel for updates on {game_name}.')
        client.loop.create_task(send_match_updates(game_name, interaction.channel.id))

async def get_match_info(game_name):
    url = f"https://api.pandascore.co/matches?filter[videogame_id]={game_name}&token={PANDASCORE_TOKEN}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            matches = await response.json()
    return matches

class VoteButton(discord.ui.Button):
    def __init__(self, label):
        super().__init__(style=discord.ButtonStyle.secondary, label=label)
        self.votes = 0

    async def callback(self, interaction: discord.Interaction):
        self.votes += 1
        self.label = f"{self.label.split(' ')[0]} ({self.votes} votes)"
        await interaction.response.edit_message(view=self.view)

async def send_match_updates(game_name, channel_id):
    while True:
        matches = await get_match_info(game_name)
        if matches:
            channel = client.get_channel(channel_id)
            for match in matches:
                if 'opponents' in match and len(match['opponents']) > 0 and 'opponent' in match['opponents'][0]:
                    team1 = match['opponents'][0]['opponent']['name']
                    team2 = match['opponents'][1]['opponent']['name']
                    embed = discord.Embed(title=f"Un nouveau match commence: {match['name']}", color=discord.Color.blue())
                    embed.add_field(name="Équipe 1", value=team1, inline=True)
                    embed.add_field(name="Équipe 2", value=team2, inline=True)
                    view = discord.ui.View()
                    view.add_item(VoteButton(label=f"{team1} (0 votes)"))
                    view.add_item(VoteButton(label=f"{team2} (0 votes)"))
                    await channel.send(embed=embed, view=view)
        await asyncio.sleep(60)

async def check_match_updates():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()

    rows = c.execute('SELECT server_id, channel_id, game_name FROM game_channels').fetchall()

    for row in rows:
        server_id, channel_id, game_name = row
        server = client.get_guild(server_id)
        channel = server.get_channel(channel_id)
        await send_match_updates(game_name, channel)

    conn.close()
client.run(BOT_TOKEN)