import discord 
import asyncio
import requests
import json
import aiohttp
import sqlite3

with open('config.json') as f:
    config = json.load(f)

conn = sqlite3.connect('database.sqlite')
c = conn.cursor()

BOT_TOKEN = config['DISCORD_TOKEN']
PANDASCORE_TOKEN = config['PANDASCORE_TOKEN'] 

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    client.loop.create_task(check_match_updates())

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    server_ids = [row[0] for row in c.execute('SELECT serverid FROM SERVER_DATA').fetchall()]
    if message.guild.id not in server_ids:
        c.execute('INSERT INTO SERVER_DATA (serverid, prefix) VALUES (?, ?)', (message.guild.id, prefix))
        conn.commit()

    prefix = c.execute('SELECT prefix FROM SERVER_DATA WHERE serverid = ?', (message.guild.id,)).fetchone()[0]
    if message.content.startswith(prefix + 'help'):
        embed = discord.Embed(title="Commands", color=0xFF00FF)
        embed.add_field(name=f"`{prefix}help`", value="Display this help message.", inline=False)
        embed.add_field(name=f"`{prefix}team` **`<team name>`**", value="Search for a team.", inline=False)
        embed.add_field(name=f"`{prefix}player` **`<player name>`**", value="Search for a player.", inline=False)
        if message.author.guild_permissions.administrator:
            embed.add_field(name=f"`{prefix}setprefix` **`<new prefix>`**", value="Change the command prefix (admin only).", inline=False)
            embed.add_field(name=f"`{prefix}setchannel`", value="Set the current channel to receive updates for the specified game (admin only).", inline=False)
            embed.add_field(name=f"`{prefix}unsetchannel`", value="Unset the channel for the specified game (admin only).", inline=False)
        await message.channel.send(embed=embed)

    elif message.content.startswith(prefix + 'setchannel'):
        if not message.author.guild_permissions.administrator:
            embed = discord.Embed(title="You don't have the necessary permissions to use this command!", color=0xFF0000)
            await message.channel.send(embed=embed)
            return
        supported_games = await get_supported_games()
        view = discord.ui.View()
        view.add_item(GameSelect(supported_games))
        embed = discord.Embed(title="Select a game to receive updates on:", color=0x00F0F0)
        await message.channel.send(embed=embed, view=view)
    
    elif message.content.startswith(prefix + 'unsetchannel'):
        if not message.author.guild_permissions.administrator:
            embed = discord.Embed(title="You don't have the necessary permissions to use this command!", color=0xFF0000)
            await message.channel.send(embed=embed)
            return
        games = c.execute('SELECT game FROM GAME_DATA WHERE serverid = ? AND channelid = ?', (message.guild.id, message.channel.id)).fetchall()
        if not games:
            embed = discord.Embed(title="This channel is not set to receive updates for any game.", color=0xFF0000)
            await message.channel.send(embed=embed)
            return
        supported_games = await get_supported_games()
        view = discord.ui.View()
        view.add_item(GameUnselect(supported_games, message.guild.id, message.channel.id))
        embed = discord.Embed(title="Select a game to stop receiving updates on:", color=0x00F0F0)
        await message.channel.send(embed=embed, view=view)

    elif message.content.startswith(prefix + 'setprefix'):
        if not message.author.guild_permissions.administrator:
            embed = discord.Embed(title="You don't have the necessary permissions to use this command!", color=0xFF0000)
            await message.channel.send(embed=embed)
            return
        if len(message.content.split(' ')) == 1:
            embed = discord.Embed(title="Please provide a new prefix!", color=0xFF00FF)
            embed.add_field(name="Usage", value=f"`{prefix}setprefix <new prefix>`", inline=False)
            await message.channel.send(embed=embed)
            return
        new_prefix = message.content.split(' ', 1)[1]
        if len(new_prefix) != 1:
            embed = discord.Embed(title="The prefix must be a single character!", color=0xFF00FF)
            embed.add_field(name="Usage", value=f"`{prefix}setprefix <new prefix>`", inline=False)
            await message.channel.send(embed=embed)
            return
        c.execute('UPDATE SERVER_DATA SET prefix = ? WHERE serverid = ?', (new_prefix, message.guild.id))
        conn.commit()
        embed = discord.Embed(title=f'Command prefix changed to: {new_prefix}', color=0x00FF00)
        await message.channel.send(embed=embed)
    
    elif message.content.startswith(prefix + 'team'):
        if len(message.content.split(' ')) == 1:
            embed = discord.Embed(title="Please provide a team name to search for!", color=0xFF00FF)
            embed.add_field(name="Usage", value=f"`{prefix}team <team name>`", inline=False)
            await message.channel.send(embed=embed)
            return
        team_name = message.content.split(' ', 1)[1]
        team_name = message.content.split(' ', 1)[1]
        embeds = await search_team(team_name)
        for embed in embeds:
            await message.channel.send(embed=embed)

    elif message.content.startswith(prefix + 'player'):
        if len(message.content.split(' ')) == 1:
            embed = discord.Embed(title="Please provide a player name to search for!", color=0xFF00FF)
            embed.add_field(name="Usage", value=f"`{prefix}player <player name>`", inline=False)
            await message.channel.send(embed=embed)
            return
        player_name = message.content.split(' ', 1)[1]
        embed = discord.Embed(title=f'Searching for player {player_name}...', color=0xF0F000)
        await message.channel.send(embed=embed)
        embed = await search_player(player_name)
        await message.channel.send(embed=embed)
        
