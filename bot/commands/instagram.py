import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import os
import tempfile
import logging
import asyncio
import sys

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.stats_manager import stats_manager

class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Limite le nombre de téléchargements simultanés à 2
        self.semaphore = asyncio.Semaphore(2)
        self.progress_msg = None
        self.send_to_channel = False
        self.user_mention = ""

    def progress_hook(self, d):
        """Hook pour suivre la progression du téléchargement"""
        if d['status'] == 'downloading':
            try:
                # Extraire les informations de progression
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                
                if total:
                    percent = int(downloaded / total * 100)
                    prefix = self.user_mention if self.send_to_channel else ""
                    # Créer une barre de progression visuelle
                    bar_length = 20
                    filled = int(bar_length * downloaded / total)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    
                    # Mettre à jour le message de progression de manière asynchrone
                    asyncio.create_task(self._update_progress(
                        f"{prefix}⏳ Téléchargement : {percent}% [{bar}]"
                    ))
            except Exception as e:
                logging.warning(f"⚠️ Erreur dans progress_hook: {e}")
    
    async def _update_progress(self, content):
        """Met à jour le message de progression"""
        if self.progress_msg:
            try:
                await self.progress_msg.edit(content=content)
            except Exception:
                pass  # Ignore les erreurs de rate limit

    @app_commands.command(
        name="instagram",
        description="Télécharge une vidéo Instagram et l'envoie en message privé"
    )
    @app_commands.describe(url="Le lien de partage Instagram de la vidéo")
    async def instagram(self, interaction: discord.Interaction, url: str):
        # Défère la réponse IMMÉDIATEMENT pour éviter l'expiration
        await interaction.response.defer(ephemeral=True)
        
        # Vérifier si la commande est utilisée dans le bon salon
        if (
            not hasattr(interaction.channel, "name")
            or interaction.channel.name != "▶️┃gen-instagram"
        ):
            await interaction.followup.send(
                "❌ Cette commande ne peut être utilisée que dans le salon **▶️┃gen-instagram**",
                ephemeral=True,
            )
            return
        
        logging.info(
            f"📥 Commande /instagram_beta appelée par {interaction.user.name} avec l'URL : {url}"
        )

        # Envoie une notification dans le salon indiquant l'envoi en DM
        await interaction.followup.send(
            f"📩 {interaction.user.mention}, je vais t'envoyer la vidéo en message privé.",
            ephemeral=True,
        )
        
        # Utilisation d'un sémaphore pour limiter les téléchargements simultanés
        async with self.semaphore:
            try:
                # Vérifier que c'est bien un lien Instagram
                if "instagram.com" not in url:
                    try:
                        await interaction.user.send("❌ Veuillez fournir un lien Instagram valide.")
                    except:
                        await interaction.followup.send("❌ Veuillez fournir un lien Instagram valide.", ephemeral=True)
                    return

                # Configuration yt-dlp
                temp_dir = tempfile.gettempdir()
                output_path = os.path.join(temp_dir, "instagram_video_%(id)s.%(ext)s")
                
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': output_path,
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'progress_hooks': [self.progress_hook],
                }

                # Message de disclaimer et barre de progression
                try:
                    await interaction.user.send(
                        "⚠️ **Disclaimer :**\n"
                        "• Vous êtes responsable de l'utilisation du contenu téléchargé\n"
                        "• Vous respectez les droits d'auteur et les conditions d'utilisation d'Instagram\n"
                        "• Le bot est fourni tel quel, sans garantie\n"
                        "• Vous utilisez ce service de votre plein gré et à vos propres risques"
                    )
                    self.progress_msg = await interaction.user.send("⏳ Téléchargement de la vidéo en cours : 0%")
                    self.send_to_channel = False
                    self.user_mention = ""
                except:
                    # Si impossible d'envoyer en DM, on enverra sur le salon
                    await interaction.followup.send(
                        f"{interaction.user.mention}\n⚠️ **Disclaimer :**\n"
                        "• Vous êtes responsable de l'utilisation du contenu téléchargé\n"
                        "• Vous respectez les droits d'auteur et les conditions d'utilisation d'Instagram\n"
                        "• Le bot est fourni tel quel, sans garantie\n"
                        "• Vous utilisez ce service de votre plein gré et à vos propres risques"
                    )
                    self.progress_msg = await interaction.followup.send(
                        f"{interaction.user.mention} ⏳ Téléchargement de la vidéo en cours : 0%", wait=True
                    )
                    self.send_to_channel = True
                    self.user_mention = f"{interaction.user.mention} "

                # Télécharger la vidéo
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_title = info.get('title') or 'Instagram Video'
                    video_file = ydl.prepare_filename(info)

                # Vérifier la taille du fichier
                file_size = os.path.getsize(video_file)
                max_size = 8 * 1024 * 1024  # 8 MB en octets
                
                if file_size > max_size:
                    size_mb = file_size / (1024 * 1024)
                    os.remove(video_file)
                    
                    if self.send_to_channel:
                        await interaction.followup.send(
                            f"{interaction.user.mention} ❌ La vidéo est trop volumineuse ({size_mb:.2f} MB). "
                            f"La limite est de 8 MB."
                        )
                        if self.progress_msg:
                            await self.progress_msg.delete()
                    else:
                        await interaction.user.send(
                            f"❌ La vidéo est trop volumineuse ({size_mb:.2f} MB). "
                            f"La limite est de 8 MB."
                        )
                        if self.progress_msg:
                            await self.progress_msg.edit(content="❌ Vidéo trop volumineuse.")
                    return

                # Envoyer la vidéo
                video_sent_successfully = False
                try:
                    with open(video_file, 'rb') as f:
                        discord_file = discord.File(f, filename=f"{video_title[:50]}.mp4")
                        
                        if self.send_to_channel:
                            await interaction.followup.send(
                                content=f"{interaction.user.mention} ✅ Téléchargement terminé :",
                                file=discord_file
                            )
                            if self.progress_msg:
                                await self.progress_msg.delete()
                            logging.info("✅ Vidéo Instagram envoyée sur le salon")
                            video_sent_successfully = True
                        else:
                            await interaction.user.send(
                                content="✅ Téléchargement terminé :",
                                file=discord_file
                            )
                            logging.info("✅ Vidéo Instagram envoyée en DM")
                            video_sent_successfully = True
                
                except Exception as send_error:
                    # Si l'envoi échoue, essaie l'autre méthode
                    logging.warning(f"⚠️ Échec de l'envoi : {send_error}. Tentative alternative...")
                    try:
                        with open(video_file, 'rb') as f:
                            discord_file = discord.File(f, filename=f"{video_title[:50]}.mp4")
                            
                            if self.send_to_channel:
                                # Si échec sur le salon, essaie en DM
                                await interaction.user.send(
                                    content="✅ Téléchargement terminé :",
                                    file=discord_file
                                )
                                if self.progress_msg:
                                    await self.progress_msg.delete()
                                logging.info("✅ Vidéo Instagram envoyée en DM")
                                video_sent_successfully = True
                            else:
                                # Si échec en DM, essaie sur le salon
                                await interaction.followup.send(
                                    content=f"{interaction.user.mention} ✅ Téléchargement terminé :",
                                    file=discord_file
                                )
                                if self.progress_msg:
                                    await self.progress_msg.edit(
                                        content="✅ Vidéo envoyée sur le salon (DM bloqués)"
                                    )
                                logging.info("✅ Vidéo Instagram envoyée sur le salon")
                                video_sent_successfully = True
                    except Exception as e2:
                        error_msg = f"❌ Impossible d'envoyer la vidéo : {str(e2)}"
                        if self.progress_msg:
                            await self.progress_msg.edit(content=f"{self.user_mention}{error_msg}")
                        logging.error(f"❌ Échec complet de l'envoi : {e2}")

                # Enregistrer les statistiques si l'envoi a réussi
                if video_sent_successfully:
                    try:
                        await stats_manager.record_download(
                            user_id=interaction.user.id,
                            user_name=interaction.user.name,
                            platform="instagram",
                            video_url=url,
                            video_title=video_title
                        )
                    except Exception as stats_error:
                        logging.warning(f"⚠️ Erreur lors de l'enregistrement des stats: {stats_error}")

                # Nettoyer le fichier temporaire
                if os.path.exists(video_file):
                    os.remove(video_file)
                logging.info(f"✅ Vidéo Instagram téléchargée et envoyée par {interaction.user}")

            except Exception as download_error:
                # Gestion des erreurs
                logging.error(f"❌ Erreur dans /instagram_beta: {download_error}", exc_info=True)
                try:
                    await interaction.user.send(
                        f"❌ Une erreur s'est produite : {str(download_error)}"
                    )
                except:
                    await interaction.followup.send(
                        f"❌ Une erreur s'est produite : {str(download_error)}",
                        ephemeral=True
                    )

async def setup(bot):
    await bot.add_cog(Instagram(bot))
