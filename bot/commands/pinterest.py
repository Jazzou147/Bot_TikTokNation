import discord
from discord.ext import commands
import aiohttp
import re
import os
import json
import logging
import asyncio


# Définition de la classe Pinterest en tant que "Cog" pour le bot Discord
class Pinterest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Limite le nombre de téléchargements simultanés à 2
        self.semaphore = asyncio.Semaphore(2)
        # Charger la configuration
        self.max_file_size_mb = 8  # Valeur par défaut
        try:
            with open("config/config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                self.max_file_size_mb = config.get("max_discord_file_size_mb", 8)
        except Exception as e:
            print(
                f"⚠️ Erreur lors de la lecture de la config: {e}. Utilisation de la valeur par défaut (8MB)"
            )

    # Commande slash pour télécharger une vidéo Pinterest
    @discord.app_commands.command(
        name="pinterest",
        description="Télécharge une vidéo Pinterest en qualité maximale",
    )
    async def pinterest_download(self, interaction: discord.Interaction, url: str):
        # Vérifier si la commande est utilisée dans le bon salon
        if (
            not hasattr(interaction.channel, "name")
            or interaction.channel.name != "🎨┃gen-pinterest"
        ):
            await interaction.response.send_message(
                "❌ Cette commande ne peut être utilisée que dans le salon **🎨┃gen-pinterest**",
                ephemeral=True,
            )
            return

        # Défère la réponse pour indiquer que le bot traite la commande
        await interaction.response.defer()
        logging.info(
            f"📥 Commande /pinterest appelée par {interaction.user.name} avec l'URL : {url}"
        )

        # Envoie une notification initiale dans le salon (on la capture pour suppression plus tard)
        initial_msg = await interaction.followup.send(
            f"📩 {interaction.user.mention}, la vidéo sera publiée dans ce salon si possible.",
            wait=True,
        )

        # Nom affichable du salon en évitant l'accès direct à `mention` (DM n'a pas cet attribut)
        channel_mention = getattr(
            interaction.channel, "mention", interaction.user.mention
        )

        # Utilisation d'un sémaphore pour limiter les téléchargements simultanés
        async with self.semaphore:
            # Configuration des en-têtes pour éviter les blocages
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with aiohttp.ClientSession(headers=headers) as session:
                # Résolution des liens raccourcis (ex. pin.it)
                if re.match(r"^https?://pin\.it/", url):
                    try:
                        # Suit les redirections multiples (pin.it -> api.pinterest.com -> pinterest.com)
                        async with session.get(
                            url, allow_redirects=True, max_redirects=10
                        ) as resp:
                            url = str(resp.url)
                            logging.info(f"🔗 Lien raccourci résolu : {url}")

                            # Vérifie que l'URL finale est bien un lien Pinterest valide
                            if not re.match(
                                r"^https?://([a-z]+\.)?pinterest\.[a-z]+/pin/", url
                            ):
                                logging.error(
                                    f"❌ L'URL résolue n'est pas un lien Pinterest valide : {url}"
                                )
                                await interaction.followup.send(
                                    "❌ Le lien raccourci ne pointe pas vers une épingle Pinterest valide."
                                )
                                return
                    except Exception as e:
                        logging.error(
                            f"❌ Erreur de résolution du lien raccourci : {e}"
                        )
                        await interaction.followup.send(
                            "❌ Impossible de résoudre le lien raccourci Pinterest."
                        )
                        return

                # Vérifie si l'URL est un lien Pinterest valide
                if not re.match(r"^https?://([a-z]+\.)?pinterest\.[a-z]+/pin/", url):
                    await interaction.followup.send("❌ Lien Pinterest invalide.")
                    return

                try:
                    # Récupère le contenu de la page Pinterest
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            await interaction.followup.send(
                                "⚠️ Impossible d'accéder au lien."
                            )
                            return
                        page = await resp.text()

                    # Recherche des sources vidéo dans le HTML
                    video_sources = re.findall(r'<source[^>]+src="([^"]+)"[^>]*>', page)
                    video_url = None
                    if video_sources:
                        # Si des sources vidéo HTML sont trouvées, utilise la dernière
                        video_url = video_sources[-1]
                        logging.info(f"🎥 Source vidéo HTML détectée : {video_url}")
                    else:
                        # Si aucune source HTML n'est trouvée, recherche dans les données JSON
                        json_match = re.search(
                            r'<script data-test-id="video-snippet"[^>]*>(.*?)</script>',
                            page,
                        )
                        if json_match:
                            try:
                                json_data = json.loads(json_match.group(1))
                                variants = json_data.get("videoVariants", [])
                                if variants:
                                    # Trie les variantes par hauteur (résolution) décroissante
                                    sorted_variants = sorted(
                                        variants,
                                        key=lambda v: v.get("height", 0),
                                        reverse=True,
                                    )
                                    video_url = sorted_variants[0].get("url")
                                    logging.info(
                                        f"🎥 Source vidéo JSON détectée : {video_url}"
                                    )
                                else:
                                    # Utilise d'autres champs si disponibles
                                    video_url = json_data.get(
                                        "contentUrl"
                                    ) or json_data.get("embedUrl")
                            except Exception as e:
                                logging.warning(f"⚠️ Erreur JSON : {e}")

                    # Si aucune source vidéo n'est trouvée, notifie l'utilisateur
                    if not video_url:
                        await interaction.followup.send(
                            "⚠️ Aucun média détecté sur ce lien."
                        )
                        return

                    # Téléchargement de la vidéo avec suivi de progression
                    progress_msg: discord.WebhookMessage = (
                        await interaction.followup.send(
                            "⏳ Téléchargement de la vidéo en cours : 0%", wait=True
                        )
                    )
                    async with session.get(video_url) as video_resp:
                        file_size = int(video_resp.headers.get("Content-Length", 0))
                        chunk_size = 1024 * 64  # Taille des chunks (64 Ko)
                        downloaded = 0
                        video_data = bytearray()

                        # Télécharge la vidéo par morceaux
                        while True:
                            chunk = await video_resp.content.read(chunk_size)
                            if not chunk:
                                break
                            video_data.extend(chunk)
                            downloaded += len(chunk)

                            # Met à jour la progression en pourcentage ou en Mo
                            if file_size:
                                percent = int(downloaded / file_size * 100)
                                await progress_msg.edit(
                                    content=f"⏳ Téléchargement : {percent}%"
                                )
                            else:
                                size_mb = round(downloaded / 1024 / 1024, 2)
                                await progress_msg.edit(
                                    content=f"⏳ Téléchargement : {size_mb} Mo"
                                )

                    # Vérifie si la vidéo dépasse la limite de taille de Discord
                    if len(video_data) > self.max_file_size_mb * 1024 * 1024:
                        size_mb = round(len(video_data) / 1024 / 1024, 2)
                        # Publie le lien direct dans le salon si la vidéo est trop lourde
                        await interaction.followup.send(
                            content=f"📎 La vidéo est trop lourde pour Discord ({size_mb} Mo).\nVoici le lien direct : {video_url}"
                        )
                        await progress_msg.edit(
                            content=f"📬 Lien direct publié dans le salon {channel_mention}"
                        )
                        logging.info("📎 Lien direct publié dans le salon")

                        # Supprime les messages précédents (initial + progression)
                        try:
                            await initial_msg.delete()
                        except Exception:
                            pass
                        try:
                            await progress_msg.delete()
                        except Exception:
                            pass

                        return

                    # Sauvegarde temporairement la vidéo sur le disque
                    with open("temp.mp4", "wb") as f:
                        f.write(video_data)

                        try:
                            # Envoie la vidéo directement dans le salon où la commande a été utilisée
                            await interaction.followup.send(
                                content="✅ Téléchargement terminé :",
                                file=discord.File("temp.mp4"),
                            )

                            await progress_msg.edit(
                                content=f"📬 Vidéo publiée dans le salon {channel_mention}"
                            )
                            logging.info("✅ Vidéo publiée dans le salon avec succès")

                            # Supprime les messages précédents (initial + progression)
                            try:
                                await initial_msg.delete()
                            except Exception:
                                pass
                            try:
                                await progress_msg.delete()
                            except Exception:
                                pass

                        except Exception as e:
                            # Si l'envoi dans le salon échoue, notifie l'utilisateur
                            await progress_msg.edit(
                                content=f"❌ Impossible de publier la vidéo dans le salon : {e}"
                            )
                            logging.warning(f"❌ Échec de l'envoi dans le salon : {e}")

                    # Supprime le fichier temporaire après l'envoi
                    os.remove("temp.mp4")

                except Exception as e:
                    # Gère les erreurs et notifie l'utilisateur
                    logging.error(f"❌ Erreur dans /pindownload : {e}", exc_info=True)
                    await interaction.followup.send(
                        f"❌ Une erreur est survenue : {str(e)}"
                    )


# Fonction pour charger le "Cog" dans le bot
async def setup(bot):
    await bot.add_cog(Pinterest(bot))
    logging.info("✅ Extension 'Pinterest' chargée")
