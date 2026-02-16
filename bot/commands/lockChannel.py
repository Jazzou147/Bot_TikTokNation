import discord
from discord.ext import commands
from discord import app_commands
import logging

# Tableau des salons qui peuvent être verrouillés
LOCKABLE_CHANNELS = {
    "▶️┃gen-instagram": "instagram",
    "🎨┃gen-pinterest": "pinterest",
    "🔥┃tiktok-posts": "tiktok",
    # Ajoutez d'autres salons ici si nécessaire
    # "emoji┃nom-du-salon": "identifiant",
}


class LockChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Liste des salons verrouillés (stockage en mémoire)
        self.locked_channels = set()

        # Créer dynamiquement les commandes pour chaque salon
        self._create_lock_commands()

    def _create_lock_commands(self):
        """Crée dynamiquement les commandes lock/unlock pour chaque salon dans LOCKABLE_CHANNELS"""
        for channel_name, channel_id in LOCKABLE_CHANNELS.items():
            # Créer la commande lock
            self._add_lock_command(channel_name, channel_id)
            # Créer la commande unlock
            self._add_unlock_command(channel_name, channel_id)

    def _add_lock_command(self, channel_name: str, channel_id: str):
        """Ajoute une commande lock pour un salon spécifique"""
        command_name = f"lock_{channel_id}"
        description = f"Verrouille le salon {channel_name} - seules les commandes du bot sont autorisées"

        async def lock_command(interaction: discord.Interaction):
            await self._lock_channel(interaction, channel_name)

        # Créer la commande avec les décorateurs appropriés
        cmd = app_commands.Command(
            name=command_name,
            description=description,
            callback=lock_command,
        )
        cmd.default_permissions = discord.Permissions(manage_channels=True)

        # Ajouter au tree
        self.bot.tree.add_command(cmd)

    def _add_unlock_command(self, channel_name: str, channel_id: str):
        """Ajoute une commande unlock pour un salon spécifique"""
        command_name = f"unlock_{channel_id}"
        description = f"Déverrouille le salon {channel_name} - les messages sont à nouveau autorisés"

        async def unlock_command(interaction: discord.Interaction):
            await self._unlock_channel(interaction, channel_name)

        # Créer la commande avec les décorateurs appropriés
        cmd = app_commands.Command(
            name=command_name,
            description=description,
            callback=unlock_command,
        )
        cmd.default_permissions = discord.Permissions(manage_channels=True)

        # Ajouter au tree
        self.bot.tree.add_command(cmd)

    async def _lock_channel(self, interaction: discord.Interaction, channel_name: str):
        """Fonction générique pour verrouiller un salon"""
        # Vérifier que c'est le bon salon
        if (
            interaction.channel is None
            or not isinstance(interaction.channel, discord.TextChannel)
            or interaction.channel.name != channel_name
        ):
            await interaction.response.send_message(
                f"❌ Cette commande ne peut être utilisée que dans le salon **{channel_name}**",
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
            ephemeral=True,
        )
        logging.info(f"🔒 Salon {channel_name} verrouillé par {interaction.user}")

    async def _unlock_channel(
        self, interaction: discord.Interaction, channel_name: str
    ):
        """Fonction générique pour déverrouiller un salon"""
        # Vérifier que c'est le bon salon
        if (
            interaction.channel is None
            or not isinstance(interaction.channel, discord.TextChannel)
            or interaction.channel.name != channel_name
        ):
            await interaction.response.send_message(
                f"❌ Cette commande ne peut être utilisée que dans le salon **{channel_name}**",
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
            ephemeral=True,
        )
        logging.info(f"🔓 Salon {channel_name} déverrouillé par {interaction.user}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignorer les messages du bot lui-même
        if message.author.bot:
            return

        # Vérifier si le message est dans un salon verrouillé
        if message.channel.id not in self.locked_channels:
            return

        # Vérifier que c'est bien un salon verrouillable
        if (
            not isinstance(message.channel, discord.TextChannel)
            or message.channel.name not in LOCKABLE_CHANNELS
        ):
            return

        # Supprimer le message et notifier l'utilisateur
        try:
            await message.delete()
            await message.channel.send(
                f"❌ {message.author.mention}, ce salon est verrouillé. Utilisez uniquement les commandes du bot.",
                delete_after=5,
            )
            logging.info(
                f"🗑️ Message de {message.author} supprimé dans le salon verrouillé {message.channel.name}"
            )
        except discord.Forbidden:
            logging.error("❌ Permission insuffisante pour supprimer le message")
        except Exception as e:
            logging.error(f"❌ Erreur lors de la suppression du message: {e}")


async def setup(bot):
    await bot.add_cog(LockChannel(bot))
