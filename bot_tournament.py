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
        await ctx.send("Le nombre maximum d'équipes est atteint.")
        return

    if team_name in teams:
        await ctx.send("Ce nom d'équipe est déjà pris.")
        return

    teams[team_name] = {'players': list(players), 'score': 0}
    await ctx.send(f"L'équipe {team_name} a été inscrite avec succès.")

# Commande pour afficher les équipes inscrites
@bot.command()
async def teams_list(ctx):
    if not teams:
        await ctx.send("Aucune équipe n'est inscrite pour le moment.")
        return

    team_list = "\n".join([f"{team}: {', '.join(data['players'])}" for team, data in teams.items()])
    await ctx.send(f"Équipes inscrites :\n{team_list}")

# Commande pour lancer le tournoi
@bot.command()
async def start_tournament(ctx, tournament_type: str):
    if len(teams) < 2:
        await ctx.send("Il faut au moins 2 équipes pour lancer le tournoi.")
        return

    if tournament_type.lower() == 'suisse':
        await ctx.send("Le tournoi suisse commence !")
        await round_swiss(ctx)
    elif tournament_type.lower() == 'double_elimination':
        await ctx.send("Le tournoi à double élimination commence !")
        await double_elimination(ctx)
    else:
        await ctx.send("Type de tournoi non reconnu. Utilisez suisse ou double_elimination.")

async def round_swiss(ctx):
    team_names = list(teams.keys())
    random.shuffle(team_names)

    if len(team_names) % 2 != 0:
        bye_team = team_names.pop()
        await ctx.send(f"{bye_team} a un bye ce tour-ci.")

    round_matches = [(team_names[i], team_names[i + 1]) for i in range(0, len(team_names), 2)]

    match_results = {}
    for match in round_matches:
        await ctx.send(f"Match : {match[0]} vs {match[1]}\nVeuillez saisir le score pour chaque équipe (séparé par un espace) :")
        result = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
        scores = result.content.split()
        if len(scores) != 2:
            await ctx.send("Veuillez saisir deux scores.")
            return
        try:
            team1_score = int(scores[0])
            team2_score = int(scores[1])
        except ValueError:
            await ctx.send("Veuillez saisir des nombres entiers pour les scores.")
            return

        match_results[match] = (team1_score, team2_score)
        # Mise à jour des scores des équipes
        if team1_score > team2_score:
            teams[match[0]]['score'] += 1
        elif team2_score > team1_score:
            teams[match[1]]['score'] += 1
        else:
            teams[match[0]]['score'] += 0.5
            teams[match[1]]['score'] += 0.5

    await ctx.send("Les résultats du tour sont enregistrés.")

async def double_elimination(ctx):
    team_names = list(teams.keys())
    bracket = {"winners": team_names[:], "losers": []}
    round_number = 1

    while len(bracket["winners"]) > 1 or len(bracket["losers"]) > 1:
        await ctx.send(f"Round {round_number} :")
        round_number += 1

        winners_matches = [(bracket["winners"][i], bracket["winners"][i + 1]) for i in range(0, len(bracket["winners"]), 2)]
        winners_results = await play_matches(ctx, winners_matches)

       
        bracket["winners"] = []
        for match, result in winners_results.items():
            if result[0] > result[1]:
                bracket["winners"].append(match[0])
                bracket["losers"].append(match[1])
            else:
                bracket["winners"].append(match[1])
                bracket["losers"].append(match[0])

        if len(bracket["losers"]) > 1:
            losers_matches = [(bracket["losers"][i], bracket["losers"][i + 1]) for i in range(0, len(bracket["losers"]), 2)]
            losers_results = await play_matches(ctx, losers_matches)

        
            new_losers = []
            for match, result in losers_results.items():
                if result[0] > result[1]:
                    new_losers.append(match[0])
                else:
                    new_losers.append(match[1])
            bracket["losers"] = new_losers

    await ctx.send(f"Le tournoi est terminé. Le gagnant est {bracket['winners'][0]}")

async def play_matches(ctx, matches):
    match_results = {}
    for match in matches:
        await ctx.send(f"Match : {match[0]} vs {match[1]}\nVeuillez saisir le score pour chaque équipe (séparé par un espace) :")
        result = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
        scores = result.content.split()
        if len(scores) != 2:
            await ctx.send("Veuillez saisir deux scores.")
            return
        try:
            team1_score = int(scores[0])
            team2_score = int(scores[1])
        except ValueError:
            await ctx.send("Veuillez saisir des nombres entiers pour les scores.")
            return

        match_results[match] = (team1_score, team2_score)
    return match_results

@bot.command(name='commands')
async def list_commands(ctx):
    help_text = """
    **Commandes disponibles :**
    *!register* <nom_équipe> <joueur1> <joueur2> ... : Inscrire une nouvelle équipe avec des joueurs.
    *!teams_list* : Afficher la liste des équipes inscrites.
    *!start_tournament* suisse/double_elimination : Lancer le tournoi avec le type de tournoi spécifié.
    *!commands* : Afficher cette aide.
    """
    await ctx.send(help_text)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Commande non trouvée. Utilisez !commands pour voir la liste des commandes disponibles.")

bot.run(BOT_TOKEN)
