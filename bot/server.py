from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import os
import time
import requests
import logging

load_dotenv()

app = Flask("")


@app.route("/")
def home():
    return "Bot connecté !"


@app.route("/ping")
def ping():
    return "pong"


@app.route("/health")
def health():
    return {"status": "alive", "timestamp": time.time()}


def run():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


def auto_ping():
    """Ping automatique amélioré pour maintenir l'instance active"""
    time.sleep(45)  # Attendre que le serveur démarre
    
    # Utiliser l'URL publique si disponible, sinon localhost
    public_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("PUBLIC_URL")
    port = os.getenv("PORT", 8080)
    
    if public_url:
        url = f"{public_url}/ping"
        logging.info(f"🔄 Auto-ping configuré vers: {url}")
    else:
        url = f"http://localhost:{port}/ping"
        logging.info(f"🔄 Auto-ping configuré en local: {url}")
    
    ping_count = 0
    
    while True:
        try:
            response = requests.get(url, timeout=10)
            ping_count += 1
            if ping_count % 10 == 0:  # Log tous les 10 pings
                logging.info(f"✅ Auto-ping #{ping_count} réussi")
        except Exception as e:
            logging.warning(f"⚠️ Erreur auto-ping: {str(e)}")
        
        time.sleep(120)  # Ping toutes les 2 minutes


def keep_alive():
    server = Thread(target=run)
    server.daemon = True
    server.start()
    
    pinger = Thread(target=auto_ping)
    pinger.daemon = True
    pinger.start()
    
    logging.info("🚀 Serveur Flask et auto-ping démarrés")