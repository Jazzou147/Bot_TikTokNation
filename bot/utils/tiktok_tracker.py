import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional


class TikTokTracker:
    """Gestionnaire pour suivre les comptes TikTok liés et leurs vidéos"""

    def __init__(self, data_file="data/tiktok_linked.json"):
        self.data_file = data_file
        self.data = self.load_data()

    def load_data(self) -> Dict:
        """Charge les données des comptes liés"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"❌ Erreur lors du chargement des données TikTok: {e}")
                return {"guilds": {}, "users": {}}
        return {"guilds": {}, "users": {}}

    def save_data(self):
        """Sauvegarde les données"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"❌ Erreur lors de la sauvegarde: {e}")

    def link_account(self, guild_id: int, user_id: int, tiktok_username: str) -> bool:
        """Lie un compte TikTok à un utilisateur Discord"""
        guild_str = str(guild_id)
        user_str = str(user_id)

        if guild_str not in self.data["guilds"]:
            self.data["guilds"][guild_str] = {
                "notification_channel": None,
                "linked_users": {},
            }

        # Vérifier si l'utilisateur a déjà un compte lié
        if user_str in self.data["guilds"][guild_str]["linked_users"]:
            old_username = self.data["guilds"][guild_str]["linked_users"][user_str][
                "tiktok_username"
            ]
            if old_username == tiktok_username:
                return False  # Déjà lié au même compte

        self.data["guilds"][guild_str]["linked_users"][user_str] = {
            "tiktok_username": tiktok_username,
            "linked_at": datetime.now().isoformat(),
            "last_checked": None,
            "last_video_id": None,
        }

        # Index global des utilisateurs
        if user_str not in self.data["users"]:
            self.data["users"][user_str] = {}
        self.data["users"][user_str][guild_str] = tiktok_username

        self.save_data()
        return True

    def unlink_account(self, guild_id: int, user_id: int) -> bool:
        """Délie un compte TikTok"""
        guild_str = str(guild_id)
        user_str = str(user_id)

        if guild_str not in self.data["guilds"]:
            return False

        if user_str not in self.data["guilds"][guild_str]["linked_users"]:
            return False

        del self.data["guilds"][guild_str]["linked_users"][user_str]

        # Nettoyer l'index global
        if user_str in self.data["users"] and guild_str in self.data["users"][user_str]:
            del self.data["users"][user_str][guild_str]
            if not self.data["users"][user_str]:
                del self.data["users"][user_str]

        self.save_data()
        return True

    def get_linked_account(self, guild_id: int, user_id: int) -> Optional[str]:
        """Récupère le compte TikTok lié d'un utilisateur"""
        guild_str = str(guild_id)
        user_str = str(user_id)

        if guild_str not in self.data["guilds"]:
            return None

        user_data = self.data["guilds"][guild_str]["linked_users"].get(user_str)
        return user_data["tiktok_username"] if user_data else None

    def get_all_linked_users(self, guild_id: int) -> Dict:
        """Récupère tous les utilisateurs liés d'un serveur"""
        guild_str = str(guild_id)

        if guild_str not in self.data["guilds"]:
            return {}

        return self.data["guilds"][guild_str]["linked_users"]

    def set_notification_channel(self, guild_id: int, channel_id: int):
        """Définit le canal de notification pour un serveur"""
        guild_str = str(guild_id)

        if guild_str not in self.data["guilds"]:
            self.data["guilds"][guild_str] = {
                "notification_channel": None,
                "linked_users": {},
            }

        self.data["guilds"][guild_str]["notification_channel"] = channel_id
        self.save_data()

    def get_notification_channel(self, guild_id: int) -> Optional[int]:
        """Récupère le canal de notification d'un serveur"""
        guild_str = str(guild_id)

        if guild_str not in self.data["guilds"]:
            return None

        return self.data["guilds"][guild_str].get("notification_channel")

    def update_last_video(self, guild_id: int, user_id: int, video_id: str):
        """Met à jour le dernier ID de vidéo vérifié"""
        guild_str = str(guild_id)
        user_str = str(user_id)

        if (
            guild_str in self.data["guilds"]
            and user_str in self.data["guilds"][guild_str]["linked_users"]
        ):
            self.data["guilds"][guild_str]["linked_users"][user_str][
                "last_video_id"
            ] = video_id
            self.data["guilds"][guild_str]["linked_users"][user_str][
                "last_checked"
            ] = datetime.now().isoformat()
            self.save_data()

    def get_all_tracked_accounts(self) -> List[Dict]:
        """Récupère tous les comptes à surveiller"""
        accounts = []
        for guild_id, guild_data in self.data["guilds"].items():
            for user_id, user_data in guild_data["linked_users"].items():
                accounts.append(
                    {
                        "guild_id": int(guild_id),
                        "user_id": int(user_id),
                        "tiktok_username": user_data["tiktok_username"],
                        "last_video_id": user_data.get("last_video_id"),
                        "last_checked": user_data.get("last_checked"),
                    }
                )

        return accounts


# Instance globale
tiktok_tracker = TikTokTracker()
