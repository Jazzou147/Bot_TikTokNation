FROM python:3.11-slim

# Installer ffmpeg, wget, unzip et autres dépendances
RUN apt-get update && \
    apt-get install -y ffmpeg wget unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Créer le répertoire pour Real-ESRGAN
RUN mkdir -p /app/tools/real-esrgan/models

# Télécharger Real-ESRGAN pour Linux
WORKDIR /tmp
RUN wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip && \
    unzip realesrgan-ncnn-vulkan-20220424-ubuntu.zip && \
    mv realesrgan-ncnn-vulkan /app/tools/real-esrgan/ && \
    chmod +x /app/tools/real-esrgan/realesrgan-ncnn-vulkan && \
    mv models/* /app/tools/real-esrgan/models/ && \
    rm -rf /tmp/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Désactiver le buffering Python pour voir les logs en temps réel
ENV PYTHONUNBUFFERED=1

# Lancer le bot
CMD ["python", "-u", "main.py"]
