import discord
from discord.ext import commands
from discord import app_commands
import sys
import os

# Ajouter le dossier parent au path pour importer utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.stats_manager import stats_manager


class Suggest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="suggest",
        description="💡 Suggère du contenu tendance basé sur les téléchargements populaires"
    )
    async def suggest(self, interaction: discord.Interaction):
        """Affiche les contenus les plus populaires du serveur"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Récupérer les vidéos les plus téléchargées
            top_videos = await stats_manager.get_top_videos(limit=5)
            global_stats = await stats_manager.get_global_stats()
            
            # Créer l'embed
            embed = discord.Embed(
                title="💡 Contenu Tendance",
                description="*Voici les contenus les plus populaires du serveur !*\n"
                           "Ces vidéos ont été les plus téléchargées par la communauté.\n\n"
                           "═══════════════════════════════════════",
                color=discord.Color.from_rgb(255, 105, 180)  # Rose tendance
            )
            
            # Si aucune vidéo n'a été téléchargée
            if not top_videos:
                embed.add_field(
                    name="📭 Aucune donnée disponible",
                    value="Aucun contenu n'a encore été téléchargé !\n"
                          "Soyez le premier à partager du contenu populaire !",
                    inline=False
                )
            else:
                # Afficher les vidéos tendances
                suggestions_text = ""
                emoji_platforms = {
                    "instagram": "📸",
                    "pinterest": "📌",
                    "tiktok": "🎵",
                    "youtube": "▶️"
                }
                
                for rank, (video_url, video_data) in enumerate(top_videos, start=1):
                    platform = video_data.get('platform', 'inconnu')
                    platform_emoji = emoji_platforms.get(platform, "🎬")
                    title = video_data.get('title', 'Vidéo sans titre')
                    downloads = video_data.get('downloads', 0)
                    unique_users = len(video_data.get('downloaded_by', []))
                    
                    # Tronquer le titre s'il est trop long
                    if len(title) > 50:
                        title = title[:47] + "..."
                    
                    suggestions_text += (
                        f"**{rank}.** {platform_emoji} {title}\n"
                        f"└ 📥 {downloads} téléchargements • 👥 {unique_users} utilisateurs\n"
                        f"└ [Voir la vidéo]({video_url})\n\n"
                    )
                
                embed.add_field(
                    name="🔥 Top 5 des contenus populaires",
                    value=suggestions_text,
                    inline=False
                )
                
                # Ajouter des statistiques supplémentaires
                total_downloads = global_stats.get('total_downloads', 0)
                total_videos = global_stats.get('total_videos', 0)
                
                stats_text = (
                    f"📊 **{total_downloads}** téléchargements au total\n"
                    f"🎬 **{total_videos}** vidéos uniques partagées"
                )
                
                embed.add_field(
                    name="📈 Statistiques du serveur",
                    value=stats_text,
                    inline=False
                )
            
            # Footer avec conseil
            embed.set_footer(
                text="💡 Astuce : Utilisez /mystats pour voir vos propres statistiques !"
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Erreur",
                description=f"Une erreur s'est produite lors de la récupération des suggestions.\n\n"
                           f"Détails : {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            print(f"Erreur dans /suggest: {e}")


async def setup(bot):
    await bot.add_cog(Suggest(bot))