async def get_supported_games():
    url = f"https://api.pandascore.co/videogames?token={PANDASCORE_TOKEN}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            games = await response.json()
    return [game['name'] for game in games]

class GameUnselect(discord.ui.Select):
    def __init__(self, games, server_id, channel_id):
        games = c.execute('SELECT game FROM GAME_DATA WHERE serverid = ? AND channelid = ?', (server_id, channel_id)).fetchall()
        options = [
            discord.SelectOption(label=game[0], value=game[0])
            for game in games
        ]
        super().__init__(placeholder='Select a game...', min_values=1, max_values=1, options=options)
        self.server_id = server_id
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        game_name = self.values[0]
        c.execute('DELETE FROM GAME_DATA WHERE serverid = ? AND channelid = ? AND game = ?', (self.server_id, self.channel_id, game_name))
        conn.commit()

        embed = discord.Embed(title=f'Unset this channel for updates on {game_name}.', color=0x00FF00)
        await interaction.channel.send(embed=embed)

class GameSelect(discord.ui.Select):
    def __init__(self, games):
        options = [discord.SelectOption(label=game, value=game) for game in games]
        super().__init__(placeholder='Select a game', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        game_name = self.values[0]
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id

        c.execute('INSERT INTO GAME_DATA(serverid, channelid, game)VALUES (?, ?, ?)', (guild_id, channel_id, game_name))
        conn.commit()

        embed = discord.Embed(title=f'Set this channel for updates on {game_name}.', color=0x00FF00)
        await interaction.channel.send(embed=embed)
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
                    await channel.send(embed=embed)
        await asyncio.sleep(60)

async def check_match_updates():
    while True:
        rows = c.execute('SELECT serverid, channelid, game FROM GAME_DATA').fetchall()
        for row in rows:
            server_id, channel_id, game_name = row
            await send_match_updates(game_name, channel_id)
        await asyncio.sleep(60)

async def search_player(player_name):
    url = f"https://api.pandascore.co/players?search[name]={player_name}&token={PANDASCORE_TOKEN}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            players = await response.json()

    if not players:
        embed = discord.Embed(title="No players found.", color=0xFF0000)
        return embed
    
    embeds = []
    player_embeds = []
    for i, player in enumerate(players, start=1):
        if i % 25 == 0:
            embed = discord.Embed(title=f"Player search results for '{player_name}':", color=0x00FF00)
            for player_info in player_embeds:
                embed.add_field(name=player_info['name'], value=f"ID: {player_info['id']}", inline=False)
            embeds.append(embed)
            player_embeds = []
        player_embeds.append(player)
    
    if player_embeds:
        embed = discord.Embed(title=f"Player search results for '{player_name}':", color=0x00FF00)
        for player_info in player_embeds:
            embed.add_field(name=player_info['name'], value=f"ID: {player_info['id']}", inline=False)
        embeds.append(embed)
    
    return embeds
    
async def search_team(team_name):
    url = f"https://api.pandascore.co/teams?search[name]={team_name}&token={PANDASCORE_TOKEN}"
    response = requests.get(url)
    teams = response.json()
    
    if not teams:
        embed = discord.Embed(title="No teams found.", color=0xFF0000)
        return embed
    
    embeds = []
    team_embeds = []
    for i, team in enumerate(teams, start=1):
        if i % 25 == 0:
            embed = discord.Embed(title=f"Team search results for '{team_name}':", color=0x00FF00)
            for team_info in team_embeds:
                embed.add_field(name=team_info['name'], value=f"ID: {team_info['id']}", inline=False)
            embeds.append(embed)
            team_embeds = []
        team_embeds.append(team)

    if team_embeds:
        embed = discord.Embed(title=f"Team search results for '{team_name}':", color=0x00FF00)
        for team_info in team_embeds:
            embed.add_field(name=team_info['name'], value=f"ID: {team_info['id']}", inline=False)
        embeds.append(embed)

    return embeds

client.run(BOT_TOKEN)
