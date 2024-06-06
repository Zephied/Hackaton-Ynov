import discord
from discord.ext import commands
import random
import json
import matplotlib.pyplot as plt
import networkx as nx
import math

# Charger le token du bot depuis le fichier de configuration
with open('config.json') as f:
    config = json.load(f)

BOT_TOKEN = config['DISCORD_TOKEN']

intents = discord.Intents.default()
intents.message_content = True  # Activer l'intent pour accéder au contenu des messages

bot = commands.Bot(command_prefix='!', intents=intents)

teams = {}
max_teams = 16
match_history = []

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

def generate_round_matches_swiss(team_names, previous_rounds):
    num_teams = len(team_names)
    matches = []
    attempted_pairs = set(previous_rounds)

    for i in range(num_teams):
        for j in range(i + 1, num_teams):
            pair = (team_names[i], team_names[j])
            if pair not in attempted_pairs:
                matches.append(pair)
                attempted_pairs.add(pair)
    return matches

async def round_swiss(ctx):
    team_names = list(teams.keys())
    random.shuffle(team_names)

    previous_rounds = []

    if len(team_names) % 2 != 0:
        bye_team = team_names.pop()
        await ctx.send(f"**{bye_team} a un bye ce tour-ci.**")

    num_teams = len(team_names)
    num_rounds = math.ceil(math.log2(num_teams))

    match_results = {}
    for round_number in range(num_rounds):
        await ctx.send(f"**Round {round_number + 1} :**")
        round_matches = generate_round_matches_swiss(team_names, previous_rounds)

        if not round_matches:
            await ctx.send("**Plus de matchs possibles pour ce round.**")
            break

        results = await play_matches(ctx, round_matches, 'suisse')

        # Enregistrement des résultats
        for match, result in results.items():
            match_results[match] = result
            if result[0] > result[1]:
                teams[match[0]]['scores']['suisse'] += 1
            elif result[1] > result[0]:
                teams[match[1]]['scores']['suisse'] += 1
            else:
                teams[match[0]]['scores']['suisse'] += 0.5
                teams[match[1]]['scores']['suisse'] += 0.5

        previous_rounds.extend(round_matches)
        await ctx.send("**Les résultats du tour sont enregistrés.**")

        team_names = [team for team, _ in sorted(teams.items(), key=lambda x: x[1]['scores']['suisse'], reverse=True)]

    await show_ranking(ctx, 'suisse')
    return match_results

async def show_ranking(ctx, tournament_type: str):
    sorted_teams = sorted(teams.items(), key=lambda item: item[1]['scores'][tournament_type], reverse=True)
    ranking_text = "\n".join([f"**{index + 1}. {team} - {data['scores'][tournament_type]} points**" for index, (team, data) in enumerate(sorted_teams)])
    
    await ctx.send(f"**Classement des équipes pour le tournoi {tournament_type}**:\n{ranking_text}")

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
            record_match_results(winners_results, 'winners')

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
            record_match_results(losers_results, 'losers')

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
            final_match = (bracket["winners"][0], bracket["losers"][0])
            final_result = await play_matches(ctx, [final_match], 'double_elimination')
            record_match_results(final_result, 'final')

            if final_result[final_match][0] > final_result[final_match][1]:
                await ctx.send(f"**Le tournoi est terminé. Le gagnant est {final_match[0]}.**")
            else:
                await ctx.send(f"**Le tournoi est terminé. Le gagnant est {final_match[1]}.**")

            break

    await generate_tournament_tree(ctx)

async def play_matches(ctx, matches, tournament_type):
    match_results = {}
    for match in matches:
        if match[1] is None:
            await ctx.send(f"**{match[0]} a un bye et avance automatiquement au tour suivant.**")
            match_results[match] = (1, 0)
            teams[match[0]]['scores'][tournament_type] += 1
            continue
        
        await ctx.send(f"**Match : {match[0]} vs {match[1]}**\nVeuillez saisir le score pour chaque équipe (séparé par un espace) :")
        
        while True:
            result = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
            scores = result.content.split()
            if len(scores) != 2:
                await ctx.send("**Veuillez saisir deux scores.**")
                continue
            try:
                team1_score = int(scores[0])
                team2_score = int(scores[1])
                break
            except ValueError:
                await ctx.send("**Veuillez saisir des nombres entiers pour les scores.**")

        match_results[match] = (team1_score, team2_score)
        if team1_score > team2_score:
            teams[match[0]]['scores'][tournament_type] += 1
        elif team2_score > team1_score:
            teams[match[1]]['scores'][tournament_type] += 1
        else:
            teams[match[0]]['scores'][tournament_type] += 0.5
            teams[match[1]]['scores'][tournament_type] += 0.5
    return match_results

def record_match_results(results, bracket_type):
    global match_history
    for match, result in results.items():
        match_history.append({
            'team1': match[0],
            'team2': match[1],
            'team1_score': result[0],
            'team2_score': result[1],
            'bracket': bracket_type
        })

async def generate_tournament_tree(ctx):
    global match_history
    G = nx.DiGraph()

    for match in match_history:
        team1 = match['team1']
        team2 = match['team2']
        score1 = match['team1_score']
        score2 = match['team2_score']
        winner = team1 if score1 > score2 else team2

        G.add_edge(team1, winner, label=f"{score1}-{score2}")
        if team2:
            G.add_edge(team2, winner, label=f"{score2}-{score1}")

    pos = nx.spring_layout(G)
    edge_labels = nx.get_edge_attributes(G, 'label')
    plt.figure(figsize=(12, 8))
    nx.draw(G, pos, with_labels=True, node_size=3000, node_color='skyblue', font_size=10, font_color='black', arrows=True)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

    plt.title('Arbre de Tournoi')
    plt.savefig('tournament_tree.png')
    plt.close()

    await ctx.send(file=discord.File('tournament_tree.png'))

@bot.command(name='commands')
async def list_commands(ctx):
    help_text = """
    **Commandes disponibles :**
    `!register <nom_équipe> <joueur1> <joueur2> ...` : Inscrire une nouvelle équipe avec des joueurs.
    `!team_list all` : Afficher la liste des équipes inscrites.
    `!team_list members <nom_équipe>` : Afficher les membres d'une équipe spécifiée.
    `!start_tournament double_elimination` : Lancer un tournois à double élimination.
    `!start_tournament suisse` : Lancer un tournoi à round suisse.
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