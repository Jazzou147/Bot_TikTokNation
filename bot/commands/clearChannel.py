import discord
from discord.ext import commands


class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Commande pour supprimer tous les messages du canal
    @discord.app_commands.command(
        name="channel-clear",
        description="Supprime les messages du canal (admin uniquement)",
    )
    @discord.app_commands.checks.has_permissions(administrator=True)
    @discord.app_commands.describe(
        limit="Nombre de messages à supprimer (défaut: 100, max: 1000)"
    )
    async def channel_clear(self, interaction: discord.Interaction, limit: int = 100):
        if (
            not interaction.guild
            or not interaction.guild.me.guild_permissions.manage_messages
        ):
            await interaction.response.send_message(
                "🚫 Je n'ai pas la permission de gérer les messages.", ephemeral=True
            )
            return

        # Vérifier que le canal supporte purge()
        if not isinstance(
            interaction.channel,
            (discord.TextChannel, discord.Thread, discord.VoiceChannel),
        ):
            await interaction.response.send_message(
                "🚫 Cette commande ne fonctionne que dans les canaux texte.",
                ephemeral=True,
            )
            return

        # Répondre de manière éphémère pour ne pas polluer
        await interaction.response.defer(ephemeral=True)

        # Limiter à un maximum de 1000 messages pour éviter le rate limiting
        if limit > 1000:
            limit = 1000
        elif limit < 1:
            limit = 1

        # Supprimer les messages du canal avec une limite
        deleted = await interaction.channel.purge(limit=limit)

        # Envoyer un message de confirmation qui sera aussi supprimé
        confirmation = await interaction.channel.send(
            f"🧨 Tous les messages ont été supprimés ({len(deleted)} messages)."
        )

        # Attendre 3 secondes puis supprimer le message de confirmation
        await confirmation.delete(delay=3)

        # Confirmer à l'utilisateur de manière éphémère
        await interaction.followup.send(
            f"✅ Canal nettoyé : {len(deleted)} messages supprimés.",
            ephemeral=True,
        )

    # Gestion des erreurs de permissions
    @channel_clear.error
    async def clear_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "🚫 Tu n'as pas la permission d'utiliser cette commande.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(Clear(bot))
    print("✅ Extension 'Clear' chargée")
