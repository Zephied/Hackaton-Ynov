import discord
from discord.ext import commands
import random
import json

# Charger le token du bot depuis le fichier de configuration
with open('config.json') as f:
    config = json.load(f)

BOT_TOKEN = config['DISCORD_TOKEN']

intents = discord.Intents.default()
intents.message_content = True  # Activer l'intent pour accéder au contenu des messages

bot = commands.Bot(command_prefix='!', intents=intents)

teams = {}
max_teams = 16

# Commande pour inscrire une équipe
@bot.command()
async def register(ctx, team_name: str, *players):
    if len(teams) >= max_teams:
        await ctx.send("**Le nombre maximum d'équipes est atteint.**")
        return

    if team_name in teams:
        await ctx.send("**Ce nom d'équipe est déjà pris.**")
        return

    teams[team_name] = {'players': list(players), 'scores': {'suisse': 0, 'double_elimination': 0}}
    await ctx.send(f"**L'équipe {team_name} a été inscrite avec succès.**")

# Commande pour afficher les équipes inscrites
@bot.group(name='team_list', invoke_without_command=True)
async def team_list(ctx):
    await ctx.send("Utilisez `!team_list all` pour afficher toutes les équipes ou `!team_list members <nom_équipe>` pour afficher les membres d'une équipe.")

@team_list.command(name='all')
async def team_list_all(ctx):
    if not teams:
        await ctx.send("**Aucune équipe n'est inscrite pour le moment.**")
        return

    team_list = "\n".join([f"**{team}**: {', '.join(data['players'])}" for team, data in teams.items()])
    await ctx.send(f"**Équipes inscrites :**\n{team_list}")

@team_list.command(name='members')
async def team_list_members(ctx, team_name: str):
    if team_name not in teams:
        await ctx.send("**Cette équipe n'est pas inscrite.**")
        return

    players = ", ".join(teams[team_name]['players'])
    await ctx.send(f"**Membres de l'équipe {team_name}** : {players}")

# Commande pour lancer le tournoi
@bot.command()
async def start_tournament(ctx, tournament_type: str):
    if len(teams) < 2:
        await ctx.send("**Il faut au moins 2 équipes pour lancer le tournoi.**")
        return

    if tournament_type.lower() == 'suisse':
        await ctx.send("**Le tournoi suisse commence !**")
        await round_swiss(ctx)
    elif tournament_type.lower() == 'double_elimination':
        await ctx.send("**Le tournoi à double élimination commence !**")
        await double_elimination(ctx)
    else:
        await ctx.send("**Type de tournoi non reconnu. Utilisez `suisse` ou `double_elimination`.**")

async def round_swiss(ctx):
    team_names = list(teams.keys())
    random.shuffle(team_names)

    if len(team_names) % 2 != 0:
        bye_team = team_names.pop()
        await ctx.send(f"**{bye_team} a un bye ce tour-ci.**")

    round_matches = [(team_names[i], team_names[i + 1]) for i in range(0, len(team_names), 2)]

    match_results = {}
    for match in round_matches:
        await ctx.send(f"**Match : {match[0]} vs {match[1]}**\nVeuillez saisir le score pour chaque équipe (séparé par un espace) :")
        result = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
        scores = result.content.split()
        if len(scores) != 2:
            await ctx.send("**Veuillez saisir deux scores.**")
            return
        try:
            team1_score = int(scores[0])
            team2_score = int(scores[1])
        except ValueError:
            await ctx.send("**Veuillez saisir des nombres entiers pour les scores.**")
            return

        match_results[match] = (team1_score, team2_score)
     
        if team1_score > team2_score:
            teams[match[0]]['scores']['suisse'] += 1
        elif team2_score > team1_score:
            teams[match[1]]['scores']['suisse'] += 1
        else:
            teams[match[0]]['scores']['suisse'] += 0.5
            teams[match[1]]['scores']['suisse'] += 0.5

    await ctx.send("**Les résultats du tour sont enregistrés.**")

