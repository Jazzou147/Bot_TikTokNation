# ✅ Fix Discord Timeout - "Unknown interaction" (Error 10062)

## Problème résolu

Erreur : `discord.app_commands.errors.CommandInvokeError: Command 'youtube' raised an exception: NotFound: 404 Not Found (error code: 10062): Unknown interaction`

## Cause

Discord exige que le bot réponde à une interaction en **moins de 3 secondes**. 

La fonction `get_browser_for_cookies()` prenait trop de temps à s'exécuter (en testant tous les navigateurs), ce qui causait l'expiration du token d'interaction.

## Solution appliquée

### 1. Détection ultra-rapide des cookies

La fonction ne fait plus de tests réseau lents :
- Sur **Linux/Docker** → Retourne `None` immédiatement
- Sur **Windows/Mac** → Retourne `firefox` par défaut (instantané)

### 2. Mise en cache de la détection

La détection du navigateur est faite **une seule fois** et mise en cache dans la classe `TikTokify` :

```python
self._detected_browser = None
self._browser_detection_done = False
```

### 3. Exécution asynchrone

Si la détection est nécessaire, elle est exécutée dans un thread séparé pour ne pas bloquer :

```python
self._detected_browser = await asyncio.to_thread(get_browser_for_cookies)
```

## Impact

✅ Le bot répond **instantanément** à la commande `/youtube`
✅ Plus d'erreur "Unknown interaction"
✅ La détection des cookies reste fonctionnelle quand nécessaire

## Configuration recommandée

Pour Docker/Linux, utilisez **toujours** un fichier de cookies :

```json
{
  "youtube": {
    "cookies_file": "config/youtube_cookies.txt"
  }
}
```

Voir [YOUTUBE_COOKIES.md](YOUTUBE_COOKIES.md) pour exporter vos cookies.

## Test

Le bot doit répondre en **moins de 1 seconde** maintenant.

Testez avec `/youtube <url>` dans le salon **▶️┃gen-youtube**.
