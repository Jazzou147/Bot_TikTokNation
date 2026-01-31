import discord
from discord.ext import commands


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Commande slash
    @discord.app_commands.command(
        name="ping", description="Affiche la latence du bot en millisecondes"
    )
    async def slash_ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)  # Convertit en ms
        await interaction.response.send_message(f"🏓 Pong ! Latence : `{latency} ms`")


async def setup(bot):
    await bot.add_cog(Ping(bot))
    print("✅ Extension 'Ping' chargée")
