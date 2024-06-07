import discord 
import asyncio
import requests
import json
import aiohttp
import sqlite3
import random

with open('config.json') as f:
    config = json.load(f)

conn = sqlite3.connect('database.sqlite')
c = conn.cursor()

BOT_TOKEN = config['DISCORD_TOKEN']
PANDASCORE_TOKEN = config['PANDASCORE_TOKEN'] 

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

teams = {}
max_teams = 16

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
        c.execute('INSERT INTO SERVER_DATA (serverid, prefix) VALUES (?, ?)', (message.guild.id, '>'))
        conn.commit()

    prefix = c.execute('SELECT prefix FROM SERVER_DATA WHERE serverid = ?', (message.guild.id,)).fetchone()[0]
    if message.content.startswith(prefix + 'help'):
        embed = discord.Embed(title="Commands", color=0xFF00FF)
        embed.add_field(name=f"`{prefix}help`", value="Display this help message.", inline=False)
        embed.add_field(name=f"`{prefix}searchteam` **`<team name>`**", value="Search for a team.", inline=False)
        embed.add_field(name=f"`{prefix}player` **`<player name>`**", value="Search for a player.", inline=False)
        embed.add_field(name=f"`{prefix}register` **`<team name>`** **`<player1>`** **`<player2>`** ...", value="Register a team with the specified players.", inline=False)
        embed.add_field(name=f"`{prefix}teamlist` **`<all/registered>`**", value="List all teams or only the registered teams.", inline=False)
        embed.add_field(name=f"`{prefix}start` `**<swiss/double_elimination>**`", value="Start the tournament with the registered teams.", inline=False)
        embed.add_field(name=f"`{prefix}ranking` `**<swiss/double_elimination>**`", value="Display the current tournament ranking.", inline=False)
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
    
    elif message.content.startswith(prefix + 'searchteam'):
        if len(message.content.split(' ')) == 1:
            embed = discord.Embed(title="Please provide a team name to search for!", color=0xFF00FF)
            embed.add_field(name="Usage", value=f"`{prefix}searchteam <team name>`", inline=False)
            await message.channel.send(embed=embed)
            return
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

    elif message.content.startswith(prefix + 'register'):
        await register(message)

    elif message.content.startswith(prefix + 'teamlist'):
        await team_list(message)

    elif message.content.startswith(prefix + 'start'):
        await start_tournament(message)

    elif message.content.startswith(prefix + 'ranking'):
        if len(message.content.split()) == 1:
            embed = discord.Embed(title="Please provide a tournament type!", color=0xFF00FF)
            embed.add_field(name="Usage", value=f"`{prefix}ranking <swiss/double_elimination>`", inline=False)
            await message.channel.send(embed=embed)
            return
        await ranking(message)

async def ranking(message):
    tournament_type = message.content.split(' ')[1]
    if tournament_type.lower not in ['swiss', 'double_elimination']:
        embed = discord.Embed(title="Error", color=0xFF0000)
        embed.add_field(name="Error", value="Unrecognized tournament type. Use `swiss` or `double_elimination`.", inline=False)
        await message.channel.send(embed=embed)
        return

    sorted_teams = sorted(teams.items(), key=lambda item: item[1]['scores'][tournament_type], reverse=True)
    ranking_text = "\n".join([f"**{index + 1}. {team} - {data['scores'][tournament_type]} points**" for index, (team, data) in enumerate(sorted_teams)])
    embed = discord.Embed(title=f"Ranking for {tournament_type} tournament:", color=0x00FF00)
    embed.add_field(name="Ranking", value=ranking_text, inline=False)
    await message.channel.send(embed=embed)


async def start_tournament(message):
    prefix = c.execute('SELECT prefix FROM SERVER_DATA WHERE serverid = ?', (message.guild.id,)).fetchone()[0]
    parts = message.content.split()
    if len(parts) != 2:
        embed = discord.Embed(title="Usage", color=0xFF0000)
        embed.add_field(name="Usage", value=f"`{prefix}start <swiss/double_elimination>`", inline=False)
        await message.channel.send(embed=embed)
        return

    tournament_type = parts[1].lower()
    if len(teams) < 2:
        embed = discord.Embed(title="At least 2 teams are required to start a tournament.", color=0xFF0000)
        await message.channel.send(embed=embed)
        return

    if tournament_type == 'swiss':
        embed = discord.Embed(title="The Swiss tournament is starting!", color=0x0000FF)
        await message.channel.send(embed=embed)
        await round_swiss(message)
    elif tournament_type == 'double_elimination':
        embed = discord.Embed(title="The double elimination tournament is starting!", color=0x0000FF)
        await message.channel.send(embed=embed)
        await double_elimination(message)
    else:
        embed = discord.Embed(title="Unrecognized tournament type. Use `swiss` or `double_elimination`.", color=0xFF0000)
        await message.channel.send(embed=embed)

