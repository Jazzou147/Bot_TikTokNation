import discord
from discord.ext import commands
import logging


class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="help", description="Affiche toutes les commandes disponibles"
    )
    async def help(self, interaction: discord.Interaction):
        logging.info("📥 Commande /help appelée par %s", interaction.user.name)

        try:
            embed = self.new_method()

            try:
                await interaction.response.send_message(embed=embed)
                logging.info("✅ Réponse envoyée pour /help")
            except Exception as send_err:
                # Si la réponse initiale échoue (interaction expirée/unknown), essayer le followup
                logging.warning("⚠️ Envoi initial /help échoué: %s", str(send_err))
                try:
                    await interaction.followup.send(embed=embed)
                    logging.info("✅ Réponse followup envoyée pour /help")
                except Exception as follow_err:
                    logging.error(
                        "❌ Impossible d'envoyer la réponse /help (followup): %s",
                        str(follow_err),
                    )

        except Exception as e:
            logging.error("❌ Erreur dans la commande /help : %s", str(e))
            # Essayer d'envoyer un message d'erreur via followup si la réponse initiale n'est plus possible
            try:
                await interaction.followup.send(
                    "❌ Une erreur est survenue lors de l'affichage de l'aide."
                )
            except Exception:
                # Dernier recours: rien à faire si l'interaction est indisponible
                logging.exception("❌ Échec d'envoyer le message d'erreur pour /help")

    def new_method(self):
        embed = discord.Embed(
            title="🤖 Centre de Commandes",
            description="*Bienvenue dans le panneau d'aide du bot ! Découvrez toutes les fonctionnalités disponibles.*\n\n"
            "═══════════════════════════════════════\n"
            "🎯 **Commandes organisées par catégorie**\n"
            "═══════════════════════════════════════",
            color=0x5865F2,  # Discord Blurple moderne
        )

        # ═══════════════════════════════════════════════════
        # 📊 INFORMATIONS GÉNÉRALES
        # ═══════════════════════════════════════════════════
        embed.add_field(
            name="📊 Informations & Utilitaires",
            value="*Commandes de base pour interagir avec le bot*",
            inline=False,
        )

        embed.add_field(
            name="</help:0>",
            value="```yaml\nAffiche ce menu d'aide complet```\n" "🌐 Accessible à tous",
            inline=False,
        )

        embed.add_field(
            name="</ping:0>",
            value="```yaml\nVérifie la latence du bot (ms)```\n" "🌐 Accessible à tous",
            inline=False,
        )

        embed.add_field(
            name="</status:0>",
            value="```yaml\nConfirme le statut en ligne du bot```\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        embed.add_field(
            name="</servermap:0>",
            value="```yaml\nCartographie tous les salons du serveur```\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        # ═══════════════════════════════════════════════════
        # 📈 STATISTIQUES & TENDANCES
        # ═══════════════════════════════════════════════════
        embed.add_field(
            name="📈 Statistiques & Tendances",
            value="*Suivez les contenus populaires et vos performances*",
            inline=False,
        )

        embed.add_field(
            name="</suggest:0>",
            value="```yaml\nSuggère du contenu tendance```\n"
            "💡 Basé sur les téléchargements populaires\n"
            "🔥 Top 5 des vidéos les plus partagées\n"
            "📊 Statistiques du serveur\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        embed.add_field(
            name="</mystats:0>",
            value="```yaml\nAffiche tes statistiques personnelles```\n"
            "📊 Nombre de téléchargements\n"
            "🏆 Ton classement sur le serveur\n"
            "📈 Répartition par plateforme\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        # ═══════════════════════════════════════════════════
        # 🎬 TÉLÉCHARGEMENTS & MÉDIAS
        # ═══════════════════════════════════════════════════
        embed.add_field(
            name="🎬 Téléchargements & Médias",
            value="*Téléchargez et convertissez vos contenus favoris*",
            inline=False,
        )

        embed.add_field(
            name="</pindownload:0> `url`",
            value="```fix\nTélécharge des vidéos Pinterest HD```\n"
            "✨ Qualité maximale • Envoi en DM\n"
            "⚡ Gestion fichiers lourds (>8 MB)\n"
            "📥 Résout les liens pin.it\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        embed.add_field(
            name="</yt_download:0> `url` `[sous_titres]`",
            value="```fix\nTélécharge et découpe vidéos YouTube```\n"
            "📱 Format TikTok vertical (1080x1920)\n"
            "✂️ Clips de 60 secondes automatiques\n"
            "💬 Sous-titres FR/EN optionnels\n"
            "🎨 Arrière-plan flouté artistique\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        # ═══════════════════════════════════════════════════
        # 🎨 AMÉLIORATION QUALITÉ (AI)
        # ═══════════════════════════════════════════════════
        embed.add_field(
            name="🎨 Amélioration Qualité (Real-ESRGAN)",
            value="*Upscaling AI pour images et vidéos*",
            inline=False,
        )

        embed.add_field(
            name="</upscale:0> `image`",
            value="```fix\nAméliore la qualité d'images (x4)```\n"
            "🔬 Upscaling IA x4 résolution\n"
            "✨ Détails et netteté améliorés\n"
            "📊 Comparaison avant/après\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        embed.add_field(
            name="</upscale_video:0> `video` `scale`",
            value="```fix\nAméliore la qualité de vidéos```\n"
            "📈 Upscaling x2/x3/x4 au choix\n"
            "🎞️ Traitement frame par frame\n"
            "🔊 Conservation audio parfaite\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        # ═══════════════════════════════════════════════════
        # 🎵 CRÉATION MUSICALE (AI)
        # ═══════════════════════════════════════════════════
        embed.add_field(
            name="🎵 Création Musicale (Ollama AI)",
            value="*Générez des paroles professionnelles avec l'IA*",
            inline=False,
        )

        embed.add_field(
            name="</paroles:0> `description`",
            value="```fix\nGénère des paroles musicales IA```\n"
            "🎼 Structure pro (Intro/Couplet/Refrain/Pont)\n"
            "🎸 Tous genres (rap, pop, rock, drill...)\n"
            "🎯 Tags Suno AI automatiques\n"
            "📝 Export TXT • 400-600 mots\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        embed.add_field(
            name="</modifier_paroles:0> `modifications`",
            value="```fix\nModifie les paroles générées```\n"
            "🔄 Modification intelligente\n"
            "🎨 Conservation de l'esprit original\n"
            "✅ Structure et rimes maintenues\n"
            "🌐 Accessible à tous",
            inline=False,
        )

        # ═══════════════════════════════════════════════════
        # 🛡️ ADMINISTRATION
        # ═══════════════════════════════════════════════════
        embed.add_field(
            name="🛡️ Administration",
            value="*Gestion et maintenance du serveur*",
            inline=False,
        )

        embed.add_field(
            name="</clear_all:0>",
            value="```diff\n- Supprime TOUS les messages du salon```\n"
            "⚠️ Action irréversible\n"
            "🔒 Admin uniquement",
            inline=False,
        )

        embed.add_field(
            name="</maintenance:0>",
            value="```diff\n- Active/désactive le mode maintenance```\n"
            "🔧 Mises à jour et réparations\n"
            "👑 Propriétaire uniquement",
            inline=False,
        )

        # Footer professionnel
        embed.set_footer(
            text="💡 Conseil : Tapez / dans le chat pour voir toutes les commandes avec auto-complétion",
            icon_url="https://cdn.discordapp.com/emojis/1234567890123456789.png",  # Optionnel
        )

        embed.timestamp = discord.utils.utcnow()

        return embed


async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
    logging.info("✅ Extension 'HelpCommand' chargée")