async def double_elimination(ctx):
    team_names = list(teams.keys())
    bracket = {"winners": team_names[:], "losers": []}
    round_number = 1

    while len(bracket["winners"]) > 1 or len(bracket["losers"]) > 1:
        await ctx.send(f"**Round {round_number}** :")
        round_number += 1

       
        if len(bracket["winners"]) > 1:
            winners_matches = [(bracket["winners"][i], bracket["winners"][i + 1]) for i in range(0, len(bracket["winners"]) - 1, 2)]
            if len(bracket["winners"]) % 2 == 1:
                winners_matches.append((bracket["winners"][-1], None))
            winners_results = await play_matches(ctx, winners_matches, 'double_elimination')

            new_winners = []
            for match, result in winners_results.items():
                if match[1] is None:  
                    new_winners.append(match[0])
                elif result[0] > result[1]:
                    new_winners.append(match[0])
                    bracket["losers"].append(match[1])
                else:
                    new_winners.append(match[1])
                    bracket["losers"].append(match[0])
            bracket["winners"] = new_winners

      
        if len(bracket["losers"]) > 1:
            losers_matches = [(bracket["losers"][i], bracket["losers"][i + 1]) for i in range(0, len(bracket["losers"]) - 1, 2)]
            if len(bracket["losers"]) % 2 == 1:
                losers_matches.append((bracket["losers"][-1], None))
            losers_results = await play_matches(ctx, losers_matches, 'double_elimination')

            new_losers = []
            for match, result in losers_results.items():
                if match[1] is None:  
                    new_losers.append(match[0])
                elif result[0] > result[1]:
                    new_losers.append(match[0])
                else:
                    new_losers.append(match[1])
            bracket["losers"] = new_losers

        if len(bracket["winners"]) == 1 and len(bracket["losers"]) == 1:
            # Final match between the last winner and the last loser
            final_match = (bracket["winners"][0], bracket["losers"][0])
            final_result = await play_matches(ctx, [final_match], 'double_elimination')
            if final_result[final_match][0] > final_result[final_match][1]:
                await ctx.send(f"**Le tournoi est terminé. Le gagnant est {final_match[0]}.**")
            else:
                await ctx.send(f"**Le tournoi est terminé. Le gagnant est {final_match[1]}.**")
            return

    if len(bracket["winners"]) == 1:
        await ctx.send(f"**Le tournoi est terminé. Le gagnant est {bracket['winners'][0]}.**")
    elif len(bracket["losers"]) == 1:
        await ctx.send(f"**Le tournoi est terminé. Le gagnant est {bracket['losers'][0]}.**")

async def play_matches(ctx, matches, tournament_type):
    match_results = {}
    for match in matches:
        if match[1] is None:
            await ctx.send(f"**{match[0]} a un bye et avance automatiquement au tour suivant.**")
            match_results[match] = (1, 0)  
            teams[match[0]]['scores'][tournament_type] += 1
            continue
        
        await ctx.send(f"**Match : {match[0]} vs {match[1]}**\nVeuillez saisir le score pour chaque équipe (séparé par un espace) :")
        result = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
        scores = result.content.split()
        if len(scores) != 2:
            await ctx.send("**Veuillez saisir deux scores.**")
            return
        try:
            team1_score = int(scores[0])
            team2_score = int(scores[1])
        except ValueError:
            await ctx.send("**Veuillez saisir des nombres entiers pour les scores.**")
            return

        match_results[match] = (team1_score, team2_score)
        if team1_score > team2_score:
            teams[match[0]]['scores'][tournament_type] += 1
        elif team2_score > team1_score:
            teams[match[1]]['scores'][tournament_type] += 1
        else:
            teams[match[0]]['scores'][tournament_type] += 0.5
            teams[match[1]]['scores'][tournament_type] += 0.5
    return match_results

@bot.command(name='commands')
async def list_commands(ctx):
    help_text = """
    **Commandes disponibles :**
    `!register <nom_équipe> <joueur1> <joueur2> ...` : Inscrire une nouvelle équipe avec des joueurs.
    `!team_list all` : Afficher la liste des équipes inscrites.
    `!team_list members <nom_équipe>` : Afficher les membres d'une équipe spécifiée.
    `!start_tournament suisse/double_elimination` : Lancer le tournoi avec le type de tournoi spécifié.
    `!ranking suisse/double_elimination` : Afficher le classement des équipes pour le type de tournoi spécifié.
    `!commands` : Afficher cette aide.
    """
    await ctx.send(help_text)

@bot.command()
async def ranking(ctx, tournament_type: str):
    if tournament_type.lower() not in ['suisse', 'double_elimination']:
        await ctx.send("**Type de tournoi non reconnu. Utilisez `suisse` ou `double_elimination`.**")
        return

    sorted_teams = sorted(teams.items(), key=lambda item: item[1]['scores'][tournament_type], reverse=True)
    ranking_text = "\n".join([f"**{index + 1}. {team} - {data['scores'][tournament_type]} points**" for index, (team, data) in enumerate(sorted_teams)])
    
    await ctx.send(f"**Classement des équipes pour le tournoi {tournament_type}**:\n{ranking_text}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("**Commande non trouvée. Utilisez `!commands` pour voir la liste des commandes disponibles.**")

bot.run(BOT_TOKEN)