async def round_swiss(message):
    team_names = list(teams.keys())
    random.shuffle(team_names)

    if len(team_names) % 2 != 0:
        bye_team = team_names.pop()
        embed = discord.Embed(title="Information", description=f"{bye_team} has a bye this round.", color=0x0000FF)
        await message.channel.send(embed=embed)

    round_matches = [(team_names[i], team_names[i + 1]) for i in range(0, len(team_names), 2)]

    match_results = {}
    for match in round_matches:

        embed = discord.Embed(title=f"Match: {match[0]} vs {match[1]}", color=0x0000FF)
        embed.add_field(name="Instructions", value="Please enter the score for each team (separated by a space):", inline=False)
        await message.channel.send(embed=embed)
        result = await client.wait_for('message', check=lambda msg: msg.author == message.author and msg.channel == message.channel)
        scores = result.content.split()
        if len(scores) != 2:
            embed = discord.Embed(title="please enter two scores.", color=0xFF0000)
            await message.channel.send(embed=embed)
            return
        try:
            team1_score = int(scores[0])
            team2_score = int(scores[1])
        except ValueError:
            embed = discord.Embed(title="Please enter integer scores.", color=0xFF0000)
            await message.channel.send(embed=embed)
            return

        match_results[match] = (team1_score, team2_score)

        if team1_score > team2_score:
            teams[match[0]]['scores']['swiss'] += 1
        elif team2_score > team1_score:
            teams[match[1]]['scores']['swiss'] += 1
        else:
            teams[match[0]]['scores']['swiss'] += 0.5
            teams[match[1]]['scores']['swiss'] += 0.5

    embed = discord.Embed(title="Round results have been recorded.", color=0x0000FF)
    await message.channel.send(embed=embed)

async def double_elimination(message):
    team_names = list(teams.keys())
    bracket = {"winners": team_names[:], "losers": []}
    round_num = 1

    while len(bracket["winners"]) > 1 or len(bracket["losers"]) > 1:
        embed = discord.Embed(title=f"Round {round_num} of the winners bracket:", color=0x0000FF)
        await message.channel.send(embed=embed)
        winners_matches = [(bracket["winners"][i], bracket["winners"][i + 1]) for i in range(0, len(bracket["winners"]), 2)]
        winners_results = await play_matches(message, winners_matches)
        bracket["winners"] = []
        for match, scores in winners_results.items():
            if scores[0] > scores[1]:
                bracket["winners"].append(match[0])
                bracket["losers"].append(match[1])
            else:
                bracket["winners"].append(match[1])
                bracket["losers"].append(match[0])

        if bracket["losers"]:
            embed = discord.Embed(title=f"Round {round_num} of the losers bracket:", color=0x0000FF)
            await message.channel.send(embed=embed)
            losers_matches = [(bracket["losers"][i], bracket["losers"][i + 1] if i + 1 < len(bracket["losers"]) else None) for i in range(0, len(bracket["losers"]), 2)]
            losers_results = await play_matches(message, losers_matches)
            new_losers = []
            for match, scores in losers_results.items():
                if scores[0] > scores[1]:
                    new_losers.append(match[0])
                else:
                    new_losers.append(match[1])
            bracket["losers"] = new_losers

        round_num += 1

    winner = bracket["winners"][0] if bracket["winners"] else bracket["losers"][0]
    embed = discord.Embed(title=f"Round {round_num} of the losers bracket:", color=0x0000FF)
    await message.channel.send(embed=embed)
    losers_matches = [(bracket["losers"][i], bracket["losers"][i + 1] if i + 1 < len(bracket["losers"]) else None) for i in range(0, len(bracket["losers"]), 2)]    
    losers_results = await play_matches(message, losers_matches)
    new_losers = []
    for match, scores in losers_results.items():
        if scores[0] > scores[1]:
            new_losers.append(match[0])
        else:
            new_losers.append(match[1])
    bracket["losers"] = new_losers

    round_num += 1

    winner = bracket["winners"][0] if bracket["winners"] else bracket["losers"][0]
    embed = discord.Embed(title=f"The double elimination tournament is over! The winner is {winner}.", color=0x0000FF)
    await message.channel.send(embed=embed)

