import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os
import time
import logging
from typing import Union, Any


class CrunchyrollDownloader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.semaphore = asyncio.Semaphore(2)
        self.max_file_size_mb = 8
        try:
            with open("config/config.json", "r", encoding="utf-8") as f:
                import json

                config = json.load(f)
                self.max_file_size_mb = config.get("max_discord_file_size_mb", 8)
        except Exception as e:
            print(f"⚠️ Erreur config: {e}. Valeur par défaut 8MB")

        self.semaphore = asyncio.Semaphore(2)
        self.max_file_size_mb = 8
        try:
            with open("config/config.json", "r", encoding="utf-8") as f:
                import json

                config = json.load(f)
                self.max_file_size_mb = config.get("max_discord_file_size_mb", 8)
        except Exception as e:
            print(f"⚠️ Erreur config: {e}. Valeur par défaut 8MB")

    @app_commands.command(
        name="video",
        description=(
            "Télécharge et découpe une vidéo en clips de 1 min. Sélectionnez les clips via boutons."
        ),
    )
    async def video_download(self, interaction: discord.Interaction, url: str):
        logging.info(f"📥 Commande /video par {interaction.user.name} : {url}")
        if self.semaphore._value == 0:
            await interaction.response.send_message(
                "⏳ Trop d'utilisateurs utilisent cette commande. Réessayez plus tard.",
                ephemeral=True,
            )
            return
        async with self.semaphore:
            await interaction.response.send_message(
                "📥 **Téléchargement en cours...**\n⏳ Extraction de la vidéo...",
                ephemeral=False,
            )
            initial_message = await interaction.original_response()

            async def safe_edit(**kwargs):
                content = kwargs.pop("content", None)
                view = kwargs.pop("view", None)
                try:
                    await initial_message.edit(content=content, view=view)
                    return
                except Exception as e:
                    logging.exception(f"Erreur edit initial_message: {e}")
                # Fallback: try followup, then channel.send
                try:
                    if content is None and view is None:
                        return
                    await interaction.followup.send(content=content or "", view=view)
                    return
                except Exception as e:
                    logging.exception(f"Erreur followup send fallback: {e}")
                try:
                    if hasattr(channel, "send"):
                        await channel.send(content or "", view=view)
                        return
                except Exception as e:
                    logging.exception(f"Erreur channel.send fallback: {e}")

            if not interaction.channel or not isinstance(
                interaction.channel,
                (
                    discord.TextChannel,
                    discord.DMChannel,
                    discord.Thread,
                    discord.VoiceChannel,
                ),
            ):
                await interaction.followup.send(
                    "❌ Impossible d'envoyer des messages dans ce type de canal.",
                    ephemeral=True,
                )
                return
            channel: Union[
                discord.TextChannel,
                discord.DMChannel,
                discord.Thread,
                discord.VoiceChannel,
            ] = interaction.channel
            interaction_id = str(interaction.id)
            timestamp = int(time.time())
            unique_id = f"{interaction_id}_{timestamp}"
            input_filename = f"video_{unique_id}.mp4"
            created_files = []
            try:
                ydl_opts: dict[str, Any] = {
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "outtmpl": input_filename,
                    "quiet": False,
                    "no_warnings": False,
                    "merge_output_format": "mp4",
                    "ignoreerrors": False,
                    "extract_flat": False,
                    "nocheckcertificate": True,
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    "referer": "https://www.youtube.com/",
                    "http_headers": {
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Cache-Control": "max-age=0",
                    },
                    "extractor_args": {
                        "youtube": {
                            "skip": ["dash", "hls"],
                            "player_client": ["android", "web"],
                            "player_skip": ["configs"],
                        }
                    },
                }
                try:
                    logging.info(f"🔽 Démarrage téléchargement: {url}")
                    print(f"[crunchyroll] Démarrage téléchargement: {url}")
                    with yt_dlp.YoutubeDL(
                        __import__("typing").cast(Any, ydl_opts)
                    ) as ydl:
                        info = await asyncio.to_thread(ydl.extract_info, url, download=True)
                        if info:
                            logging.info(f"✅ Vidéo extraite: {info.get('title', 'Unknown')}")
                    logging.info(f"✅ Téléchargement terminé: {input_filename}")
                    print(f"[crunchyroll] Téléchargement terminé: {input_filename}")
                except Exception as e:
                    # Gestion explicite des sites non supportés ou erreurs yt-dlp
                    err_str = str(e).lower()
                    logging.error(f"❌ Erreur yt-dlp détaillée: {e}")
                    print(f"[crunchyroll] Erreur yt-dlp: {e}")
                    
                    if "sign in to confirm" in err_str or "not a bot" in err_str or "cookies" in err_str:
                        await safe_edit(
                            content="❌ YouTube bloque le téléchargement (détection de bot).\n"
                            "💡 **Alternatives :**\n"
                            "• Essayez avec un lien d'un autre site (TikTok, Twitter, Instagram, etc.)\n"
                            "• Ou téléchargez manuellement et envoyez le fichier"
                        )
                        return
                    if "unsupported url" in err_str or "no suitable extractor" in err_str:
                        await safe_edit(
                            content="❌ Ce site n'est pas supporté par yt-dlp."
                        )
                        return
                    if "drm" in err_str or "protected" in err_str:
                        await safe_edit(
                            content="❌ Cette vidéo est protégée par DRM et ne peut pas être téléchargée."
                        )
                        return
                    if "private" in err_str or "members-only" in err_str:
                        await safe_edit(
                            content="❌ Cette vidéo est privée ou réservée aux membres."
                        )
                        return
                    if "age" in err_str and "restricted" in err_str:
                        await safe_edit(
                            content="❌ Cette vidéo a une restriction d'âge et ne peut pas être téléchargée."
                        )
                        return
                    if "unavailable" in err_str or "removed" in err_str:
                        await safe_edit(
                            content="❌ Cette vidéo n'est plus disponible ou a été supprimée."
                        )
                        return
                    await safe_edit(content=f"❌ Erreur lors du téléchargement:\n```{str(e)[:500]}```")
                    return
                if not os.path.exists(input_filename):
                    await safe_edit(
                        content="❌ Téléchargement échoué. Vérifiez l'URL ou réessayez plus tard."
                    )
                    return
                created_files.append(input_filename)
                # Analyse durée vidéo
                ffprobe_cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    input_filename,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *ffprobe_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                duration_str = stdout.decode().strip()
                duration = (
                    float(duration_str)
                    if duration_str and duration_str != "N/A"
                    else 300
                )
                total_clips = int(duration // 60) + (1 if duration % 60 > 0 else 0)
                logging.info(f"⏱ Durée vidéo: {duration:.1f}s → {total_clips} clip(s)")
                print(
                    f"[crunchyroll] Durée vidéo: {duration:.1f}s → {total_clips} clip(s)"
                )

                # Présenter une vue avec boutons pour sélectionner les clips
                class ClipButton(discord.ui.Button):
                    def __init__(self, clip_no: int, view_ref: "ClipSelectView"):
                        super().__init__(
                            label=f"Clip {clip_no}", style=discord.ButtonStyle.secondary
                        )
                        self.clip_no = clip_no
                        self.view_ref = view_ref

                    async def callback(self, interaction: discord.Interaction):
                        if interaction.user.id != self.view_ref.author.id:
                            await interaction.response.send_message(
                                "❌ Vous ne pouvez pas interagir avec cette sélection.",
                                ephemeral=True,
                            )
                            return
                        if self.clip_no in self.view_ref.selected:
                            self.view_ref.selected.remove(self.clip_no)
                            self.style = discord.ButtonStyle.secondary
                        else:
                            self.view_ref.selected.add(self.clip_no)
                            self.style = discord.ButtonStyle.success
                        # Met à jour l'étiquette avec le nombre sélectionné
                        self.label = f"Clip {self.clip_no}{' ✅' if self.clip_no in self.view_ref.selected else ''}"
                        await interaction.response.edit_message(view=self.view_ref)

                class StartButton(discord.ui.Button):
                    def __init__(self, view_ref: "ClipSelectView"):
                        super().__init__(
                            label="Démarrer", style=discord.ButtonStyle.primary
                        )
                        self.view_ref = view_ref

                    async def callback(self, interaction: discord.Interaction):
                        if interaction.user.id != self.view_ref.author.id:
                            await interaction.response.send_message(
                                "❌ Vous ne pouvez pas lancer le traitement.",
                                ephemeral=True,
                            )
                            return
                        if not self.view_ref.selected:
                            await interaction.response.send_message(
                                "❌ Aucune sélection. Cliquez sur les clips souhaités.",
                                ephemeral=True,
                            )
                            return
                        self.view_ref.confirmed = True
                        for item in list(self.view_ref.children):
                            try:
                                setattr(item, "disabled", True)
                            except Exception:
                                pass
                        await interaction.response.edit_message(
                            content="🔄 Lancement du traitement...", view=self.view_ref
                        )
                        self.view_ref.stop()

                class CancelButton(discord.ui.Button):
                    def __init__(self, view_ref: "ClipSelectView"):
                        super().__init__(
                            label="Annuler", style=discord.ButtonStyle.danger
                        )
                        self.view_ref = view_ref

                    async def callback(self, interaction: discord.Interaction):
                        if interaction.user.id != self.view_ref.author.id:
                            await interaction.response.send_message(
                                "❌ Vous ne pouvez pas annuler cette opération.",
                                ephemeral=True,
                            )
                            return
                        self.view_ref.confirmed = False
                        for item in list(self.view_ref.children):
                            try:
                                setattr(item, "disabled", True)
                            except Exception:
                                pass
                        await interaction.response.edit_message(
                            content="❌ Sélection annulée.", view=self.view_ref
                        )
                        self.view_ref.stop()

                class ClipSelectView(discord.ui.View):
                    def __init__(
                        self,
                        author: Union[discord.User, discord.Member],
                        total_clips: int,
                        timeout: int = 60,
                    ):
                        super().__init__(timeout=timeout)
                        self.author = author
                        self.total_clips = total_clips
                        self.selected: set[int] = set()
                        self.confirmed = False
                        # Ajouter boutons (respecter la limite de 25 composants Discord)
                        max_components = 25
                        reserved = 2  # Démarrer + Annuler
                        clip_limit = min(total_clips, max_components - reserved)
                        for n in range(1, clip_limit + 1):
                            self.add_item(ClipButton(n, self))
                        self.add_item(StartButton(self))
                        self.add_item(CancelButton(self))

                view = ClipSelectView(interaction.user, total_clips, timeout=120)
                select_text = (
                    f"✅ **Téléchargement terminé**\n📊 Vidéo découpée en {total_clips} clip(s).\n"
                    "Cliquez sur les boutons pour sélectionner les clips, puis 'Démarrer'."
                )
                # Si beaucoup de clips, prévenir
                if total_clips > 25:
                    select_text += "\n⚠️ Plus de 25 clips détectés — seuls les 25 premiers sont affichés."
                await safe_edit(content=select_text, view=view)
                logging.info(
                    f"🖱 Affichage sélection clips (total {total_clips}) pour {interaction.user}"
                )
                print(
                    f"[crunchyroll] Affichage sélection clips (total {total_clips}) pour {interaction.user}"
                )
                await view.wait()
                if not getattr(view, "confirmed", False):
                    # annulé ou timeout
                    await safe_edit(content="❌ Opération annulée ou expirée.")
                    logging.info("⚠️ Sélection annulée ou timeout")
                    print("[crunchyroll] Sélection annulée ou timeout")
                    return

                target_clips = sorted(view.selected)
                logging.info(f"✅ Clips sélectionnés: {target_clips}")
                print(f"[crunchyroll] Clips sélectionnés: {target_clips}")

                for count, clip_number in enumerate(target_clips, start=1):
                    start_time = (clip_number - 1) * 60
                    logging.info(
                        f"▶ Traitement clip {clip_number} (start {start_time}s)"
                    )
                    print(
                        f"[crunchyroll] Traitement clip {clip_number} (start {start_time}s)"
                    )
                    output_filename = f"cr_clip_{clip_number}_{unique_id}.mp4"
                    created_files.append(output_filename)
                    ffmpeg_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        input_filename,
                        "-ss",
                        str(start_time),
                        "-t",
                        str(min(60, duration - start_time)),
                        "-filter_complex",
                        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[main];[bg][main]overlay=(W-w)/2:(H-h)/2[out]",
                        "-map",
                        "[out]",
                        "-map",
                        "0:a?",
                        "-sn",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "medium",
                        "-crf",
                        "23",
                        "-b:v",
                        "2000k",
                        "-maxrate",
                        "2500k",
                        "-bufsize",
                        "3500k",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "128k",
                        "-avoid_negative_ts",
                        "make_zero",
                        output_filename,
                    ]
                    process = await asyncio.create_subprocess_exec(
                        *ffmpeg_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await process.communicate()
                    logging.info(
                        f"🔧 ffmpeg terminé pour clip {clip_number}, vérification fichier..."
                    )
                    print(f"[crunchyroll] ffmpeg terminé pour clip {clip_number}")
                    if (
                        os.path.exists(output_filename)
                        and os.path.getsize(output_filename) > 0
                    ):
                        file_size_mb = os.path.getsize(output_filename) / (1024 * 1024)
                        logging.info(
                            f"📦 Clip {clip_number} taille: {file_size_mb:.2f}MB"
                        )
                        print(
                            f"[crunchyroll] Clip {clip_number} taille: {file_size_mb:.2f}MB"
                        )
                        # Réencodage automatique si trop gros
                        max_attempts = 3
                        attempt = 0
                        while (
                            file_size_mb > self.max_file_size_mb
                            and attempt < max_attempts
                        ):
                            logging.info(
                                f"🔁 Recompression tentative {attempt+1} pour clip {clip_number}"
                            )
                            print(
                                f"[crunchyroll] Recompression tentative {attempt+1} pour clip {clip_number}"
                            )
                            # Calculer la durée réelle du clip
                            ffprobe_cmd = [
                                "ffprobe",
                                "-v",
                                "error",
                                "-show_entries",
                                "format=duration",
                                "-of",
                                "default=noprint_wrappers=1:nokey=1",
                                output_filename,
                            ]
                            proc = await asyncio.create_subprocess_exec(
                                *ffprobe_cmd,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                            )
                            stdout, _ = await proc.communicate()
                            clip_duration = (
                                float(stdout.decode().strip()) if stdout else 60
                            )
                            # Calcul du bitrate cible pour rester sous la limite
                            target_size_mb = self.max_file_size_mb * 0.98
                            target_bitrate = int(
                                (target_size_mb * 8 * 1024) / clip_duration
                            )
                            video_bitrate = max(
                                target_bitrate - 96, 400
                            )  # 96k pour l'audio, min 400k
                            temp_filename = f"temp_{output_filename}"
                            reduced_cmd = [
                                "ffmpeg",
                                "-y",
                                "-i",
                                output_filename,
                                "-c:v",
                                "libx264",
                                "-preset",
                                "medium",
                                "-crf",
                                "30",
                                "-b:v",
                                f"{video_bitrate}k",
                                "-maxrate",
                                f"{int(video_bitrate * 1.2)}k",
                                "-bufsize",
                                f"{int(video_bitrate * 2)}k",
                                "-c:a",
                                "aac",
                                "-b:a",
                                "96k",
                                temp_filename,
                            ]
                            proc2 = await asyncio.create_subprocess_exec(
                                *reduced_cmd,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                            )
                            await proc2.communicate()
                            if os.path.exists(temp_filename):
                                os.remove(output_filename)
                                os.rename(temp_filename, output_filename)
                                file_size_mb = os.path.getsize(output_filename) / (
                                    1024 * 1024
                                )
                                logging.info(
                                    f"✅ Recompression réussie, nouvelle taille: {file_size_mb:.2f}MB"
                                )
                                print(
                                    f"[crunchyroll] Recompression réussie, nouvelle taille: {file_size_mb:.2f}MB"
                                )
                            attempt += 1
                        if file_size_mb > self.max_file_size_mb:
                            await safe_edit(
                                content=(
                                    f"❌ Clip {clip_number} trop volumineux (> {self.max_file_size_mb}MB) "
                                    "et n'a pas pu être compressé suffisamment."
                                )
                            )
                        else:
                            # Si malgré tout le clip est >9MB, tenter une passe supplémentaire
                            HARD_LIMIT_MB = 9
                            if file_size_mb > HARD_LIMIT_MB:
                                extra_attempts = 2
                                extra_try = 0
                                while (
                                    file_size_mb > HARD_LIMIT_MB
                                    and extra_try < extra_attempts
                                ):
                                    # Recalcule la durée réelle du clip
                                    ffprobe_cmd = [
                                        "ffprobe",
                                        "-v",
                                        "error",
                                        "-show_entries",
                                        "format=duration",
                                        "-of",
                                        "default=noprint_wrappers=1:nokey=1",
                                        output_filename,
                                    ]
                                    proc = await asyncio.create_subprocess_exec(
                                        *ffprobe_cmd,
                                        stdout=asyncio.subprocess.PIPE,
                                        stderr=asyncio.subprocess.PIPE,
                                    )
                                    stdout, _ = await proc.communicate()
                                    clip_duration = (
                                        float(stdout.decode().strip()) if stdout else 60
                                    )

                                    target_size_mb = HARD_LIMIT_MB * 0.98
                                    target_bitrate = int(
                                        (target_size_mb * 8 * 1024) / clip_duration
                                    )
                                    video_bitrate = max(target_bitrate - 96, 300)

                                    temp_filename = f"extra_{output_filename}"
                                    extra_cmd = [
                                        "ffmpeg",
                                        "-y",
                                        "-i",
                                        output_filename,
                                        "-c:v",
                                        "libx264",
                                        "-preset",
                                        "slow",
                                        "-crf",
                                        "28",
                                        "-b:v",
                                        f"{video_bitrate}k",
                                        "-maxrate",
                                        f"{int(video_bitrate * 1.2)}k",
                                        "-bufsize",
                                        f"{int(video_bitrate * 2)}k",
                                        "-c:a",
                                        "aac",
                                        "-b:a",
                                        "64k",
                                        temp_filename,
                                    ]
                                    proc2 = await asyncio.create_subprocess_exec(
                                        *extra_cmd,
                                        stdout=asyncio.subprocess.PIPE,
                                        stderr=asyncio.subprocess.PIPE,
                                    )
                                    await proc2.communicate()
                                    if os.path.exists(temp_filename):
                                        os.remove(output_filename)
                                        os.rename(temp_filename, output_filename)
                                        file_size_mb = os.path.getsize(
                                            output_filename
                                        ) / (1024 * 1024)
                                    extra_try += 1
                                if file_size_mb > HARD_LIMIT_MB:
                                    await safe_edit(
                                        content=(
                                            f"❌ Clip {clip_number} trop volumineux (> {HARD_LIMIT_MB}MB) "
                                            "après tentatives de recompression."
                                        )
                                    )
                                    logging.warning(
                                        f"❌ Clip {clip_number} non compressible sous {HARD_LIMIT_MB}MB"
                                    )
                                    print(
                                        f"[crunchyroll] Clip {clip_number} non compressible sous {HARD_LIMIT_MB}MB"
                                    )
                                    # passe à la suite sans envoyer ce clip
                                    continue
                            try:
                                logging.info(
                                    f"📤 Envoi clip {clip_number} vers Discord"
                                )
                                print(
                                    f"[crunchyroll] Envoi clip {clip_number} vers Discord"
                                )
                                with open(output_filename, "rb") as f:
                                    await channel.send(
                                        f"📤 **Clip {count}/{len(target_clips)}** ({file_size_mb:.1f}MB)",
                                        file=discord.File(
                                            f,
                                            filename=os.path.basename(output_filename),
                                        ),
                                    )
                                logging.info(f"✅ Clip {clip_number} envoyé")
                                print(f"[crunchyroll] Clip {clip_number} envoyé")
                            except Exception as e:
                                logging.error(f"Erreur envoi clip {clip_number}: {e}")
                                print(
                                    f"[crunchyroll] Erreur envoi clip {clip_number}: {e}"
                                )
                                await safe_edit(
                                    content=f"❌ Erreur envoi clip {clip_number}: {e}"
                                )
                        await asyncio.sleep(0.3)
                        if os.path.exists(output_filename):
                            try:
                                os.remove(output_filename)
                                created_files.remove(output_filename)
                            except Exception:
                                pass
                        else:
                            await safe_edit(
                                content=f"❌ Erreur création clip {clip_number}"
                            )
                    await asyncio.sleep(0.5)
                await safe_edit(
                    content=(
                        f"✅ **Traitement terminé**\n📊 {len(target_clips)} clip(s) générés et envoyés."
                    )
                )
                logging.info(
                    f"✔️ Traitement terminé pour {interaction.user}. Clips envoyés: {len(target_clips)}"
                )
                print(
                    f"[crunchyroll] Traitement terminé. Clips envoyés: {len(target_clips)}"
                )
            except Exception as e:
                logging.exception(f"Erreur critique: {e}")
                print(f"[crunchyroll] Erreur critique: {e}")
                await safe_edit(content=f"❌ **Erreur critique**\n{e}")
            finally:
                await asyncio.sleep(1)
                for filename in created_files:
                    if os.path.exists(filename):
                        try:
                            os.remove(filename)
                            logging.info(f"🧹 Suppression fichier: {filename}")
                            print(f"[crunchyroll] Suppression fichier: {filename}")
                        except Exception:
                            logging.warning(f"Échec suppression fichier: {filename}")
                            print(
                                f"[crunchyroll] Échec suppression fichier: {filename}"
                            )


# Fonction setup obligatoire
async def setup(bot):
    await bot.add_cog(CrunchyrollDownloader(bot))
    print("✅ Extension Crunchyroll chargée")
