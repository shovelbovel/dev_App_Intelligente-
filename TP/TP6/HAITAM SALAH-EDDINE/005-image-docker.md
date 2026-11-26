# ADR 005 : ce qui entre dans l'image Docker de MaintAI

Date : 26/11/2026 ·  Auteurs :HAITAM SALAH EDDINE  Heure: 11:25

## Contexte

MaintAI doit tourner à l'identique sur n'importe quelle machine équipée de Docker : l'API (port 8000) et l'interface Streamlit (port 8501). Le modèle a été écrit par scikit-learn 1.8.0 et doit être chargé avec cette même version. La clé API ne doit jamais être publiée. Il faut décider de ce qu'on met dans l'image et de ce qui arrive au lancement.

## Options étudiées

1. **Tout dans l'image** : le code, les bibliothèques, le modèle, les données et le `.env`.
   - Avantages : un seul `docker run` suffit, sans aucun fichier sur le PC.
   - Inconvénients : la clé est lisible par quiconque récupère l'image (`docker history`, `docker cp`). Il faut reconstruire l'image à chaque réentraînement, et elle grossit avec les données.
2. **Le code et les bibliothèques dans l'image, le reste au lancement** : le modèle et les données arrivent par des volumes en lecture seule, la clé par `--env-file` / `env_file`.
   - Avantages : l'image ne contient aucun secret. Un nouveau modèle se déploie par un simple redémarrage, sans rebuild. La même image sert en test et en production.
   - Inconvénients : il faut fournir `models/` et `.env` sur la machine. Si on oublie le volume, l'API démarre sans modèle (`model_loaded: false`, puis 503).
3. **Une image par service** (API seule d'un côté, interface de l'autre) au lieu d'une image commune.
   - Avantages : des images plus petites, et l'API n'embarque pas Streamlit.
   - Inconvénients : deux Dockerfiles et deux listes de dépendances à maintenir et à garder synchronisées.

## Décision

Option 2, avec **une seule image `maintai:0.4.0`** pour les deux services. Cette image est construite sur `python:3.11-slim` à partir de `requirements-docker.txt`, dont les versions sont figées (`scikit-learn==1.8.0`). Elle ne contient ni mlflow, ni dvc, ni pytest. La raison principale : la clé API ne doit jamais se retrouver dans un artefact partageable, et le modèle doit pouvoir changer sans reconstruire l'image. L'image unique reste simple tant que le projet est petit.

## Conséquences

- Ce qui entre dans l'image : le code (`maintai/`, `ui/`) et les bibliothèques. Ce qui arrive au lancement : le modèle (`./models:/app/models:ro`), les données (`./data:/app/data:ro`) et la clé (`env_file: .env`). Le `.dockerignore` garantit cette séparation.
- Le cache de build est efficace : comme les bibliothèques sont installées avant que le code soit copié, une modification du code se reconstruit en environ 3 s au lieu de 70 s.
- L'API écoute sur `0.0.0.0`. Avec `127.0.0.1`, elle serait injoignable depuis le PC.
- Dans Compose, l'interface appelle `http://api:8000` (le nom du service), et non `localhost`.
- À surveiller :
  - l'image pèse 1,13 Go sur le disque, dont une bonne part pour Streamlit, qui ne sert pas à l'API. Si la taille devient gênante, il faudra passer à l'option 3 ;
  - le conteneur tourne en `root` ;
  - `depends_on` n'attend pas que l'API soit prête. Un `healthcheck` sur `/health` corrigerait ce point.
