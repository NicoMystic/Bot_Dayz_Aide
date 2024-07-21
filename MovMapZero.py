import discord
from discord.ext import commands
import json
import asyncio
import aiofiles
import numpy as np
from Config import TOKEN

# Configuration des intents pour recevoir les messages et les fichiers joints
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
target_channel_id = 1241443490030817340

def euler_to_matrix(yaw, pitch, roll):
    # Convert degrees to radians
    yaw, pitch, roll = np.deg2rad([yaw, pitch, roll])
    
    # Compute rotation matrix components
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cr, sr = np.cos(roll), np.sin(roll)
    
    # Create rotation matrix
    rotation_matrix = np.array([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr]
    ])
    
    return rotation_matrix

@bot.command()
async def move_items(ctx):
    # Vérifier si la commande est envoyée dans le bon canal
    if ctx.channel.id != target_channel_id:
        await ctx.send("Cette commande ne peut être utilisée que dans le canal spécifié.")
        return

    # Demander le fichier JSON
    await ctx.send("Veuillez envoyer le fichier JSON.")

    def check_file(msg):
        return msg.author == ctx.author and msg.attachments and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check_file, timeout=60.0)
    except asyncio.TimeoutError:
        await ctx.send("Vous n'avez pas envoyé de fichier à temps.")
        return

    attachment = msg.attachments[0]
    json_data = await attachment.read()
    data = json.loads(json_data)

    # Enregistrer le nom du fichier principal sans extension
    main_filename = attachment.filename.split('.')[0]

    # Demander l'objet principal
    await ctx.send("Quel est le nom de l'objet principal à identifier ?")

    def check_name(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        main_object_msg = await bot.wait_for("message", check=check_name, timeout=60.0)
    except asyncio.TimeoutError:
        await ctx.send("Vous n'avez pas répondu à temps.")
        return

    main_object_name = main_object_msg.content

    # Trouver l'objet principal dans les données JSON
    main_object = next((obj for obj in data["Objects"] if obj["name"] == main_object_name), None)
    if not main_object:
        await ctx.send("Objet principal non trouvé.")
        return

    # Calculer les différences pour mettre l'objet principal à (0, 0, 0)
    current_xyz = main_object["pos"][:3]
    diff_xyz = [-coord for coord in current_xyz]

    # Appliquer les différences de translation à tous les objets
    for obj in data["Objects"]:
        obj["pos"][:3] = [coord + diff for coord, diff in zip(obj["pos"][:3], diff_xyz)]

    # Enregistrer le fichier modifié
    new_filename = f"{main_filename}_Zero.json"
    async with aiofiles.open(new_filename, "w") as f:
        await f.write(json.dumps(data, indent=4))

    await ctx.send("Voici le fichier modifié :", file=discord.File(new_filename))

bot.run(TOKEN)
