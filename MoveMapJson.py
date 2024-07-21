import discord
import json
import numpy as np
from discord.ext import commands
from Config import TOKEN

# Configuration des intents
intents = discord.Intents.default()
intents.message_content = True  # Pour permettre de lire le contenu des messages

# Créez une instance du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionnaire pour stocker l'état de progression des utilisateurs
user_state = {}

# Variable globale pour stocker le fichier JSON téléversé
uploaded_filename = None

# Demander le fichier JSON
@bot.command()
async def upload(ctx):
    await ctx.send("Veuillez téléverser le fichier JSON.")

@bot.event
async def on_message(message):
    global uploaded_filename
    if message.author.bot:
        return

    if message.attachments:
        attachment = message.attachments[0]
        if attachment.filename.endswith('.json'):
            uploaded_filename = attachment.filename
            await attachment.save(uploaded_filename)
            await message.channel.send(f"Fichier {uploaded_filename} téléversé avec succès.")
            user_state[message.author.id] = {"step": "nom_objet", "filename": uploaded_filename}
            await message.channel.send("Veuillez entrer le nom de l'objet principal:")
        else:
            await message.channel.send("Veuillez téléverser un fichier JSON valide.")
    elif message.author.id in user_state:
        state = user_state[message.author.id]
        if state["step"] == "nom_objet":
            state["objet_principal"] = message.content
            state["step"] = "coordonnees"
            await message.channel.send("Veuillez entrer les nouvelles coordonnées X Y Z séparées par des espaces:")
        elif state["step"] == "coordonnees":
            try:
                coordonnees = list(map(float, message.content.split()))
                if len(coordonnees) != 3:
                    await message.channel.send("Veuillez entrer trois valeurs pour les coordonnées.")
                    return
                state["coordonnees"] = coordonnees
                state["step"] = "orientations"
                await message.channel.send("Veuillez entrer les nouvelles orientations Y P R séparées par des espaces:")
            except ValueError:
                await message.channel.send("Veuillez entrer des valeurs numériques.")
        elif state["step"] == "orientations":
            try:
                orientations = list(map(float, message.content.split()))
                if len(orientations) != 3:
                    await message.channel.send("Veuillez entrer trois valeurs pour les orientations.")
                    return
                state["orientations"] = orientations
                await deplacer_objets(message.channel, state["filename"], state["objet_principal"], state["coordonnees"], orientations)
                del user_state[message.author.id]  # Réinitialiser l'état de l'utilisateur
            except ValueError:
                await message.channel.send("Veuillez entrer des valeurs numériques.")
    else:
        await bot.process_commands(message)

# Fonction pour convertir les angles d'Euler en matrice de rotation
def euler_to_matrix(yaw, pitch, roll):
    yaw, pitch, roll = np.deg2rad([yaw, pitch, roll])
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cr, sr = np.cos(roll), np.sin(roll)
    return np.array([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr]
    ])

# Déplacer l'objet principal et les objets associés
async def deplacer_objets(channel, filename, objet_principal, coordonnees, orientations):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)

        objet_principal_data = None
        for obj in data['Objects']:
            if obj['name'] == objet_principal:
                objet_principal_data = obj
                break

        if not objet_principal_data:
            await channel.send(f"Objet principal {objet_principal} non trouvé dans le fichier JSON.")
            return

        # Calculer la différence de position
        diff_xyz = np.array(coordonnees) - np.array(objet_principal_data['pos'])

        # Mettre à jour les coordonnées et l'orientation de l'objet principal
        objet_principal_data['pos'] = coordonnees
        objet_principal_data['ypr'] = orientations

        for obj in data['Objects']:
            if obj != objet_principal_data:
                # Calculer la position relative par rapport à l'objet principal initial
                relative_pos = np.array(obj['pos']) - np.array(objet_principal_data['pos'])
                # Mettre à jour la position en ajoutant la différence
                obj['pos'] = (relative_pos + np.array(coordonnees)).tolist()
                # Conserver les orientations des objets
                obj['ypr'] = obj['ypr']

        new_filename = f"{filename.split('.')[0]}_Final.json"
        with open(new_filename, 'w') as file:
            json.dump(data, file, indent=4)

        await channel.send(f"Les objets ont été déplacés et le fichier a été sauvegardé en tant que {new_filename}.")
        await channel.send(file=discord.File(new_filename))
    except Exception as e:
        await channel.send(f"Une erreur s'est produite: {e}")

# Démarrer le bot
bot.run(TOKEN)
