# 🎵 TikTok Auto-Share

## Description

Ce système permet aux membres du serveur Discord de lier leur compte TikTok et de partager automatiquement leurs nouvelles vidéos dans un canal dédié.

## 🚀 Fonctionnalités

- **Liaison de compte** : Les utilisateurs peuvent lier leur compte TikTok
- **Vérification automatique** : Le bot vérifie toutes les 5 minutes les nouvelles vidéos
- **Notifications** : Les nouvelles vidéos sont postées automatiquement dans un canal configuré
- **Gestion** : Les admins peuvent configurer le canal et voir tous les comptes liés

## 📋 Commandes

### Pour tous les utilisateurs

#### `/linktiktok <username>`
Lie ton compte TikTok au bot pour partager automatiquement tes vidéos.

**Paramètres:**
- `username` : Ton nom d'utilisateur TikTok (sans @)

**Exemple:**
```
/linktiktok charlidamelio
```

#### `/unlinktiktok`
Délie ton compte TikTok et arrête le partage automatique.

#### `/mytiktok`
Affiche ton compte TikTok actuellement lié et les informations de configuration.

### Pour les administrateurs

#### `/settiktokchannel <channel>`
Configure le canal où les nouvelles vidéos TikTok seront postées.

**Paramètres:**
- `channel` : Le canal Discord à utiliser

**Exemple:**
```
/settiktokchannel #nouvelles-videos
```

#### `/linkedtiktoks`
Affiche la liste de tous les comptes TikTok liés sur le serveur.

## 🔧 Configuration

### Étape 1: Configurer le canal (Admin)
Avant que les utilisateurs puissent lier leurs comptes, un administrateur doit configurer le canal de notification :

```
/settiktokchannel #tiktok-videos
```

### Étape 2: Lier son compte (Utilisateur)
Les utilisateurs peuvent maintenant lier leur compte :

```
/linktiktok monpseudo
```

### Étape 3: C'est tout !
Le bot vérifiera automatiquement toutes les 5 minutes et postera les nouvelles vidéos.

## 📊 Fonctionnement technique

### Vérification des vidéos
- Le bot utilise `yt-dlp` pour récupérer les dernières vidéos
- Intervalle de vérification : **5 minutes**
- Seules les nouvelles vidéos (non vues) sont postées

### Stockage des données
Les données sont stockées dans `data/tiktok_linked.json` :
```json
{
  "guilds": {
    "123456789": {
      "notification_channel": 987654321,
      "linked_users": {
        "111111111": {
          "tiktok_username": "username",
          "linked_at": "2026-02-16T10:00:00",
          "last_checked": "2026-02-16T10:05:00",
          "last_video_id": "7123456789"
        }
      }
    }
  }
}
```

### Format de notification
Quand une nouvelle vidéo est détectée, un embed est posté avec :
- 📌 Mention de l'utilisateur Discord
- 🎵 Titre de la vidéo
- 🔗 Lien vers la vidéo TikTok
- 🖼️ Miniature (si disponible)
- ⏰ Horodatage

## ⚠️ Limitations

- **Délai de détection** : Maximum 5 minutes entre la publication et la notification
- **Première vidéo** : La première vidéo lors de la liaison ne sera pas postée (elle sert de référence)
- **Comptes privés** : Les comptes TikTok privés ne peuvent pas être surveillés
- **Rate limiting** : TikTok peut limiter les requêtes si trop de comptes sont liés

## 🔒 Permissions requises

- **Utilisateurs** : Aucune permission spéciale requise
- **Administrateurs** : Permission `administrator` pour `/settiktokchannel` et `/linkedtiktoks`
- **Bot** : Permissions `Send Messages`, `Embed Links` dans le canal de notification

## 🆘 Dépannage

### "Canal non configuré"
Un administrateur doit d'abord utiliser `/settiktokchannel` pour définir où poster les vidéos.

### "Compte introuvable"
Vérifiez que :
- Le nom d'utilisateur est correct (sans @)
- Le compte TikTok existe et est public
- Le compte n'est pas banni ou restreint

### Les vidéos ne sont pas postées
Vérifiez que :
- Le bot est en ligne
- Le canal configuré existe toujours
- Le bot a les permissions nécessaires dans le canal
- Le compte TikTok est toujours public

## 📝 Logs

Le système génère les logs suivants :
- ✅ Démarrage du système de surveillance
- 🔗 Liaison/déliaison de compte
- 📺 Configuration du canal
- 🔍 Vérifications périodiques
- 📺 Nouvelles vidéos postées
- ❌ Erreurs de vérification

## 🔮 Améliorations futures possibles

- [ ] Notifications par DM pour l'utilisateur
- [ ] Statistiques de vues/likes
- [ ] Support d'autres plateformes (Instagram Reels, YouTube Shorts)
- [ ] Filtres de contenu (hashtags, durée)
- [ ] Réactions automatiques
- [ ] Multi-canaux (différents créateurs dans différents canaux)
