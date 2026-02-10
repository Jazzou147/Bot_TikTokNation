import discord
from discord.ext import commands
from discord import app_commands
import logging

class LockChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Liste des salons verrouillés (stockage en mémoire)
        self.locked_channels = set()

    @app_commands.command(
        name="lock_instagram",
        description="Verrouille le salon Instagram - seules les commandes du bot sont autorisées"
    )
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock_instagram(self, interaction: discord.Interaction):
        # Vérifier que c'est le bon salon
        if (
            interaction.channel is None
            or not hasattr(interaction.channel, "name")
            or interaction.channel.name != "▶️┃gen-instagram"
        ):
            await interaction.response.send_message(
                "❌ Cette commande ne peut être utilisée que dans le salon **▶️┃gen-instagram**",
                ephemeral=True,
            )
            return

        channel_id = interaction.channel.id
        
        if channel_id in self.locked_channels:
            await interaction.response.send_message(
                "⚠️ Ce salon est déjà verrouillé.",
                ephemeral=True,
            )
            return

        self.locked_channels.add(channel_id)
        await interaction.response.send_message(
            "🔒 **Salon verrouillé !** Seules les commandes du bot sont désormais autorisées.",
            ephemeral=False,
        )
        channel_name = getattr(interaction.channel, "name", "Unknown")
        logging.info(f"🔒 Salon {channel_name} verrouillé par {interaction.user}")

    @app_commands.command(
        name="unlock_instagram",
        description="Déverrouille le salon Instagram - les messages sont à nouveau autorisés"
    )
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock_instagram(self, interaction: discord.Interaction):
        # Vérifier que c'est le bon salon
        if (
            interaction.channel is None
            or not hasattr(interaction.channel, "name")
            or interaction.channel.name != "▶️┃gen-instagram"
        ):
            await interaction.response.send_message(
                "❌ Cette commande ne peut être utilisée que dans le salon **▶️┃gen-instagram**",
                ephemeral=True,
            )
            return

        channel_id = interaction.channel.id
        
        if channel_id not in self.locked_channels:
            await interaction.response.send_message(
                "⚠️ Ce salon n'est pas verrouillé.",
                ephemeral=True,
            )
            return

        self.locked_channels.remove(channel_id)
        await interaction.response.send_message(
            "🔓 **Salon déverrouillé !** Les messages sont à nouveau autorisés.",
            ephemeral=False,
        )
        channel_name = getattr(interaction.channel, "name", "Unknown")
        logging.info(f"🔓 Salon {channel_name} déverrouillé par {interaction.user}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignorer les messages du bot lui-même
        if message.author.bot:
            return

        # Vérifier si le message est dans un salon verrouillé
        if message.channel.id not in self.locked_channels:
            return

        # Vérifier que c'est bien le salon Instagram
        if not hasattr(message.channel, "name") or message.channel.name != "▶️┃gen-instagram":
            return

        # Supprimer le message et notifier l'utilisateur
        try:
            await message.delete()
            channel_name = getattr(message.channel, "name", "Unknown")
            await message.channel.send(
                f"❌ {message.author.mention}, ce salon est verrouillé. Utilisez uniquement les commandes du bot.",
                delete_after=5
            )
            logging.info(f"🗑️ Message de {message.author} supprimé dans le salon verrouillé")
        except discord.Forbidden:
            logging.error("❌ Permission insuffisante pour supprimer le message")
        except Exception as e:
            logging.error(f"❌ Erreur lors de la suppression du message: {e}")

    @lock_instagram.error
    async def lock_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ Vous n'avez pas la permission de gérer les salons.",
                ephemeral=True
            )

    @unlock_instagram.error
    async def unlock_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ Vous n'avez pas la permission de gérer les salons.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(LockChannel(bot))
