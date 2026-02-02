import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os
import time
import subprocess
import aiohttp
import shutil
import json

FFMPEG_PATH = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg") 
FFPROBE_PATH = os.environ.get("FFPROBE_PATH") or shutil.which("ffprobe") 

if not FFMPEG_PATH or not FFPROBE_PATH: 
    print("⚠️ ffmpeg ou ffprobe introuvable. Vérifiez l'installation ou définissez FFMPEG_PATH/FFPROBE_PATH.") 

else: 
    print(f"✅ ffmpeg trouvé: {FFMPEG_PATH}") 
    print(f"✅ ffprobe trouvé: {FFPROBE_PATH}")

def get_browser_for_cookies():
    """Détecte le navigateur disponible pour extraire les cookies."""
    import platform
    
    # Sur Linux (Docker), l'extraction automatique ne fonctionne pas
    if platform.system() == 'Linux':
        print("ℹ️  Environnement Linux détecté - auto-extraction de cookies désactivée")
        print("   Utilisez un fichier de cookies exporté (voir YOUTUBE_COOKIES.md)")
        return None
    
    # Sur Windows/Mac, essayer de détecter les navigateurs
    # Firefox est plus fiable sur Windows (pas de problème DPAPI)
    browsers = ['firefox', 'chrome', 'edge', 'brave', 'opera', 'safari']
    for browser in browsers:
        try:
            # Test simple sans connexion réseau
            test_opts = {
                'cookiesfrombrowser': (browser,),
                'quiet': True,
                'no_warnings': True,
            }
            # Juste tester si le navigateur existe, pas de connexion
            with yt_dlp.YoutubeDL(test_opts) as ydl:
                print(f"✅ Navigateur détecté pour cookies: {browser}")
                return browser
        except Exception as e:
            error_msg = str(e).lower()
            # Ignorer les erreurs connues
            if 'unsupported platform' in error_msg or 'failed to load' in error_msg:
                continue
    
    print("⚠️  Aucun navigateur détecté pour l'extraction automatique des cookies")
    print("   Sur Docker/Linux, utilisez un fichier de cookies exporté")
    return None

