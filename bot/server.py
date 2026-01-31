from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import os
import time
import requests

load_dotenv()

app = Flask("")


@app.route("/")
def home():
    return "Bot connecté !"


@app.route("/ping")
def ping():
    return "pong"


def run():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


def auto_ping():
    """Ping automatique toutes les 2.5 minutes pour garder le bot actif"""
    time.sleep(60)  # Attendre 1 minute que le serveur démarre
    url = f"http://localhost:{os.getenv('PORT', 8080)}/ping"
    
    while True:
        try:
            requests.get(url, timeout=5)
        except:
            pass
        time.sleep(150)  # 2.5 minutes


def keep_alive():
    server = Thread(target=run)
    server.daemon = True
    server.start()
    
    pinger = Thread(target=auto_ping)
    pinger.daemon = True
    pinger.start()
