import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import os
import tempfile
import logging

class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="instagram_beta",
        description="Télécharge une vidéo Instagram et l'envoie sur Discord"
    )
    @app_commands.describe(url="Le lien de partage Instagram de la vidéo")
    async def instagram(self, interaction: discord.Interaction, url: str):
        # Vérifier que la commande est utilisée dans le bon salon
        if interaction.channel and interaction.channel.name != "▶️┃gen-instagram":
            await interaction.response.send_message(
                "❌ Cette commande n'est disponible que dans le salon <#▶️┃gen-instagram>.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Vérifier que c'est bien un lien Instagram
            if "instagram.com" not in url:
                await interaction.followup.send("❌ Veuillez fournir un lien Instagram valide.")
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
            }

            await interaction.followup.send("⏳ Téléchargement de la vidéo en cours...")

            # Télécharger la vidéo
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_title = info.get('title') or 'Instagram Video'
                video_file = ydl.prepare_filename(info)

            # Vérifier la taille du fichier (limite à 8 MB)
            file_size = os.path.getsize(video_file)
            max_size = 8 * 1024 * 1024  # 8 MB en octets
            
            if file_size > max_size:
                os.remove(video_file)
                await interaction.followup.send(
                    f"❌ La vidéo est trop volumineuse ({file_size / (1024 * 1024):.2f} MB). "
                    f"La limite est de 8 MB."
                )
                return

            # Envoyer le disclaimer d'abord
            disclaimer_embed = discord.Embed(
                title="⚠️ Disclaimer",
                description=(
                    "• Vous êtes responsable de l'utilisation du contenu téléchargé\n"
                    "• Vous respectez les droits d'auteur et les conditions d'utilisation d'Instagram\n"
                    "• Le bot est fourni tel quel, sans garantie\n"
                    "• Vous utilisez ce service de votre plein gré et à vos propres risques"
                ),
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=disclaimer_embed)
            
            # Puis envoyer la vidéo
            with open(video_file, 'rb') as f:
                discord_file = discord.File(f, filename=f"{video_title[:50]}.mp4")
                video_embed = discord.Embed(
                    title="📹 Vidéo Instagram",
                    description=f"**{video_title}**",
                    color=discord.Color.purple()
                )
                video_embed.set_footer(text=f"Demandé par {interaction.user.display_name}")
                
                await interaction.followup.send(embed=video_embed, file=discord_file)

            # Nettoyer le fichier temporaire
            os.remove(video_file)
            logging.info(f"✅ Vidéo Instagram téléchargée et envoyée par {interaction.user}")

        except Exception as download_error:
            # Gestion des erreurs de téléchargement yt-dlp
            if "DownloadError" in str(type(download_error)):
                await interaction.followup.send(
                    f"❌ Erreur lors du téléchargement : La vidéo n'est peut-être pas accessible ou le lien est invalide."
                )
                logging.error(f"Erreur yt-dlp: {download_error}")
            else:
                await interaction.followup.send(
                    f"❌ Une erreur s'est produite : {str(download_error)}"
                )
                logging.error(f"Erreur Instagram command: {download_error}")

async def setup(bot):
    await bot.add_cog(Instagram(bot))