def load_youtube_config():
    """Charge la configuration YouTube depuis config.json."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('youtube', {})
    except Exception as e:
        print(f"⚠️ Impossible de charger la config YouTube: {e}")
        return {}

# Charger la config YouTube
YOUTUBE_CONFIG = load_youtube_config()
COOKIES_FILE = YOUTUBE_CONFIG.get('cookies_file')
PREFERRED_BROWSER = YOUTUBE_CONFIG.get('preferred_browser')
# Ne pas auto-détecter au démarrage pour éviter les erreurs sur Docker/Linux
AUTO_BROWSER = None

# Vérifier et mettre à jour yt-dlp si nécessaire
try:
    print("🔄 Vérification de la version de yt-dlp...")
    subprocess.run(
        ["pip", "install", "--upgrade", "yt-dlp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    print("✅ yt-dlp est à jour")
except Exception as e:
    print(f"⚠️ Impossible de mettre à jour yt-dlp : {e}")

try:
    import pysrt

    HAS_PYSRT = True
except ImportError:
    HAS_PYSRT = False
    print("⚠️ pysrt non installé. Installation automatique...")

    subprocess.check_call(["pip", "install", "pysrt"])
    import pysrt

    HAS_PYSRT = True


class TikTokify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.semaphore = asyncio.Semaphore(2)

    async def safe_edit_message(self, message, content, channel):
        """Édite un message de manière sécurisée, envoie dans le canal si le token expire"""
        try:
            await message.edit(content=content)
        except discord.errors.HTTPException as e:
            if e.code == 50027:  # Invalid Webhook Token
                # Le token a expiré, envoyer un nouveau message dans le canal
                try:
                    if hasattr(channel, "send"):
                        await channel.send(content)
                except:
                    pass
            else:
                # Ignorer les autres erreurs
                pass
        except:
            # Ignorer toutes les autres erreurs
            pass

    async def upload_to_catbox(self, file_path: str) -> str | None:
        """Upload un fichier sur catbox.moe et retourne l'URL"""
        try:
            async with aiohttp.ClientSession() as session:
                with open(file_path, "rb") as f:
                    form = aiohttp.FormData()
                    form.add_field("reqtype", "fileupload")
                    form.add_field(
                        "fileToUpload", f, filename=os.path.basename(file_path)
                    )

                    async with session.post(
                        "https://catbox.moe/user/api.php", data=form
                    ) as resp:
                        if resp.status == 200:
                            url = await resp.text()
                            return url.strip()
                        else:
                            return None
        except Exception as e:
            print(f"❌ Erreur upload catbox: {e}")
            return None

    @app_commands.command(
        name="youtube",
        description="Télécharge et découpe une vidéo YouTube en clips TikTok",
    )
    async def yt_download(
        self,
        interaction: discord.Interaction,
        video_url: str,
        sous_titres: bool = False,
    ):
        # Vérifier si la commande est utilisée dans le bon salon
        if (
            not hasattr(interaction.channel, "name")
            or interaction.channel.name != "▶️┃gen-youtube"
        ):
            await interaction.response.send_message(
                "❌ Cette commande ne peut être utilisée que dans le salon **▶️┃gen-youtube**",
                ephemeral=True,
            )
            return

        # Vérifier si le semaphore permet encore des téléchargements
        if self.semaphore._value == 0:
            await interaction.response.send_message(
                "⏳ Trop d'utilisateurs utilisent cette commande en ce moment. Veuillez réessayer dans quelques instants.",
                ephemeral=False,
            )
            return

        async with self.semaphore:
            await interaction.response.send_message(
                "📥 **Téléchargement en cours...**\n⏳ Extraction de la vidéo YouTube...",
                ephemeral=False,
            )

            # Récupérer le message pour le modifier plus tard
            initial_message = await interaction.original_response()

            interaction_id = str(interaction.id)
            timestamp = int(time.time())
            unique_id = f"{interaction_id}_{timestamp}"
            input_filename = f"video_{unique_id}.mp4"
            created_files = []  # Liste pour tracker tous les fichiers créés

            try:
                ydl_opts = {
                    "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best[height<=720]/best",
                    "outtmpl": input_filename,
                    "quiet": True,
                    "merge_output_format": "mp4",
                    "writesubtitles": sous_titres,
                    "writeautomaticsub": sous_titres,
                    "subtitleslangs": ["fr", "en"] if sous_titres else [],
                    "subtitlesformat": "srt" if sous_titres else None,
                    "ignoreerrors": True,  # Ignorer les erreurs de sous-titres
                    "no_warnings": True,  # Réduire les warnings
                    "sleep_interval": 1,  # Délai pour éviter le rate limiting
                    "max_sleep_interval": 3,
                    "embed_subs": False,  # NE PAS intégrer les sous-titres dans la vidéo
                    "writeinfojson": False,  # Pas besoin du fichier info
                    # Options pour contourner l'erreur 403
                    "http_headers": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Accept-Encoding": "gzip, deflate",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    },
                    "extractor_args": {
                        "youtube": {
                            "player_client": ["android", "web"],
                            "player_skip": ["webpage", "configs"],
                        }
                    },
                    "nocheckcertificate": True,
                    "retries": 10,
                    "fragment_retries": 10,
                    "skip_unavailable_fragments": True,
                }
                
                # Ajouter l'authentification par cookies pour contourner la protection anti-bot
                if COOKIES_FILE and os.path.exists(COOKIES_FILE):
                    print(f"🍪 Utilisation du fichier cookies: {COOKIES_FILE}")
                    ydl_opts["cookiefile"] = COOKIES_FILE
                elif PREFERRED_BROWSER:
                    print(f"🍪 Utilisation des cookies du navigateur: {PREFERRED_BROWSER}")
                    ydl_opts["cookiesfrombrowser"] = (PREFERRED_BROWSER,)
                else:
                    # Détecter dynamiquement au moment du téléchargement
                    detected_browser = get_browser_for_cookies()
                    if detected_browser:
                        print(f"🍪 Utilisation des cookies du navigateur: {detected_browser}")
                        ydl_opts["cookiesfrombrowser"] = (detected_browser,)
                    else:
                        print("ℹ️  Aucun cookie d'authentification configuré")
                        print("   En cas d'erreur, consultez YOUTUBE_COOKIES.md")

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        await asyncio.to_thread(ydl.download, [video_url])
                    except Exception as e:
                        # Si le téléchargement avec le format spécifique échoue, essayer un format plus simple
                        if (
                            "format" in str(e).lower()
                            or "not available" in str(e).lower()
                        ):
                            print(f"⚠️ Erreur format : {e}")
                            print("🔄 Tentative avec un format plus simple...")

                            # Fallback avec format plus simple
                            ydl_opts_fallback = ydl_opts.copy()
                            ydl_opts_fallback["format"] = "best[height<=720]/best"
                            ydl_opts_fallback["writesubtitles"] = False
                            ydl_opts_fallback["writeautomaticsub"] = False

                            with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl_fallback:
                                await asyncio.to_thread(
                                    ydl_fallback.download, [video_url]
                                )

                            # Télécharger les sous-titres séparément si demandés
                            if sous_titres:
                                try:
                                    ydl_opts_subs = {
                                        "writesubtitles": True,
                                        "writeautomaticsub": True,
                                        "subtitleslangs": ["fr", "en"],
                                        "subtitlesformat": "srt",
                                        "skip_download": True,
                                        "outtmpl": input_filename,
                                        "quiet": True,
                                        "ignoreerrors": True,
                                    }
                                    with yt_dlp.YoutubeDL(ydl_opts_subs) as ydl_subs:
                                        await asyncio.to_thread(
                                            ydl_subs.download, [video_url]
                                        )
                                except Exception as sub_error:
                                    print(
                                        f"⚠️ Impossible de télécharger les sous-titres : {sub_error}"
                                    )
                        # Si le téléchargement avec sous-titres échoue, réessayer sans
                        elif sous_titres and "subtitle" in str(e).lower():
                            print(f"⚠️ Erreur sous-titres : {e}")
                            print("🔄 Téléchargement sans sous-titres...")

                            ydl_opts_no_subs = ydl_opts.copy()
                            ydl_opts_no_subs["writesubtitles"] = False
                            ydl_opts_no_subs["writeautomaticsub"] = False

                            with yt_dlp.YoutubeDL(ydl_opts_no_subs) as ydl_no_subs:
                                await asyncio.to_thread(
                                    ydl_no_subs.download, [video_url]
                                )
                        else:
                            raise e

                created_files.append(input_filename)  # Ajouter le fichier à la liste

                # Chercher les fichiers de sous-titres téléchargés
                subtitle_file = None
                if sous_titres:
                    for lang in ["fr", "en"]:
                        potential_subtitle = input_filename.replace(
                            ".mp4", f".{lang}.srt"
                        )
                        if os.path.exists(potential_subtitle):
                            subtitle_file = potential_subtitle
                            created_files.append(subtitle_file)
                            break

                    # Chercher aussi les sous-titres automatiques
                    if not subtitle_file:
                        potential_subtitle = input_filename.replace(".mp4", ".srt")
                        if os.path.exists(potential_subtitle):
                            subtitle_file = potential_subtitle
                            created_files.append(subtitle_file)

                    # Traiter le fichier SRT avec pysrt SEULEMENT si on a trouvé un fichier
                    if subtitle_file and HAS_PYSRT and os.path.exists(subtitle_file):
                        processed_subtitle = f"clean_{os.path.basename(subtitle_file)}"
                        created_files.append(processed_subtitle)

                        try:
                            # Charger le fichier SRT avec pysrt
                            subs = pysrt.open(subtitle_file, encoding="utf-8")
                        except:
                            try:
                                subs = pysrt.open(subtitle_file, encoding="latin-1")
                            except Exception as e:
                                print(f"❌ Erreur lecture SRT: {e}")
                                subs = []

                        # Nettoyer et optimiser les sous-titres avec gestion des chevauchements
                        if subs:  # Seulement si on a des sous-titres à traiter
                            cleaned_subs = pysrt.SubRipFile()

                            for i, sub in enumerate(subs):
                                # Fusionner toutes les lignes en une seule
                                text = sub.text.replace("\n", " ").replace("\r", " ")
                                # Nettoyer les balises HTML/XML
                                import re

                                text = re.sub(r"<[^>]+>", "", text)
                                # Limiter la longueur pour éviter le débordement
                                if len(text) > 60:
                                    text = text[:57] + "..."

                                # Ajuster les timings pour éviter les chevauchements
                                start_time = sub.start
                                end_time = sub.end

                                # Si ce n'est pas le premier sous-titre, vérifier le chevauchement
                                if i > 0 and len(cleaned_subs) > 0:
                                    previous_sub = cleaned_subs[-1]
                                    # Si le sous-titre actuel commence avant que le précédent se termine
                                    if start_time < previous_sub.end:
                                        # Terminer le précédent 0.5 seconde avant le début du nouveau
                                        gap = pysrt.SubRipTime(
                                            0, 0, 0, 500
                                        )  # 0.5 seconde
                                        if start_time > gap:
                                            previous_sub.end = start_time - gap
                                        else:
                                            previous_sub.end = start_time

                                # Créer un nouveau sous-titre propre avec les timings ajustés
                                clean_sub = pysrt.SubRipItem(
                                    index=len(cleaned_subs) + 1,
                                    start=start_time,
                                    end=end_time,
                                    text=text.strip(),
                                )
                                if (
                                    clean_sub.text
                                ):  # Ajouter seulement s'il y a du texte
                                    cleaned_subs.append(clean_sub)

                            # Sauvegarder le fichier nettoyé seulement s'il y a des sous-titres
                            if cleaned_subs:
                                cleaned_subs.save(processed_subtitle, encoding="utf-8")
                                subtitle_file = (
                                    processed_subtitle  # Utiliser le fichier nettoyé
                                )
                            else:
                                subtitle_file = None  # Pas de sous-titres valides

                # Analyser la durée de la vidéo
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
                stdout, stderr = await proc.communicate()
                duration_str = stdout.decode().strip()

                # Vérifier si ffprobe a retourné une durée valide
                if not duration_str or duration_str == "N/A":
                    print(f"Erreur ffprobe: {stderr.decode()}")
                    # Utiliser une durée par défaut si ffprobe échoue
                    duration = 300  # 5 minutes par défaut
                    print("Utilisation de la durée par défaut: 300s")
                else:
                    try:
                        duration = float(duration_str)
                    except ValueError:
                        print(f"Impossible de convertir la durée: '{duration_str}'")
                        duration = 300  # 5 minutes par défaut
                        print("Utilisation de la durée par défaut: 300s")

                total_clips = int(duration // 60) + (1 if duration % 60 > 0 else 0)

                # Mise à jour du message principal avec les informations finales
                if sous_titres:
                    if subtitle_file:
                        status_message = f"✅ **Téléchargement terminé**\n📊 Analyse : {total_clips} clip(s) de 60s à traiter\n📝 Sous-titres : {os.path.basename(subtitle_file)}\n\n🔄 **Traitement en cours...**"
                    else:
                        status_message = f"✅ **Téléchargement terminé**\n📊 Analyse : {total_clips} clip(s) de 60s à traiter\n⚠️ Sous-titres non disponibles\n\n🔄 **Traitement en cours...**"
                else:
                    status_message = f"✅ **Téléchargement terminé**\n📊 Analyse : {total_clips} clip(s) de 60s à traiter\n\n🔄 **Traitement en cours...**"

                await self.safe_edit_message(
                    initial_message, status_message, interaction.channel
                )
                await asyncio.sleep(0.5)

                # Liste pour stocker les clips traités
                processed_clips = []

                for i in range(total_clips):
                    start_time = i * 60
                    output_filename = f"clip_{i+1}_{unique_id}.mp4"
                    created_files.append(
                        output_filename
                    )  # Ajouter le fichier à la liste
                    progress = int(((i + 1) / total_clips) * 100)

                    # Calculer la durée réelle pour ce clip
                    remaining_duration = duration - start_time
                    clip_duration = min(60, remaining_duration)

                    # Mise à jour du message principal avec la progression
                    if sous_titres:
                        if subtitle_file:
                            progress_message = f"✅ **Téléchargement terminé**\n📊 Analyse : {total_clips} clip(s) de 60s à traiter\n📝 Sous-titres : {os.path.basename(subtitle_file)}\n\n✂️ **Traitement : {progress}%** ({i+1}/{total_clips})"
                        else:
                            progress_message = f"✅ **Téléchargement terminé**\n📊 Analyse : {total_clips} clip(s) de 60s à traiter\n⚠️ Sous-titres non disponibles\n\n✂️ **Traitement : {progress}%** ({i+1}/{total_clips})"
                    else:
                        progress_message = f"✅ **Téléchargement terminé**\n📊 Analyse : {total_clips} clip(s) de 60s à traiter\n\n✂️ **Traitement : {progress}%** ({i+1}/{total_clips})"

                    await self.safe_edit_message(
                        initial_message, progress_message, interaction.channel
                    )

                    # Construire la commande FFmpeg avec sous-titres optimisés
                    if subtitle_file and sous_titres:
                        # Utiliser le fichier SRT nettoyé avec pysrt
                        ffmpeg_cmd = [
                            "ffmpeg",
                            "-y",
                            "-i",
                            input_filename,
                            "-ss",
                            str(start_time),
                            "-t",
                            str(clip_duration),
                            "-filter_complex",
                            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,subtitles='{subtitle_file.replace(chr(92), '/')}':force_style='FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Shadow=0,Bold=1,Alignment=2'[main];[bg][main]overlay=(W-w)/2:(H-h)/2[out]",
                            "-map",
                            "[out]",
                            "-map",
                            "0:a?",
                            "-sn",  # Supprimer tous les sous-titres de la source
                            "-c:v",
                            "libx264",
                            "-preset",
                            "medium",
                            "-crf",
                            "23",
                            "-b:v",
                            "1400k",
                            "-maxrate",
                            "1800k",
                            "-bufsize",
                            "2500k",
                            "-c:a",
                            "aac",
                            "-b:a",
                            "96k",
                            "-avoid_negative_ts",
                            "make_zero",
                            output_filename,
                        ]
                    else:
                        # Sans sous-titres - version propre
                        ffmpeg_cmd = [
                            "ffmpeg",
                            "-y",
                            "-i",
                            input_filename,
                            "-ss",
                            str(start_time),
                            "-t",
                            str(clip_duration),
                            "-filter_complex",
                            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[main];[bg][main]overlay=(W-w)/2:(H-h)/2[out]",
                            "-map",
                            "[out]",
                            "-map",
                            "0:a?",
                            "-sn",  # Supprimer tous les sous-titres de la source
                            "-c:v",
                            "libx264",
                            "-preset",
                            "medium",
                            "-crf",
                            "23",
                            "-b:v",
                            "1400k",
                            "-maxrate",
                            "1800k",
                            "-bufsize",
                            "2500k",
                            "-c:a",
                            "aac",
                            "-b:a",
                            "96k",
                            "-avoid_negative_ts",
                            "make_zero",
                            output_filename,
                        ]

                    process = await asyncio.create_subprocess_exec(
                        *ffmpeg_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await process.communicate()

                    if process.returncode != 0:
                        error_msg = stderr.decode() if stderr else "Erreur inconnue"
                        # Mettre à jour le message principal avec l'erreur
                        error_message = f"❌ **Erreur lors du traitement**\nClip {i+1}: {error_msg[:100]}..."
                        await self.safe_edit_message(
                            initial_message, error_message, interaction.channel
                        )
                        await asyncio.sleep(2)
                        continue

                    if (
                        os.path.exists(output_filename)
                        and os.path.getsize(output_filename) > 0
                    ):
                        file_size_mb = os.path.getsize(output_filename) / (1024 * 1024)

                        # Vérifier la durée réelle du clip
                        duration_cmd = [
                            "ffprobe",
                            "-v",
                            "error",
                            "-show_entries",
                            "format=duration",
                            "-of",
                            "default=noprint_wrappers=1:nokey=1",
                            output_filename,
                        ]
                        duration_proc = await asyncio.create_subprocess_exec(
                            *duration_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        duration_stdout, _ = await duration_proc.communicate()
                        clip_duration = float(duration_stdout.decode().strip())

                        # Compression progressive pour garantir une taille max de 10 Mo
                        max_attempts = 3
                        attempt = 0
                        target_size_mb = 10.0

                        while file_size_mb > target_size_mb and attempt < max_attempts:
                            attempt += 1
                            temp_filename = f"temp_{attempt}_{output_filename}"
                            created_files.append(temp_filename)

                            # Calculer les paramètres en fonction de la tentative
                            if attempt == 1:
                                crf, bitrate, maxrate, bufsize, audio_bitrate = (
                                    "26",
                                    "1000k",
                                    "1200k",
                                    "1600k",
                                    "96k",
                                )
                            elif attempt == 2:
                                crf, bitrate, maxrate, bufsize, audio_bitrate = (
                                    "28",
                                    "800k",
                                    "1000k",
                                    "1400k",
                                    "80k",
                                )
                            else:
                                crf, bitrate, maxrate, bufsize, audio_bitrate = (
                                    "30",
                                    "600k",
                                    "800k",
                                    "1200k",
                                    "64k",
                                )

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
                                crf,
                                "-b:v",
                                bitrate,
                                "-maxrate",
                                maxrate,
                                "-bufsize",
                                bufsize,
                                "-c:a",
                                "aac",
                                "-b:a",
                                audio_bitrate,
                                temp_filename,
                            ]

                            process = await asyncio.create_subprocess_exec(
                                *reduced_cmd,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                            )
                            await process.communicate()

                            if os.path.exists(temp_filename):
                                os.remove(output_filename)
                                os.rename(temp_filename, output_filename)
                                file_size_mb = os.path.getsize(output_filename) / (
                                    1024 * 1024
                                )
                            else:
                                break

                        # Stocker les informations du clip pour envoi ultérieur
                        processed_clips.append(
                            {
                                "filename": output_filename,
                                "size_mb": file_size_mb,
                                "index": i + 1,
                            }
                        )
                        print(
                            f"✅ Clip {i+1}/{total_clips} traité : {file_size_mb:.1f}MB"
                        )
                    else:
                        # Log l'erreur mais continue
                        print(f"⚠️ Erreur : Clip {i+1} - Fichier introuvable ou vide")
                    await asyncio.sleep(0.2)

                # Envoyer tous les clips traités
                if processed_clips:
                    upload_message = f"✅ **Traitement terminé**\n📤 **Envoi de {len(processed_clips)} clip(s)...**"
                    await self.safe_edit_message(
                        initial_message, upload_message, interaction.channel
                    )

                    # Envoyer tous les clips
                    # Vérifier que le canal est un TextChannel, VoiceChannel, Thread ou StageChannel
                    channel = interaction.channel
                    if not isinstance(
                        channel,
                        (
                            discord.TextChannel,
                            discord.VoiceChannel,
                            discord.Thread,
                            discord.StageChannel,
                        ),
                    ):
                        print("❌ Canal non compatible pour l'envoi de messages")
                        await self.safe_edit_message(
                            initial_message,
                            "❌ **Erreur**: Ce type de canal ne supporte pas l'envoi de fichiers",
                            interaction.channel,
                        )
                        return

                    for clip_info in processed_clips:
                        try:
                            if os.path.exists(clip_info["filename"]):
                                file_size_mb = clip_info["size_mb"]

                                # Si le fichier dépasse 10 Mo, l'uploader sur catbox.moe
                                if file_size_mb > 10.0:
                                    print(
                                        f"🔄 Upload clip {clip_info['index']} sur catbox.moe ({file_size_mb:.1f}MB)..."
                                    )
                                    url: str | None = await self.upload_to_catbox(
                                        clip_info["filename"]
                                    )

                                    if url is not None:
                                        await channel.send(
                                            f"📤 **Clip {clip_info['index']}/{total_clips}** ({file_size_mb:.1f}MB)\n"
                                            f"⚠️ Fichier trop volumineux pour Discord\n"
                                            f"🔗 **Téléchargement :** {url}"
                                        )
                                        print(
                                            f"✅ Clip {clip_info['index']} uploadé : {url}"
                                        )
                                    else:
                                        await channel.send(
                                            f"❌ **Clip {clip_info['index']}/{total_clips}** - Erreur d'upload ({file_size_mb:.1f}MB)"
                                        )
                                        print(
                                            f"❌ Échec upload clip {clip_info['index']}"
                                        )
                                else:
                                    # Envoi normal pour les fichiers < 10 Mo
                                    with open(clip_info["filename"], "rb") as f:
                                        await channel.send(
                                            f"📤 **Clip {clip_info['index']}/{total_clips}** ({file_size_mb:.1f}MB)",
                                            file=discord.File(
                                                f,
                                                filename=os.path.basename(
                                                    clip_info["filename"]
                                                ),
                                            ),
                                        )
                                    print(f"📤 Clip {clip_info['index']} envoyé")

                                await asyncio.sleep(0.3)
                        except Exception as e:
                            print(f"❌ Erreur envoi clip {clip_info['index']}: {e}")

                    # Supprimer tous les clips après envoi
                    for clip_info in processed_clips:
                        if os.path.exists(clip_info["filename"]):
                            try:
                                os.remove(clip_info["filename"])
                                if clip_info["filename"] in created_files:
                                    created_files.remove(clip_info["filename"])
                                print(f"🗑️ Clip {clip_info['index']} supprimé")
                            except Exception as e:
                                print(
                                    f"⚠️ Erreur suppression clip {clip_info['index']}: {e}"
                                )

                    final_message = f"✅ **Traitement terminé avec succès**\n📊 {len(processed_clips)} clip(s) générés et envoyés\n🎬 Tous les fichiers ont été traités correctement"
                else:
                    final_message = f"⚠️ **Aucun clip généré**\nUne erreur est survenue lors du traitement"

                await self.safe_edit_message(
                    initial_message, final_message, interaction.channel
                )

                # Supprimer le fichier de sous-titres après l'envoi de tous les clips
                if sous_titres and subtitle_file:
                    if os.path.exists(subtitle_file):
                        try:
                            os.remove(subtitle_file)
                            if subtitle_file in created_files:
                                created_files.remove(
                                    subtitle_file
                                )  # Retirer de la liste car déjà supprimé
                            print(
                                f"🗑️ Fichier de sous-titres supprimé : {os.path.basename(subtitle_file)}"
                            )
                        except Exception as e:
                            print(
                                f"⚠️ Erreur lors de la suppression des sous-titres : {e}"
                            )
                    else:
                        print(f"ℹ️ Fichier de sous-titres introuvable : {subtitle_file}")

                await asyncio.sleep(0.5)

            except Exception as e:
                # Mettre à jour le message principal avec l'erreur
                error_message = f"❌ **Erreur critique**\nUne erreur est survenue : `{str(e)[:150]}...`"
                await self.safe_edit_message(
                    initial_message, error_message, interaction.channel
                )
                await asyncio.sleep(0.5)

            finally:
                # Attendre que tous les fichiers soient libérés
                await asyncio.sleep(1)

                # Nettoyer tous les fichiers créés
                print(
                    f"🗑️ Nettoyage final : {len(created_files)} fichier(s) à supprimer"
                )
                for filename in created_files:
                    if os.path.exists(filename):
                        try:
                            os.remove(filename)
                            print(f"✅ Supprimé : {filename}")
                        except PermissionError:
                            print(
                                f"⚠️ Impossible de supprimer (verrouillé) : {filename}"
                            )
                            # Retry après un délai
                            await asyncio.sleep(0.5)
                            try:
                                os.remove(filename)
                                print(f"✅ Supprimé (2ème tentative) : {filename}")
                            except Exception as e:
                                print(f"❌ Échec définitif : {filename} - {e}")
                        except Exception as e:
                            print(f"❌ Erreur suppression : {filename} - {e}")

                # Nettoyage spécial pour les fichiers de sous-titres qui peuvent avoir des noms variés
                if sous_titres:
                    # Chercher tous les fichiers .srt avec l'unique_id
                    for file in os.listdir("."):
                        if unique_id in file and file.endswith(".srt"):
                            try:
                                os.remove(file)
                                print(f"✅ Sous-titre supprimé : {file}")
                            except Exception as e:
                                print(
                                    f"❌ Erreur suppression sous-titre : {file} - {e}"
                                )

                # Nettoyage des fichiers temp restants
                for file in os.listdir("."):
                    if unique_id in file and (
                        file.endswith(".mp4") or file.endswith(".webm")
                    ):
                        try:
                            os.remove(file)
                            print(f"✅ Fichier temp supprimé : {file}")
                        except Exception as e:
                            print(f"❌ Erreur suppression temp : {file} - {e}")

                print("🧹 Nettoyage terminé")


# Fonction setup obligatoire
async def setup(bot):
    await bot.add_cog(TikTokify(bot))
    print("✅ Extension 'YouTube' chargée")
