import discord
from discord.ext import commands
import os 
from discord import app_commands
from PIL import Image
import asyncio
from pathlib import Path
import subprocess  

# Augmenter la limite de taille d'image pour Pillow
Image.MAX_IMAGE_PIXELS = None

class Upscale(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Limite le nombre de téléchargements simultanés à 2
        self.semaphore = asyncio.Semaphore(2)

    @app_commands.command(name="image-upscale-beta", description="Upscale une image avec Real-ESRGAN")
    async def image_upscale(self, interaction: discord.Interaction, image: discord.Attachment):
        
        # Utiliser le semaphore pour limiter à 2 upscales simultanés
        async with self.semaphore:
            # Defer pour éviter le timeout (traitement long)
            await interaction.response.defer()
            
            # Vérification du type de fichier
            if not image.content_type or not image.content_type.startswith("image/"):
                await interaction.followup.send("❌ Veuillez envoyer une image valide.")
                return

            # Sauvegarde du fichier envoyé
            input_path = f"input_{interaction.id}.png"
            output_path = f"output_{interaction.id}.png"
            
            try:
                await interaction.edit_original_response(content="🔄 Téléchargement de l'image... 20%")
                await image.save(Path(input_path))

                # Déterminer le chemin de l'exécutable selon l'OS
                if os.name == 'nt':  # Windows
                    realesrgan_path = os.path.join("tools", "real-esrgan", "realesrgan-ncnn-vulkan.exe")
                else:  # Linux/Unix (Render)
                    realesrgan_path = os.path.join("tools", "real-esrgan", "realesrgan-ncnn-vulkan")
                
                # Vérifier que l'exécutable existe
                if not os.path.exists(realesrgan_path):
                    await interaction.edit_original_response(
                        content=f"❌ Real-ESRGAN n'est pas installé. Chemin: {realesrgan_path}"
                    )
                    return
                
                await interaction.edit_original_response(content="🔄 Upscaling en cours... 40%")
                
                # Commande Real-ESRGAN avec asyncio pour ne pas bloquer l'event loop
                process = await asyncio.create_subprocess_exec(
                    realesrgan_path,
                    "-i", input_path,
                    "-o", output_path,
                    "-s", "4",  # upscale x4
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Erreur inconnue"
                    await interaction.edit_original_response(
                        content=f"❌ Erreur Real-ESRGAN : {error_msg[:200]}"
                    )
                    return
                
                await interaction.edit_original_response(content="🔄 Vérification du fichier... 60%")
                
                # Vérifier que le fichier de sortie existe
                if not os.path.exists(output_path):
                    await interaction.edit_original_response(content="❌ Erreur : le fichier upscalé n'a pas été généré.")
                    return

                await interaction.edit_original_response(content="🔄 Optimisation de la taille... 80%")
                
                # Vérifier la taille du fichier (limite Discord : 8 MB)
                file_size = os.path.getsize(output_path)
                max_size = 8 * 1024 * 1024  # 8 MB en bytes
                
                final_path = output_path
                message = "✅ Voici ton image upscalée :"
                
                # Si le fichier est trop gros, le compresser
                if file_size > max_size:
                    compressed_path = f"compressed_{interaction.id}.jpg"
                    
                    try:
                        img = Image.open(output_path)
                        
                        # Compression progressive
                        quality = 95
                        while quality > 20:
                            img.save(compressed_path, "JPEG", quality=quality, optimize=True)
                            if os.path.getsize(compressed_path) <= max_size:
                                break
                            quality -= 5
                        
                        # Si toujours trop gros, réduire les dimensions
                        if os.path.getsize(compressed_path) > max_size:
                            width, height = img.size
                            new_width, new_height = width // 2, height // 2
                            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            img_resized.save(compressed_path, "JPEG", quality=85, optimize=True)
                            img_resized.close()
                        
                        img.close()
                        final_path = compressed_path
                        message = "✅ Voici ton image upscalée (compressée pour Discord) :"
                        
                    except Exception:
                        await interaction.edit_original_response(
                            content=f"❌ Fichier trop volumineux ({file_size / (1024*1024):.1f} MB) et impossible à compresser. Limite : 8 MB"
                        )
                        return

                await interaction.edit_original_response(content="🔄 Envoi du fichier... 100%")
                
                # Créer un embed avec les informations
                embed = discord.Embed(
                    title="🎨 Upscale terminé !",
                    description=message,
                    color=discord.Color.green()
                )
                
                # Ajouter les informations de taille
                original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
                final_size = os.path.getsize(final_path) / (1024 * 1024)  # MB
                
                embed.add_field(name="📊 Taille originale", value=f"{original_size:.2f} MB", inline=True)
                embed.add_field(name="📊 Taille finale", value=f"{final_size:.2f} MB", inline=True)
                embed.add_field(name="🔍 Facteur", value="x4", inline=True)
                
                # Envoi avec les deux images (avant/après)
                files = [
                    discord.File(input_path, filename="avant.png"),
                    discord.File(final_path, filename="apres.png")
                ]
                
                embed.set_image(url="attachment://apres.png")
                embed.set_thumbnail(url="attachment://avant.png")
                
                await interaction.followup.send(
                    embed=embed,
                    files=files
                )
                
                # Supprimer le message de progression
                await interaction.delete_original_response()

            except subprocess.CalledProcessError as e:
                await interaction.edit_original_response(content=f"❌ Erreur Real-ESRGAN : {e}")
            except Exception as e:
                await interaction.edit_original_response(content=f"❌ Erreur inattendue : {e}")
            finally:
                # Nettoyage des fichiers temporaires
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
                compressed_path = f"compressed_{interaction.id}.jpg"
                if os.path.exists(compressed_path):
                    os.remove(compressed_path)

async def setup(bot):
    await bot.add_cog(Upscale(bot))
    print ("✅ Extension Upscale chargée")