import discord
from discord.ext import commands


class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Commande slash pour attribuer manuellement le rôle Membre
    @discord.app_commands.command(
        name="autorole",
        description="Attribue le rôle 'Membre' à un utilisateur s'il n'a pas de rôle"
    )
    @discord.app_commands.default_permissions(manage_roles=True)
    @discord.app_commands.checks.has_permissions(manage_roles=True)
    @discord.app_commands.guild_only()
    async def slash_autorole(self, interaction: discord.Interaction, member: discord.Member):
        """
        Attribue le rôle Membre à un utilisateur qui n'a pas de rôle.
        
        Parameters:
        -----------
        member: discord.Member
            Le membre à qui attribuer le rôle
        """
        await interaction.response.defer(ephemeral=True)
        
        # Vérifier que nous sommes bien dans un serveur
        if not interaction.guild:
            await interaction.followup.send(
                "❌ Cette commande ne peut être utilisée que dans un serveur.",
                ephemeral=True
            )
            return
        
        # Récupérer le rôle "Membre"
        role = discord.utils.get(interaction.guild.roles, name="Membre")
        
        if not role:
            await interaction.followup.send(
                "❌ Le rôle 'Membre' n'existe pas sur ce serveur. Veuillez le créer d'abord.",
                ephemeral=True
            )
            return
        
        # Vérifier si le membre a déjà des rôles (en excluant @everyone)
        member_roles = [r for r in member.roles if r.name != "@everyone"]
        
        if member_roles:
            roles_list = ", ".join([r.mention for r in member_roles])
            await interaction.followup.send(
                f"ℹ️ {member.mention} possède déjà des rôles : {roles_list}",
                ephemeral=True
            )
            return
        
        # Attribuer le rôle Membre
        try:
            await member.add_roles(role, reason="Attribution automatique du rôle Membre")
            await interaction.followup.send(
                f"✅ Le rôle {role.mention} a été attribué à {member.mention}",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je n'ai pas les permissions nécessaires pour attribuer des rôles.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Une erreur s'est produite : {str(e)}",
                ephemeral=True
            )

    # Événement qui s'active quand un membre rejoint le serveur
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Attribue automatiquement le rôle Membre quand quelqu'un rejoint le serveur.
        """
        # Récupérer le rôle "Membre"
        role = discord.utils.get(member.guild.roles, name="Membre")
        
        if not role:
            print(f"⚠️ Le rôle 'Membre' n'existe pas sur le serveur {member.guild.name}")
            return
        
        # Vérifier si le membre a déjà des rôles (en excluant @everyone)
        member_roles = [r for r in member.roles if r.name != "@everyone"]
        
        if not member_roles:
            try:
                await member.add_roles(role, reason="Attribution automatique du rôle Membre lors de l'arrivée")
                print(f"✅ Rôle 'Membre' attribué automatiquement à {member.name}")
            except discord.Forbidden:
                print(f"❌ Permissions insuffisantes pour attribuer le rôle à {member.name}")
            except Exception as e:
                print(f"❌ Erreur lors de l'attribution du rôle à {member.name}: {str(e)}")

    # Gestion des erreurs pour les permissions
    @slash_autorole.error
    async def autorole_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ Vous n'avez pas la permission de gérer les rôles.",
                ephemeral=True
            )


async def setup(bot):
    # Activer l'intent members pour l'événement on_member_join
    if not bot.intents.members:
        print("⚠️ L'intent 'members' n'est pas activé. L'attribution automatique à l'arrivée ne fonctionnera pas.")
    
    await bot.add_cog(AutoRole(bot))
    print("✅ Extension 'AutoRole' chargée")
