import discord
from discord.ext import commands
import random
import json

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

    teams[team_name] = list(players)
    await ctx.send(f"L'équipe {team_name} a été inscrite avec succès.")

# Commande pour afficher les équipes inscrites
@bot.command()
async def teams_list(ctx):
    if not teams:
        await ctx.send("Aucune équipe n'est inscrite pour le moment.")
        return

    team_list = "\n".join([f"{team}: {', '.join(players)}" for team, players in teams.items()])
    await ctx.send(f"Équipes inscrites :\n{team_list}")

# Commande pour lancer le tournoi
@bot.command()
async def start_tournament(ctx):
    if len(teams) < 2:
        await ctx.send("Il faut au moins 2 équipes pour lancer le tournoi.")
        return

    await ctx.send("Le tournoi commence !")
    await round_swiss(ctx)

async def round_swiss(ctx):
    team_names = list(teams.keys())
    random.shuffle(team_names)
    round_matches = [(team_names[i], team_names[i+1]) for i in range(0, len(team_names), 2)]
    
    match_results = []
    for match in round_matches:
        await ctx.send(f"Match : {match[0]} vs {match[1]}")
        result = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
        match_results.append(result.content)

    await ctx.send("Passons à l'arbre à double élimination.")
    await double_elimination(ctx, team_names)

async def double_elimination(ctx, team_names):
    await ctx.send("Arbre à double élimination.")

@bot.command(name='commands')
async def list_commands(ctx):
    help_text = """
    Commandes disponibles :
    !register <nom_équipe> <joueur1> <joueur2> ... : Inscrire une nouvelle équipe avec des joueurs.
    !teams_list : Afficher la liste des équipes inscrites.
    !start_tournament : Lancer le tournoi.
    !commands : Afficher cette aide.
    """
    await ctx.send(help_text)


bot.run(BOT_TOKEN)
