import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import sys
import os

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.stats_manager import stats_manager
from datetime import datetime


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="mystats",
        description="Affiche tes statistiques personnelles et ton classement"
    )
    async def mystats(self, interaction: discord.Interaction):
        """Commande publique pour voir ses propres stats"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            await self._show_personal_stats(interaction, None, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Une erreur s'est produite : {str(e)}", ephemeral=True)
            print(f"Erreur dans /mystats: {e}")
    
    @app_commands.command(
        name="stats",
        description="[ADMIN] Affiche les statistiques complètes du bot"
    )
    @app_commands.describe(
        type="Type de statistiques à afficher",
        user="Utilisateur à consulter (optionnel)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="📊 Statistiques d'un utilisateur", value="personal"),
        app_commands.Choice(name="� Statistiques globales", value="global"),
    ])
    @app_commands.default_permissions(manage_channels=True)
    async def stats(
        self,
        interaction: discord.Interaction,
        type: Optional[app_commands.Choice[str]] = None,
        user: Optional[discord.Member] = None
    ):
        """Commande admin pour voir toutes les stats"""
        await interaction.response.defer()
        
        # Par défaut, affiche les stats globales pour les admins
        if type is None:
            type_value = "global"
        else:
            type_value = type.value
        
        try:
            if type_value == "personal":
                await self._show_personal_stats(interaction, user, ephemeral=False)
            elif type_value == "global":
                await self._show_global_stats(interaction)
        except Exception as e:
            await interaction.followup.send(f"❌ Une erreur s'est produite : {str(e)}")
            print(f"Erreur dans /stats: {e}")
    
    async def _show_personal_stats(self, interaction: discord.Interaction, target_user: Optional[discord.Member] = None, ephemeral: bool = False):
        """Affiche les statistiques personnelles"""
        target = target_user if target_user else interaction.user
        user_stats = await stats_manager.get_user_stats(target.id)
        user_rank = await stats_manager.get_user_rank(target.id)
        
        embed = discord.Embed(
            title=f"📊 Statistiques de {target.display_name}",
            color=discord.Color.purple()
        )
        
        # Avatar de l'utilisateur
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Nombre total de téléchargements
        embed.add_field(
            name="📥 Téléchargements totaux",
            value=f"**{user_stats['downloads']}** vidéos",
            inline=True
        )
        
        # Classement
        if user_rank > 0:
            medal = "🥇" if user_rank == 1 else "🥈" if user_rank == 2 else "🥉" if user_rank == 3 else "🏅"
            embed.add_field(
                name="🏆 Classement",
                value=f"{medal} **#{user_rank}**",
                inline=True
            )
        else:
            embed.add_field(
                name="🏆 Classement",
                value="Non classé",
                inline=True
            )
        
        # Plateforme préférée
        instagram_count = user_stats['platforms'].get('instagram', 0)
        pinterest_count = user_stats['platforms'].get('pinterest', 0)
        
        if instagram_count > pinterest_count:
            preferred = f"📹 Instagram ({instagram_count})"
        elif pinterest_count > instagram_count:
            preferred = f"📌 Pinterest ({pinterest_count})"
        else:
            preferred = "🤝 Équilibré"
        
        embed.add_field(
            name="⭐ Plateforme préférée",
            value=preferred,
            inline=True
        )
        
        # Détails par plateforme
        embed.add_field(
            name="📹 Instagram",
            value=f"{instagram_count} téléchargements",
            inline=True
        )
        
        embed.add_field(
            name="📌 Pinterest",
            value=f"{pinterest_count} téléchargements",
            inline=True
        )
        
        # Dernière activité
        if user_stats['last_download']:
            try:
                last_download = datetime.fromisoformat(user_stats['last_download'])
                embed.add_field(
                    name="🕐 Dernière activité",
                    value=f"<t:{int(last_download.timestamp())}:R>",
                    inline=True
                )
            except:
                pass
        
        embed.set_footer(text="TikTokNation Bot • Utilise /stats pour plus de détails")
        
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    
    async def _show_leaderboard(self, interaction: discord.Interaction):
        """Affiche le classement général"""
        top_users = await stats_manager.get_top_users(limit=10)
        
        embed = discord.Embed(
            title="🏆 Classement Général - Top 10",
            description="Les utilisateurs les plus actifs de TikTokNation !",
            color=discord.Color.gold()
        )
        
        if not top_users:
            embed.add_field(
                name="Aucune donnée",
                value="Aucun téléchargement n'a encore été effectué !",
                inline=False
            )
        else:
            leaderboard_text = ""
            medals = ["🥇", "🥈", "🥉"]
            
            for rank, (user_id, user_data) in enumerate(top_users, start=1):
                medal = medals[rank - 1] if rank <= 3 else f"**{rank}.**"
                user_name = user_data['name']
                downloads = user_data['downloads']
                
                # Afficher l'utilisateur avec mention si possible
                try:
                    user_mention = f"<@{user_id}>"
                except:
                    user_mention = user_name
                
                leaderboard_text += f"{medal} {user_mention} • **{downloads}** téléchargements\n"
            
            embed.add_field(
                name="👥 Top Utilisateurs",
                value=leaderboard_text,
                inline=False
            )
        
        # Ajouter la position de l'utilisateur actuel s'il n'est pas dans le top 10
        user_rank = await stats_manager.get_user_rank(interaction.user.id)
        if user_rank > 10:
            user_stats = await stats_manager.get_user_stats(interaction.user.id)
            embed.add_field(
                name="📍 Votre position",
                value=f"#{user_rank} avec **{user_stats['downloads']}** téléchargements",
                inline=False
            )
        
        embed.set_footer(text="Continue à télécharger pour grimper dans le classement ! 💜")
        
        await interaction.followup.send(embed=embed)
    
    async def _show_top_videos(self, interaction: discord.Interaction):
        """Affiche les vidéos les plus téléchargées"""
        top_videos = await stats_manager.get_top_videos(limit=10)
        
        embed = discord.Embed(
            title="🎬 Vidéos les Plus Téléchargées",
            description="Le contenu le plus populaire sur TikTokNation !",
            color=discord.Color.blue()
        )
        
        if not top_videos:
            embed.add_field(
                name="Aucune donnée",
                value="Aucune vidéo n'a encore été téléchargée !",
                inline=False
            )
        else:
            for rank, (video_url, video_data) in enumerate(top_videos, start=1):
                title = video_data['title']
                if len(title) > 50:
                    title = title[:47] + "..."
                
                platform_emoji = "📹" if video_data['platform'] == "instagram" else "📌"
                downloads = video_data['downloads']
                unique_users = len(video_data.get('downloaded_by', []))
                
                embed.add_field(
                    name=f"{rank}. {platform_emoji} {title}",
                    value=f"📥 {downloads} téléchargements • 👥 {unique_users} utilisateurs",
                    inline=False
                )
        
        embed.set_footer(text="TikTokNation Bot • Les vidéos les plus populaires")
        
        await interaction.followup.send(embed=embed)
    
    async def _show_global_stats(self, interaction: discord.Interaction):
        """Affiche les statistiques globales du bot"""
        global_stats = await stats_manager.get_global_stats()
        
        embed = discord.Embed(
            title="🌐 Statistiques Globales",
            description="Vue d'ensemble de l'activité sur TikTokNation",
            color=discord.Color.green()
        )
        
        # Stats générales
        embed.add_field(
            name="📥 Total de téléchargements",
            value=f"**{global_stats['total_downloads']}** vidéos",
            inline=True
        )
        
        embed.add_field(
            name="👥 Utilisateurs actifs",
            value=f"**{global_stats['total_users']}** membres",
            inline=True
        )
        
        embed.add_field(
            name="🎬 Vidéos uniques",
            value=f"**{global_stats['total_videos']}** vidéos",
            inline=True
        )
        
        # Stats par plateforme
        instagram_total = global_stats['platforms'].get('instagram', 0)
        pinterest_total = global_stats['platforms'].get('pinterest', 0)
        
        embed.add_field(
            name="📹 Instagram",
            value=f"{instagram_total} téléchargements",
            inline=True
        )
        
        embed.add_field(
            name="📌 Pinterest",
            value=f"{pinterest_total} téléchargements",
            inline=True
        )
        
        # Calcul du pourcentage
        if global_stats['total_downloads'] > 0:
            instagram_percent = (instagram_total / global_stats['total_downloads']) * 100
            pinterest_percent = (pinterest_total / global_stats['total_downloads']) * 100
            
            embed.add_field(
                name="📊 Répartition",
                value=f"Instagram: {instagram_percent:.1f}%\nPinterest: {pinterest_percent:.1f}%",
                inline=True
            )
        
        # Moyenne par utilisateur
        if global_stats['total_users'] > 0:
            avg_per_user = global_stats['total_downloads'] / global_stats['total_users']
            embed.add_field(
                name="📈 Moyenne par utilisateur",
                value=f"{avg_per_user:.1f} téléchargements",
                inline=True
            )
        
        embed.set_footer(text="TikTokNation Bot • Merci de faire partie de la communauté ! 💜")
        
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Stats(bot))
