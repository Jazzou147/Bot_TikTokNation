FROM python:3.11-slim

# Installer dépendances système et ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root pour la sécurité
RUN useradd --create-home --shell /bin/bash botuser
WORKDIR /app
USER botuser

# Copier et installer les dépendances Python
COPY --chown=botuser:botuser requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copier le code
COPY --chown=botuser:botuser . /app

# Variables utiles
ENV PYTHONUNBUFFERED=1
ENV FFMPEG_PATH=/usr/bin/ffmpeg
ENV FFPROBE_PATH=/usr/bin/ffprobe

# Commande de démarrage (adaptez main.py si nécessaire)
CMD ["python", "main.py"]
