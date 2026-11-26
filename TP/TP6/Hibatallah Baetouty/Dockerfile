# ============================================================================
#  Image de MaintAI : le code et ses bibliothèques, sans les données ni le modèle.
#  Construire :  docker build -t maintai:0.4.0 .
#  Lancer     :  docker run -d --name maintai-api -p 8000:8000 --env-file .env
#                  -v "%cd%\models:/app/models:ro" maintai:0.4.0
#
#  Principe de l'ordre des instructions : chaque ligne crée une COUCHE. Au build
#  suivant, Docker réutilise les couches jusqu'à la première dont l'entrée a changé,
#  puis reconstruit tout ce qui suit. D'où la règle : ce qui est lent et stable
#  AVANT ce qui est rapide et instable.
# ============================================================================

# --- Étape 1 : l'image de départ -------------------------------------------
# python:3.11-slim = la même version de Python que sur nos PC, en variante "slim"
# (Debian minimal, sans les outils de compilation) : l'image pèse quelques centaines
# de Mo au lieu du double. C'est la couche de base, elle ne change jamais.
FROM python:3.11-slim

# --- Étape 2 : le dossier de travail ---------------------------------------
# Toutes les instructions suivantes (COPY, RUN, CMD) travaillent dans /app, et le
# conteneur y démarre. Évite d'écrire des chemins absolus partout.
WORKDIR /app

# --- Étape 3 : les bibliothèques, AVANT le code ----------------------------
# On copie le seul fichier de dépendances : ainsi la couche du pip install ne dépend
# que de lui. Modifier maintai/predict.py ne l'invalide pas → le pip install reste en
# cache (CACHED dans le journal) et le rebuild tombe à quelques secondes.
COPY requirements-docker.txt .
# --no-cache-dir : pip ne garde pas son cache de téléchargement dans l'image (inutile
# une fois installé, et ça allège la couche de plusieurs dizaines de Mo).
# Les versions sont figées (==) dans requirements-docker.txt : scikit-learn==1.8.0 est
# la version qui a écrit models/model.joblib, il faut la même pour le relire.
RUN pip install --no-cache-dir -r requirements-docker.txt

# --- Étape 4 : le code -----------------------------------------------------
# maintai/ = le package (API, predict, config…) ; ui/ = l'interface Streamlit, dont le
# service "ui" de compose.yaml a besoin. Ce sont les couches reconstruites à chaque
# modification, et elles sont rapides.
# Ce qui n'est PAS copié est listé dans .dockerignore : data/, models/, .env, tests/…
COPY maintai/ ./maintai/
COPY ui/ ./ui/

# --- Étape 5 : où le code cherche le modèle et les données -----------------
# maintai/config.py lit ces deux variables (os.getenv) avec, par défaut, des chemins
# calculés depuis la racine du projet. Dans le conteneur la racine est /app : on les
# fixe donc explicitement là où les volumes seront montés au lancement.
ENV MAINTAI_MODELS_DIR=/app/models
# Les données ne servent qu'à l'onglet "Données" de l'interface ; le service ui monte
# ./data sur /app/data (compose.yaml).
ENV MAINTAI_DATA_PATH=/app/data/sensors.csv

# --- Étape 6 : le port et la commande de démarrage -------------------------
# EXPOSE documente le port écouté par le conteneur. Il ne publie rien tout seul :
# c'est -p 8000:8000 (ou "ports:" dans compose.yaml) qui l'ouvre côté PC.
EXPOSE 8000
# CMD en liste JSON (forme "exec") : uvicorn devient le processus 1 du conteneur et
# reçoit directement les signaux, donc docker stop l'arrête proprement. En forme
# "shell" (CMD uvicorn …), il serait lancé par /bin/sh et ne les recevrait pas.
# --host 0.0.0.0 est obligatoire : dans un conteneur, 127.0.0.1 veut dire "ce
# conteneur seulement", et l'API resterait injoignable depuis le PC malgré le -p
# (c'est le piège 2 du TP).
CMD ["uvicorn", "maintai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