async def play_matches(message, matches):
    match_results = {}
    for match in matches:
        embed = discord.Embed(title=f"Match: {match[0]} vs {match[1]}", color=0x0000FF)
        await message.channel.send(embed=embed)
        result = await client.wait_for('message', check=lambda msg: msg.author == message.author and msg.channel == message.channel)
        scores = result.content.split()
        if len(scores) != 2:
            embed = discord.Embed(title="Please enter two scores.", color=0xFF0000)
            await message.channel.send(embed=embed)
            return
        try:
            team1_score = int(scores[0])
            team2_score = int(scores[1])
        except ValueError:
            embed = discord.Embed(title="Please enter integer scores.", color=0xFF0000)
            await message.channel.send(embed=embed)
            return
        match_results[match] = (team1_score, team2_score)
    return match_results
    
async def ranking(message):
    prefix = c.execute('SELECT prefix FROM SERVER_DATA WHERE serverid = ?', (message.guild.id,)).fetchone()[0]
    parts = message.content.split()
    if len(parts) != 2:
        embed = discord.Embed(title="Usage", color=0xFF0000)
        embed.add_field(name="Usage", value=f"`{prefix}ranking <swiss/double_elimination>`", inline=False)
        await message.channel.send(embed=embed)
        return

    tournament_type = parts[1].lower()
    if tournament_type not in ['swiss', 'double_elimination']:
        embed = discord.Embed(title="Error", color=0xFF0000)
        embed.add_field(name="Error", value="Unrecognized tournament type. Use `swiss` or `double_elimination`.", inline=False)
        await message.channel.send(embed=embed)
        return

    sorted_teams = sorted(teams.items(), key=lambda item: item[1]['scores'][tournament_type], reverse=True)
    ranking_list = "\n".join([f"**{team}**: {data['scores'][tournament_type]}" for team, data in sorted_teams])
    embed = discord.Embed(title="Ranking", color=0x0000FF)
    for team, data in sorted_teams:
        embed.add_field(name=team, value=data['scores'][tournament_type], inline=False)
    await message.channel.send(embed=embed)


async def team_list(message):
    prefix = c.execute('SELECT prefix FROM SERVER_DATA WHERE serverid = ?', (message.guild.id,)).fetchone()[0]
    parts = message.content.split()
    if len(parts) == 1 or parts[1] == 'all':
        if not teams:
            embed = discord.Embed(title="No teams are currently registered.", color=0xFF0000)
            await message.channel.send(embed=embed)
            return
        team_list = "\n".join([f"**{team}**: {', '.join(data['players'])}" for team, data in teams.items()])
        embed = discord.Embed(title="Registered Teams", color=0x0000FF)
        embed.add_field(name="Teams", value=team_list, inline=False)
        await message.channel.send(embed=embed)
    elif parts[1] == 'members' and len(parts) == 3:
        team_name = parts[2]
        if team_name not in teams:
            embed = discord.Embed(title="This team is not registered.", color=0xFF0000)
            await message.channel.send(embed=embed)
            return
        players = ", ".join(teams[team_name]['players'])
        embed = discord.Embed(title=f"Members of Team {team_name}", color=0x0000FF)
        for team, data in teams.items():
            if team == team_name:
                embed.add_field(name=team, value=", ".join(data['players']), inline=False)
        await message.channel.send(embed=embed)
    else:
        embed = discord.Embed(title="Help", color=0xFF00FF)
        embed.add_field(name="Usage", value=f"Use `{prefix}team_list all` to list all teams or `{prefix}team_list members <team_name>` to list the members of a team.", inline=False)
        await message.channel.send(embed=embed)


async def register(message):
    prefix = c.execute('SELECT prefix FROM SERVER_DATA WHERE serverid = ?', (message.guild.id,)).fetchone()[0]
    parts = message.content.split()
    if len(parts) < 3:
        embed = discord.Embed(title="please provide a team name and at least one player!", color=0xFF0000)
        embed.add_field(name="Usage", value=f"`{prefix}register <team name> <player1> <player2> ...`", inline=False)
        await message.channel.send(embed=embed)
    team_name = parts[1]
    players = parts[2:]

    if len(teams) >= max_teams:
        embed = discord.Embed(title="The maximum number of teams has been reached.", color=0xFF0000)
        await message.channel.send(embed=embed)
        return

    if team_name in teams:
        embed = discord.Embed(title="This team name is already taken.", color=0xFF0000)
        await message.channel.send(embed=embed)
        return

    teams[team_name] = {'players': players, 'scores': {'swiss': 0, 'double_elimination': 0}}
    embed = discord.Embed(title=f"Team {team_name} has been successfully registered.", color=0x00FF00)
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
