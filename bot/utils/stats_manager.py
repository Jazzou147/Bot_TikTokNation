import json
import os
from datetime import datetime
from typing import Dict, List, Tuple
import asyncio

class StatsManager:
    def __init__(self, stats_file: str = None):
        # Utiliser un chemin absolu basé sur l'emplacement du fichier
        if stats_file is None:
            # Obtenir le dossier du bot (parent du dossier utils)
            bot_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            stats_file = os.path.join(bot_dir, "data", "stats.json")
        
        self.stats_file = stats_file
        self.lock = asyncio.Lock()
        print(f"📊 StatsManager initialisé avec le fichier : {self.stats_file}")
        self._ensure_data_directory()
        self._ensure_stats_file()
    
    def _ensure_data_directory(self):
        """Crée le dossier data s'il n'existe pas"""
        data_dir = os.path.dirname(self.stats_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"📁 Dossier de données créé : {data_dir}")
    
    def _ensure_stats_file(self):
        """Crée le fichier de stats s'il n'existe pas"""
        if not os.path.exists(self.stats_file):
            default_data = {
                "users": {},
                "videos": {},
                "platforms": {
                    "instagram": 0,
                    "pinterest": 0
                },
                "total_downloads": 0,
                "last_updated": datetime.now().isoformat()
            }
            try:
                with open(self.stats_file, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Fichier de stats créé : {self.stats_file}")
            except Exception as e:
                print(f"❌ Erreur lors de la création du fichier stats : {e}")
        else:
            print(f"✅ Fichier de stats existant trouvé : {self.stats_file}")
    
    async def load_stats(self) -> Dict:
        """Charge les statistiques depuis le fichier"""
        async with self.lock:
            try:
                if not os.path.exists(self.stats_file):
                    print(f"⚠️ Fichier stats non trouvé, création d'un nouveau fichier")
                    self._ensure_stats_file()
                
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"📖 Stats chargées : {len(data.get('users', {}))} utilisateurs, {len(data.get('videos', {}))} vidéos")
                    return data
            except Exception as e:
                print(f"⚠️ Erreur lors du chargement des stats: {e}")
                # Retourner une structure par défaut en cas d'erreur
                return {
                    "users": {},
                    "videos": {},
                    "platforms": {"instagram": 0, "pinterest": 0},
                    "total_downloads": 0,
                    "last_updated": datetime.now().isoformat()
                }
    
    async def save_stats(self, data: Dict):
        """Sauvegarde les statistiques dans le fichier"""
        async with self.lock:
            try:
                data["last_updated"] = datetime.now().isoformat()
                with open(self.stats_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                print(f"💾 Stats sauvegardées : {data.get('total_downloads', 0)} téléchargements totaux")
            except Exception as e:
                print(f"⚠️ Erreur lors de la sauvegarde des stats: {e}")
    
    async def record_download(self, user_id: int, user_name: str, platform: str, video_url: str, video_title: str = "Vidéo sans titre"):
        """Enregistre un téléchargement"""
        stats = await self.load_stats()
        
        print(f"📊 Enregistrement du téléchargement : user={user_name}, platform={platform}")
        
        # Mise à jour des stats utilisateur
        user_id_str = str(user_id)
        if user_id_str not in stats["users"]:
            stats["users"][user_id_str] = {
                "name": user_name,
                "downloads": 0,
                "platforms": {
                    "instagram": 0,
                    "pinterest": 0
                },
                "last_download": None
            }
        
        stats["users"][user_id_str]["downloads"] += 1
        stats["users"][user_id_str]["name"] = user_name  # Met à jour le nom si changé
        stats["users"][user_id_str]["platforms"][platform] = stats["users"][user_id_str]["platforms"].get(platform, 0) + 1
        stats["users"][user_id_str]["last_download"] = datetime.now().isoformat()
        
        # Mise à jour des stats vidéos
        if video_url not in stats["videos"]:
            stats["videos"][video_url] = {
                "title": video_title,
                "platform": platform,
                "downloads": 0,
                "first_download": datetime.now().isoformat(),
                "downloaded_by": []
            }
        
        stats["videos"][video_url]["downloads"] += 1
        if user_id_str not in stats["videos"][video_url]["downloaded_by"]:
            stats["videos"][video_url]["downloaded_by"].append(user_id_str)
        
        # Mise à jour des stats plateformes
        stats["platforms"][platform] = stats["platforms"].get(platform, 0) + 1
        
        # Mise à jour du total
        stats["total_downloads"] += 1
        
        await self.save_stats(stats)
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Récupère les statistiques d'un utilisateur"""
        stats = await self.load_stats()
        user_id_str = str(user_id)
        
        if user_id_str not in stats["users"]:
            return {
                "downloads": 0,
                "platforms": {"instagram": 0, "pinterest": 0},
                "last_download": None
            }
        
        return stats["users"][user_id_str]
    
    async def get_top_users(self, limit: int = 10) -> List[Tuple[str, Dict]]:
        """Récupère le classement des utilisateurs les plus actifs"""
        stats = await self.load_stats()
        users = stats["users"]
        
        # Trie par nombre de téléchargements
        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1]["downloads"],
            reverse=True
        )
        
        return sorted_users[:limit]
    
    async def get_top_videos(self, limit: int = 10) -> List[Tuple[str, Dict]]:
        """Récupère les vidéos les plus téléchargées"""
        stats = await self.load_stats()
        videos = stats["videos"]
        
        # Trie par nombre de téléchargements
        sorted_videos = sorted(
            videos.items(),
            key=lambda x: x[1]["downloads"],
            reverse=True
        )
        
        return sorted_videos[:limit]
    
    async def get_global_stats(self) -> Dict:
        """Récupère les statistiques globales"""
        stats = await self.load_stats()
        
        return {
            "total_downloads": stats["total_downloads"],
            "total_users": len(stats["users"]),
            "total_videos": len(stats["videos"]),
            "platforms": stats["platforms"]
        }
    
    async def get_user_rank(self, user_id: int) -> int:
        """Récupère le classement d'un utilisateur"""
        top_users = await self.get_top_users(limit=1000)  # Récupère tous les utilisateurs
        
        user_id_str = str(user_id)
        for rank, (uid, _) in enumerate(top_users, start=1):
            if uid == user_id_str:
                return rank
        
        return 0  # Utilisateur pas dans le classement

# Instance globale
stats_manager = StatsManager()
