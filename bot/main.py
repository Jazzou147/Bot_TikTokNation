import discord
import os
import logging
from discord.ext import commands
from dotenv import load_dotenv
import sys
import signal
from server import keep_alive

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# --- Configuration des logs ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

# --- Définir les intents ---
intents = discord.Intents.default()
intents.message_content = True


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=["/"],
            intents=intents,
        )

    async def setup_hook(self):
        # Charger les extensions
        for filename in os.listdir("./commands"):
            if filename.endswith(".py"):
                await self.load_extension(f"commands.{filename[:-3]}")

        # Supprimer les commandes obsolètes si nécessaire
        try:
            self.tree.remove_command("clear", type=discord.AppCommandType.chat_input)
        except Exception:
            pass

        await self.tree.sync()
        logging.info("✅ Commandes slash synchronisées")

    async def on_ready(self):
        logging.info("🔑 Bot démarré avec succès")
        logging.info("📁 Version du bot : 1.0.0")
        logging.info(f"👤 Connecté en tant que {self.user}")


bot = MyBot()

# --- Lancer le bot ---
if not TOKEN:
    logging.error("❌ Le token Discord est introuvable dans le fichier .env")
else:
    keep_alive()
    bot.run(TOKEN)
