from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask("")


@app.route("/")
def home():
    return "Bot connecté !"


def run():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


def keep_alive():
    server = Thread(target=run)
    server.start()
