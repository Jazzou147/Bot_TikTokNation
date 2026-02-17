import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
import sys
import os
import yt_dlp
import asyncio
import random
from datetime import datetime

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.tiktok_tracker import tiktok_tracker


class TikTokAuto(commands.Cog):
    TIKTOK_CHANNEL_NAME = "🔥┃tiktok-posts"

    def __init__(self, bot):
        self.bot = bot
        self.check_interval = 300  # 5 minutes
        self.checking = False

    def get_tiktok_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """Trouve le canal TikTok par son nom"""
        for channel in guild.text_channels:
            if channel.name == self.TIKTOK_CHANNEL_NAME:
                return channel
        return None

    async def cog_load(self):
        """Démarrage de la tâche de vérification"""
        self.check_new_videos.start()
        logging.info("✅ Système de surveillance TikTok démarré")

    async def cog_unload(self):
        """Arrêt de la tâche de vérification"""
        self.check_new_videos.cancel()
        logging.info("🔴 Système de surveillance TikTok arrêté")

    @app_commands.command(
        name="linktiktok",
        description="Lie ton compte TikTok pour partager automatiquement tes vidéos",
    )
    @app_commands.describe(username="Ton nom d'utilisateur TikTok (sans @)")
    async def link_tiktok(self, interaction: discord.Interaction, username: str):
        """Lie un compte TikTok à l'utilisateur Discord"""

        if not interaction.guild or not interaction.guild_id:
            await interaction.response.send_message(
                "❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        # Nettoyer le nom d'utilisateur
        username = username.strip().lstrip("@")

        if not username:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Le nom d'utilisateur ne peut pas être vide",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Vérifier si le canal TikTok existe
        tiktok_channel = self.get_tiktok_channel(interaction.guild)
        if not tiktok_channel:
            embed = discord.Embed(
                title="⚠️ Canal introuvable",
                description=f"Le canal `{self.TIKTOK_CHANNEL_NAME}` n'existe pas sur ce serveur.\n\nCrée ce canal pour pouvoir lier ton compte TikTok.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Vérifier que le compte TikTok existe
        try:
            is_valid = await self.verify_tiktok_account(username)
            if not is_valid:
                embed = discord.Embed(
                    title="❌ Compte introuvable",
                    description=f"Le compte TikTok `@{username}` n'a pas pu être vérifié. Assure-toi que le nom d'utilisateur est correct.",
                    color=discord.Color.red(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        except Exception as e:
            logging.error(f"❌ Erreur lors de la vérification du compte: {e}")
            embed = discord.Embed(
                title="⚠️ Vérification impossible",
                description=f"Impossible de vérifier le compte `@{username}`. Le lien sera quand même créé.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        # Lier le compte
        was_new = tiktok_tracker.link_account(
            interaction.guild_id, interaction.user.id, username
        )

        if was_new:
            embed = discord.Embed(
                title="✅ Compte TikTok lié",
                description=f"Ton compte `@{username}` a été lié avec succès !\n\n"
                f"Tes nouvelles vidéos et lives seront automatiquement partagés dans {tiktok_channel.mention}",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="✅ Compte mis à jour",
                description=f"Ton compte TikTok a été mis à jour vers `@{username}`",
                color=discord.Color.green(),
            )

        embed.set_footer(text="Vérifications toutes les 5 minutes (vidéos + lives)")
        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"🔗 {interaction.user} a lié son compte TikTok: @{username}")

    @app_commands.command(name="unlinktiktok", description="Délie ton compte TikTok")
    async def unlink_tiktok(self, interaction: discord.Interaction):
        """Délie le compte TikTok de l'utilisateur"""

        if not interaction.guild or not interaction.guild_id:
            await interaction.response.send_message(
                "❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        current_account = tiktok_tracker.get_linked_account(
            interaction.guild_id, interaction.user.id
        )

        if not current_account:
            embed = discord.Embed(
                title="⚠️ Aucun compte lié",
                description="Tu n'as pas de compte TikTok lié",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        tiktok_tracker.unlink_account(interaction.guild_id, interaction.user.id)

        embed = discord.Embed(
            title="✅ Compte délié",
            description=f"Ton compte `@{current_account}` a été délié avec succès",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.info(
            f"🔗 {interaction.user} a délié son compte TikTok: @{current_account}"
        )

    @app_commands.command(name="mytiktok", description="Affiche ton compte TikTok lié")
    async def my_tiktok(self, interaction: discord.Interaction):
        """Affiche le compte TikTok lié de l'utilisateur"""

        if not interaction.guild or not interaction.guild_id:
            await interaction.response.send_message(
                "❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        account = tiktok_tracker.get_linked_account(
            interaction.guild_id, interaction.user.id
        )

        if not account:
            embed = discord.Embed(
                title="⚠️ Aucun compte lié",
                description="Tu n'as pas encore lié de compte TikTok.\nUtilise `/linktiktok` pour en lier un !",
                color=discord.Color.orange(),
            )
        else:
            tiktok_channel = self.get_tiktok_channel(interaction.guild)
            channel_mention = (
                tiktok_channel.mention
                if tiktok_channel
                else f"`{self.TIKTOK_CHANNEL_NAME}`"
            )
            embed = discord.Embed(
                title="🎵 Ton compte TikTok",
                description=f"**Compte lié :** `@{account}`\n"
                f"**Canal de notification :** {channel_mention}",
                color=discord.Color.from_rgb(0, 242, 234),
            )
            embed.add_field(
                name="Lien TikTok", value=f"https://tiktok.com/@{account}", inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="linkedtiktoks",
        description="Liste tous les comptes TikTok liés",
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def linked_tiktoks(self, interaction: discord.Interaction):
        """Liste tous les comptes liés (Modérateurs et admins)"""

        if not interaction.guild or not interaction.guild_id:
            await interaction.response.send_message(
                "❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True
            )
            return

        linked_users = tiktok_tracker.get_all_linked_users(interaction.guild_id)

        if not linked_users:
            embed = discord.Embed(
                title="📋 Comptes TikTok liés",
                description="Aucun compte TikTok n'est actuellement lié",
                color=discord.Color.blue(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Comptes TikTok liés",
            description=f"**{len(linked_users)}** compte(s) lié(s)",
            color=discord.Color.blue(),
        )

        for user_id, user_data in linked_users.items():
            user = interaction.guild.get_member(int(user_id))
            username = user_data["tiktok_username"]

            if user:
                embed.add_field(
                    name=f"@{username}", value=f"👤 {user.mention}", inline=True
                )
            else:
                embed.add_field(
                    name=f"@{username}",
                    value=f"👤 Utilisateur quitté (ID: {user_id})",
                    inline=True,
                )

        tiktok_channel = self.get_tiktok_channel(interaction.guild)
        if tiktok_channel:
            embed.set_footer(text=f"Canal: #{tiktok_channel.name}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def verify_tiktok_account(self, username: str) -> bool:
        """Vérifie qu'un compte TikTok existe"""
        url = f"https://www.tiktok.com/@{username}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlist_items": "1",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                return info is not None
        except Exception:
            return False

    @tasks.loop(seconds=300)  # Toutes les 5 minutes
    async def check_new_videos(self):
        """Vérifie les nouvelles vidéos et lives des comptes liés"""
        if self.checking:
            return

        self.checking = True
        try:
            accounts = tiktok_tracker.get_all_tracked_accounts()

            if not accounts:
                return

            logging.info(f"🔍 Vérification de {len(accounts)} compte(s) TikTok...")

            for account in accounts:
                try:
                    await self.check_account_for_new_video(account)
                    await asyncio.sleep(2)  # Délai entre chaque vérification
                except Exception as e:
                    logging.error(
                        f"❌ Erreur lors de la vérification de @{account['tiktok_username']}: {e}"
                    )

        finally:
            self.checking = False

    @check_new_videos.before_loop
    async def before_check_new_videos(self):
        """Attendre que le bot soit prêt"""
        await self.bot.wait_until_ready()

    async def check_account_for_new_video(self, account: dict):
        """Vérifie si un compte a une nouvelle vidéo ou un live actif"""
        username = account["tiktok_username"]
        guild = self.bot.get_guild(account["guild_id"])
        if not guild:
            return

        # Trouver le canal TikTok
        tiktok_channel = self.get_tiktok_channel(guild)
        if not tiktok_channel:
            return

        url = f"https://www.tiktok.com/@{username}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlist_items": "1",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)

                if not info:
                    return

                # Vérifier si c'est un live
                is_live = info.get("is_live", False)

                if is_live:
                    # C'est un live !
                    live_id = info.get("id") or info.get("display_id")

                    # Vérifier si on a déjà notifié ce live
                    if not account.get("is_live", False) or live_id != account.get(
                        "last_live_id"
                    ):
                        await self.post_live_notification(account, info, tiktok_channel)  # type: ignore
                        if live_id:
                            tiktok_tracker.update_live_status(
                                account["guild_id"], account["user_id"], True, live_id  # type: ignore
                            )
                    return
                else:
                    # Si l'utilisateur était en live et ne l'est plus, mettre à jour le statut
                    if account.get("is_live", False):
                        tiktok_tracker.update_live_status(
                            account["guild_id"], account["user_id"], False
                        )

                # Vérifier les vidéos normales
                if "entries" not in info or not info["entries"]:
                    return

                latest_video = info["entries"][0]
                video_id = latest_video.get("id")

                if not video_id:
                    return

                # Si c'est la première vérification, juste sauvegarder l'ID
                if account["last_video_id"] is None:
                    tiktok_tracker.update_last_video(
                        account["guild_id"], account["user_id"], video_id
                    )
                    return

                # Si c'est une nouvelle vidéo
                if video_id != account["last_video_id"]:
                    await self.post_new_video(account, latest_video, tiktok_channel)
                    tiktok_tracker.update_last_video(
                        account["guild_id"], account["user_id"], video_id
                    )

        except Exception as e:
            logging.error(f"❌ Erreur lors de la vérification de @{username}: {e}")

    async def post_live_notification(
        self, account: dict, live_info: dict, channel: discord.TextChannel
    ):
        """Poste une notification de live dans le canal Discord"""
        guild = self.bot.get_guild(account["guild_id"])
        if not guild:
            return

        user = guild.get_member(account["user_id"])
        if not user:
            return

        live_url = (
            live_info.get("url")
            or f"https://www.tiktok.com/@{account['tiktok_username']}/live"
        )
        title = live_info.get("title", "Live TikTok")

        embed = discord.Embed(
            title="🔴 LIVE EN COURS !",
            description=f"**{user.mention}** est en direct sur TikTok !\n\n"
            f"**Titre :** {title[:100]}\n"
            f"**Lien :** [Rejoindre le live]({live_url})",
            color=discord.Color.red(),
            url=live_url,
            timestamp=datetime.now(),
        )

        embed.set_author(
            name=f"@{account['tiktok_username']}", icon_url=user.display_avatar.url
        )

        if live_info.get("thumbnail"):
            embed.set_thumbnail(url=live_info["thumbnail"])

        embed.set_footer(text="TikTok Live | Rejoins vite !")

        try:
            await channel.send(f"@everyone {user.mention} est en live !", embed=embed)
            logging.info(f"🔴 Live détecté pour @{account['tiktok_username']}")
        except Exception as e:
            logging.error(f"❌ Erreur lors de la notification de live: {e}")

    async def post_new_video(
        self, account: dict, video_info: dict, channel: discord.TextChannel
    ):
        """Poste une nouvelle vidéo dans le canal Discord"""
        guild = self.bot.get_guild(account["guild_id"])
        if not guild:
            return

        user = guild.get_member(account["user_id"])
        if not user:
            return

        video_url = (
            video_info.get("url")
            or f"https://www.tiktok.com/@{account['tiktok_username']}/video/{video_info.get('id')}"
        )
        title = video_info.get("title", "Nouvelle vidéo TikTok")

        # Générer une couleur aléatoire
        random_color = discord.Color.from_rgb(
            random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
        )

        embed = discord.Embed(
            title="🔥 Nouvelle vidéo TikTok !",
            description=f"**{user.mention}** a publié une nouvelle vidéo !\n\n"
            f"**Titre :** {title[:100]}...\n"
            f"**Lien :** [Voir la vidéo]({video_url})",
            color=random_color,
            url=video_url,
            timestamp=datetime.now(),
        )

        embed.set_author(
            name=f"@{account['tiktok_username']}", icon_url=user.display_avatar.url
        )

        if video_info.get("thumbnail"):
            embed.set_thumbnail(url=video_info["thumbnail"])

        embed.set_footer(text="TikTok Auto-Share")

        try:
            await channel.send(embed=embed)
            logging.info(f"📺 Nouvelle vidéo postée pour @{account['tiktok_username']}")
        except Exception as e:
            logging.error(f"❌ Erreur lors de la publication: {e}")


async def setup(bot):
    await bot.add_cog(TikTokAuto(bot))
    logging.info("TikTokAuto cog chargé avec succès.")
