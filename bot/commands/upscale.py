import discord
from discord.ext import commands
import os 
from discord import app_commands
from PIL import Image
import asyncio
from pathlib import Path
import subprocess
import sys
import logging

# Configurer le logging pour Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Augmenter la limite de taille d'image pour Pillow
Image.MAX_IMAGE_PIXELS = None

class Upscale(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Limite le nombre de téléchargements simultanés à 2
        self.semaphore = asyncio.Semaphore(2)

    @app_commands.command(name="image-upscale-beta", description="Upscale une image avec Real-ESRGAN")
    async def image_upscale(self, interaction: discord.Interaction, image: discord.Attachment):
        
        # Utiliser le semaphore pour limiter à 2 upscales simultanés
        async with self.semaphore:
            # Defer pour éviter le timeout (traitement long)
            await interaction.response.defer()
            
            # Vérification du type de fichier
            if not image.content_type or not image.content_type.startswith("image/"):
                await interaction.followup.send("❌ Veuillez envoyer une image valide.")
                return

            # Sauvegarde du fichier envoyé
            input_path = f"input_{interaction.id}.png"
            output_path = f"output_{interaction.id}.png"
            
            try:
                logger.info(f"[UPSCALE] Début du traitement pour l'interaction {interaction.id}")
                await interaction.edit_original_response(content="🔄 Téléchargement de l'image... 10%")
                await image.save(Path(input_path))
                logger.info(f"[UPSCALE] Image téléchargée: {input_path}")
                
                # Analyser la taille de l'image
                img = Image.open(input_path)
                width, height = img.size
                pixels = width * height
                img.close()
                logger.info(f"[UPSCALE] Dimensions: {width}x{height} ({pixels:,} pixels)")
                
                # Estimation du temps selon la taille (en CPU)
                if pixels < 500_000:  # ~700x700
                    time_estimate = "30 secondes à 2 minutes"
                    warning = ""
                elif pixels < 1_500_000:  # ~1200x1200
                    time_estimate = "2 à 5 minutes"
                    warning = "⚠️ Image moyenne, cela peut prendre du temps sur CPU."
                elif pixels < 4_000_000:  # ~2000x2000
                    time_estimate = "5 à 15 minutes"
                    warning = "⚠️ Grande image, traitement très long sur CPU !"
                else:  # Plus de 4 millions de pixels
                    time_estimate = "15 minutes ou plus"
                    warning = f"⚠️ Image très grande ({width}x{height}) !\n" \
                             f"⏱️ Le traitement peut prendre très longtemps et risque de timeout."
                
                logger.info(f"[UPSCALE] Temps estimé: {time_estimate}")
                
                # Afficher l'avertissement si nécessaire
                if warning:
                    await interaction.edit_original_response(
                        content=f"{warning}\n📊 Taille : {width}x{height} ({pixels:,} pixels)\n"
                                f"⏱️ Temps estimé : {time_estimate}\n\n🔄 Préparation..."
                    )
                    await asyncio.sleep(2)

                # Déterminer le chemin de l'exécutable selon l'OS
                if os.name == 'nt':  # Windows
                    realesrgan_path = os.path.join("tools", "real-esrgan", "realesrgan-ncnn-vulkan.exe")
                else:  # Linux/Unix (Render)
                    realesrgan_path = os.path.join("tools", "real-esrgan", "realesrgan-ncnn-vulkan")
                
                # Vérifier que l'exécutable existe
                if not os.path.exists(realesrgan_path):
                    logger.info(f"[UPSCALE] ERREUR: Real-ESRGAN introuvable à {realesrgan_path}")
                    await interaction.edit_original_response(
                        content=f"❌ Real-ESRGAN n'est pas installé. Chemin: {realesrgan_path}"
                    )
                    return
                
                logger.info(f"[UPSCALE] Lancement de Real-ESRGAN: {realesrgan_path}")
                await interaction.edit_original_response(
                    content=f"🔄 Upscaling en cours...\n⏱️ Temps estimé : {time_estimate}\n\n"
                            f"💡 Le bot continue de fonctionner, soyez patient !"
                )
                
                # Commande Real-ESRGAN avec asyncio pour ne pas bloquer l'event loop
                logger.info(f"[UPSCALE] Commande: {realesrgan_path} -i {input_path} -o {output_path} -s 4")
                process = await asyncio.create_subprocess_exec(
                    realesrgan_path,
                    "-i", input_path,
                    "-o", output_path,
                    "-s", "4",  # upscale x4
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Créer une tâche pour mettre à jour le message pendant le traitement
                async def update_progress():
                    dots = 1
                    elapsed = 0
                    while True:
                        await asyncio.sleep(10)  # Mise à jour toutes les 10 secondes
                        elapsed += 10
                        dot_str = "." * dots
                        logger.info(f"[UPSCALE] Toujours en cours... ({elapsed}s écoulées)")
                        await interaction.edit_original_response(
                            content=f"🔄 Upscaling en cours{dot_str}\n⏱️ Temps estimé : {time_estimate}\n💡 Le processus est actif, merci de patienter !"       
                        )
                        dots = (dots % 3) + 1
                
                update_task = asyncio.create_task(update_progress())
                
                try:
                    logger.info(f"[UPSCALE] En attente de la fin du processus...")
                    stdout, stderr = await process.communicate()
                    logger.info(f"[UPSCALE] Processus terminé avec le code: {process.returncode}")
                finally:
                    update_task.cancel()
                    try:
                        await update_task
                    except asyncio.CancelledError:
                        pass
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Erreur inconnue"
                    logger.info(f"[UPSCALE] ERREUR: {error_msg}")
                    await interaction.edit_original_response(
                        content=f"❌ Erreur Real-ESRGAN : {error_msg[:200]}"
                    )
                    return
                
                logger.info(f"[UPSCALE] Upscaling terminé avec succès")
                
                await interaction.edit_original_response(content="🔄 Vérification du fichier... 60%")
                
                # Vérifier que le fichier de sortie existe
                if not os.path.exists(output_path):
                    logger.info(f"[UPSCALE] ERREUR: Fichier de sortie introuvable: {output_path}")
                    await interaction.edit_original_response(content="❌ Erreur : le fichier upscalé n'a pas été généré.")
                    return
                
                output_size = os.path.getsize(output_path)
                logger.info(f"[UPSCALE] Fichier de sortie créé: {output_path} ({output_size / (1024*1024):.2f} MB)")

                await interaction.edit_original_response(content="🔄 Optimisation de la taille... 80%")
                
                # Vérifier la taille du fichier (limite Discord : 8 MB)
                file_size = os.path.getsize(output_path)
                max_size = 8 * 1024 * 1024  # 8 MB en bytes
                
                final_path = output_path
                message = "✅ Voici ton image upscalée :"
                
                # Si le fichier est trop gros, le compresser
                if file_size > max_size:
                    logger.info(f"[UPSCALE] Fichier trop volumineux ({file_size / (1024*1024):.2f} MB), compression nécessaire")
                    compressed_path = f"compressed_{interaction.id}.jpg"
                    
                    try:
                        img = Image.open(output_path)
                        
                        # Compression progressive
                        quality = 95
                        while quality > 20:
                            img.save(compressed_path, "JPEG", quality=quality, optimize=True)
                            if os.path.getsize(compressed_path) <= max_size:
                                break
                            quality -= 5
                        
                        # Si toujours trop gros, réduire les dimensions
                        if os.path.getsize(compressed_path) > max_size:
                            width, height = img.size
                            new_width, new_height = width // 2, height // 2
                            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            img_resized.save(compressed_path, "JPEG", quality=85, optimize=True)
                            img_resized.close()
                        
                        img.close()
                        final_path = compressed_path
                        message = "✅ Voici ton image upscalée (compressée pour Discord) :"
                        compressed_size = os.path.getsize(compressed_path)
                        logger.info(f"[UPSCALE] Compression réussie: {compressed_size / (1024*1024):.2f} MB")
                        
                    except Exception as e:
                        logger.info(f"[UPSCALE] ERREUR lors de la compression: {e}")
                        await interaction.edit_original_response(
                            content=f"❌ Fichier trop volumineux ({file_size / (1024*1024):.1f} MB) et impossible à compresser. Limite : 8 MB"
                        )
                        return

                await interaction.edit_original_response(content="🔄 Envoi du fichier... 100%")
                logger.info(f"[UPSCALE] Préparation de l'envoi de l'embed...")
                
                # Créer un embed avec les informations
                embed = discord.Embed(
                    title="🎨 Upscale terminé !",
                    description=message,
                    color=discord.Color.green()
                )
                
                # Ajouter les informations de taille
                original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
                final_size = os.path.getsize(final_path) / (1024 * 1024)  # MB
                
                embed.add_field(name="📊 Taille originale", value=f"{original_size:.2f} MB", inline=True)
                embed.add_field(name="📊 Taille finale", value=f"{final_size:.2f} MB", inline=True)
                embed.add_field(name="🔍 Facteur", value="x4", inline=True)
                
                # Récupérer le nom original du fichier (sans extension)
                original_filename = os.path.splitext(image.filename)[0]
                
                # Envoi avec les deux images (avant/après)
                files = [
                    discord.File(input_path, filename=f"{original_filename}_original.png"),
                    discord.File(final_path, filename=f"{original_filename}_upscaled.png")
                ]
                
                embed.set_image(url=f"attachment://{original_filename}_upscaled.png")
                embed.set_thumbnail(url=f"attachment://{original_filename}_original.png")
                
                await interaction.followup.send(
                    embed=embed,
                    files=files
                )
                logger.info(f"[UPSCALE] Envoi réussi, suppression du message de progression")
                
                # Supprimer le message de progression
                await interaction.delete_original_response()
                logger.info(f"[UPSCALE] Traitement terminé avec succès pour {interaction.id}")

            except subprocess.CalledProcessError as e:
                logger.info(f"[UPSCALE] ERREUR subprocess: {e}")
                await interaction.edit_original_response(content=f"❌ Erreur Real-ESRGAN : {e}")
            except Exception as e:
                logger.info(f"[UPSCALE] ERREUR inattendue: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                await interaction.edit_original_response(content=f"❌ Erreur inattendue : {e}")
            finally:
                # Nettoyage des fichiers temporaires
                logger.info(f"[UPSCALE] Nettoyage des fichiers temporaires...")
                if os.path.exists(input_path):
                    os.remove(input_path)
                    logger.info(f"[UPSCALE] Supprimé: {input_path}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                    logger.info(f"[UPSCALE] Supprimé: {output_path}")
                compressed_path = f"compressed_{interaction.id}.jpg"
                if os.path.exists(compressed_path):
                    os.remove(compressed_path)
                    logger.info(f"[UPSCALE] Supprimé: {compressed_path}")
                logger.info(f"[UPSCALE] Nettoyage terminé")

async def setup(bot):
    await bot.add_cog(Upscale(bot))
    logger.info("✅ Extension Upscale chargée")