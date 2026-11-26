# Compte rendu · TP6 : conteneuriser MaintAI (Docker, Docker Compose)

**Groupe :G1 ·  **Membres :Rim ZAKI ·  **Date :** 26/11/2026

---

## 1. Mise en place (dans `TP/TP6`)

Sortie de `docker run hello-world` (première ligne) et de `docker version` (lignes Client et Server) :

```
Hello from Docker!

Client:  Version 29.9.3
Server: Docker Desktop 4.100.1 (247138)
 Engine: Version 29.9.3   OS/Arch linux/amd64
```

Dernière ligne de `python -m pytest` après la mise en place :

```
38 passed, 4 warnings in 19.68s
```

## 2. Image et conteneur (pendant le premier build)

1. Quelle différence entre une image et un conteneur ?
   Une **image** est un modèle figé, en lecture seule : un système de fichiers en couches (Python, les bibliothèques, le code) plus une commande de démarrage. Un **conteneur** est une instance de cette image en cours d'exécution : un processus isolé, avec sa propre couche inscriptible, son réseau et ses volumes. On construit une image une fois (`docker build`), et on en lance autant de conteneurs qu'on veut (`docker run`). C'est le même rapport qu'entre une classe et un objet.
2. Pourquoi `COPY requirements-docker.txt` est-il placé avant `COPY maintai` ?
   Docker met chaque instruction en cache et réutilise ce cache tant que les fichiers copiés n'ont pas changé. L'installation des bibliothèques (`pip install`) est l'étape lente, et la liste des bibliothèques change rarement. En copiant `requirements-docker.txt` seul d'abord, une modification du code invalide seulement le `COPY maintai` et les étapes qui suivent : le `pip install` reste en cache (le build passe de 69 s à 3 s).
3. Pourquoi `requirements-docker.txt` contient-il `scikit-learn==1.8.0` et pas `scikit-learn>=1.5` ?
   Le modèle `model.joblib` a été écrit par scikit-learn 1.8.0 (voir `model_info.json`). Un fichier pickle/joblib n'est garanti lisible qu'avec la version qui l'a produit. Avec `>=1.5`, un build futur pourrait installer une autre version : le chargement afficherait un avertissement, échouerait, ou donnerait des prédictions différentes. Figer la version rend l'image reproductible et compatible avec le modèle.
4. Pourquoi ni `mlflow`, ni `dvc`, ni `pytest` dans l'image ?
   L'image sert uniquement à **servir** le modèle (l'API et l'interface). On n'y entraîne pas, on n'y versionne pas les données et on n'y lance pas les tests : ces outils restent sur le poste de développement. Les ajouter alourdirait l'image (mlflow à lui seul tire des centaines de Mo), ralentirait le build et augmenterait la surface d'attaque sans rien apporter en production.

## 3. Sprint 1 : le Dockerfile

Votre `Dockerfile` :

```dockerfile
# Image de MaintAI : le code et ses bibliothèques, sans les données ni le modèle.
# Construire : docker build -t maintai:0.4.0 .
FROM python:3.11-slim
WORKDIR /app
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt
COPY maintai ./maintai
COPY ui ./ui
ENV MAINTAI_MODELS_DIR=/app/models \
    MAINTAI_DATA_PATH=/app/data/sensors.csv
EXPOSE 8000
CMD ["uvicorn", "maintai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

| Build | Durée | Taille de l'image (`docker images`) |
|---|---|---|
| premier build (`--no-cache`) | 69,4 s | 1,13 GB sur le disque (260 MB compressés) |
| après une modification de `maintai/predict.py` | 3,3 s | 1,13 GB sur le disque (260 MB compressés) |

Que signifie `CACHED` dans le journal du second build ?

`CACHED` veut dire que Docker a réutilisé la couche déjà construite au lieu de rejouer l'instruction. Au second build, `FROM`, `WORKDIR`, `COPY requirements-docker.txt` et `RUN pip install` sont `CACHED`, car aucun de leurs fichiers d'entrée n'a changé. Seuls `COPY maintai` (le fichier `predict.py` a changé) et les instructions suivantes sont reconstruits. D'où 3 s au lieu de 69 s.

## 4. Sprint 1 : lancer un conteneur

Votre commande `docker run` (PowerShell) :

```
docker run -d --name maintai-api -p 8000:8000 --env-file .env -v "${PWD}\models:/app/models:ro" maintai:0.4.0
```

| Essai | Réponse |
|---|---|
| `GET /health` | `200` `{"status":"ok","model_loaded":true}` |
| `POST /v1/predict` sans clé | `401` `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict` avec la clé | `200` `{"failure_probability":0.9475,"alert":true,"threshold":0.3,"model_version":"2026-11-26T09:35:20Z"}` |

**Piège 1.** Sans l'option `-v ...models...`, que répondent `/health` et `/v1/predict` ? Pourquoi ?

`/health` répond `{"status":"ok","model_loaded":false}` et `/v1/predict` (avec la clé) répond `503` : `{"detail":"Modèle non chargé : lancez python -m maintai.train puis redémarrez l'API"}`. Le modèle n'est pas dans l'image (`models/` figure dans le `.dockerignore`), donc `/app/models` est vide dans le conteneur. Au démarrage, `Predictor.load` lève `FileNotFoundError`, l'API démarre quand même sans modèle, et le signale. C'est le volume qui apporte le modèle du PC dans le conteneur.

**Piège 2.** Avec `--host 127.0.0.1`, que disent `docker logs test` et `http://localhost:8002/health` ? Pourquoi ?

`docker logs test` montre une API qui a démarré normalement :

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Pourtant, `curl http://localhost:8002/health` échoue avec `curl: (52) Empty reply from server`. Dans le conteneur, `127.0.0.1` désigne l'interface de bouclage **du conteneur**. Docker redirige le port 8002 du PC vers l'interface réseau du conteneur (`eth0`), sur laquelle uvicorn n'écoute pas. L'API n'accepte donc que les connexions venant de l'intérieur du conteneur. Avec `0.0.0.0`, elle écoute sur toutes les interfaces et devient joignable depuis le PC.

## 5. Sprint 2 : Docker Compose

Votre `compose.yaml` :

```yaml
# MaintAI en deux conteneurs : l'API et l'interface Streamlit.
# Lancer : docker compose up --build      Arrêter : docker compose down

services:
  api:
    build: .
    image: maintai:0.4.0
    env_file: .env                     # MAINTAI_API_KEY, comme au TP2
    ports:
      - "8000:8000"                    # PC:conteneur
    volumes:
      - ./models:/app/models:ro

  ui:
    image: maintai:0.4.0
    command: ["python", "-m", "streamlit", "run", "ui/app.py",
              "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
    environment:
      MAINTAI_API_URL: http://api:8000
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data:ro
    depends_on:
      - api
```

Sortie de `docker compose ps` :

```
NAME        IMAGE           COMMAND                  SERVICE   CREATED          STATUS          PORTS
tp6-api-1   maintai:0.4.0   "uvicorn maintai.api…"   api       30 minutes ago   Up 30 minutes   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
tp6-ui-1    maintai:0.4.0   "python -m streamlit…"   ui        30 minutes ago   Up 30 minutes   0.0.0.0:8501->8501/tcp, [::]:8501->8501/tcp
```

Quelle URL affiche la barre latérale de l'interface ? D'où vient-elle ?

La barre latérale affiche `http://api:8000`. Cette valeur vient de la variable d'environnement `MAINTAI_API_URL`, définie dans la section `environment` du service `ui` de `compose.yaml`. `ui/app.py` la lit avec `os.getenv("MAINTAI_API_URL", "http://localhost:8000")`. Hors de Compose, la variable est absente et la valeur par défaut `localhost` s'applique.

Résultat des deux commandes `docker compose exec ui ...` (avec `api` puis avec `localhost`). Pourquoi la seconde échoue-t-elle ?

```
> docker compose exec ui python -c "import httpx;print(httpx.get('http://api:8000/health').text)"
{"status":"ok","model_loaded":true}

> docker compose exec ui python -c "import httpx;print(httpx.get('http://localhost:8000/health').text)"
httpx.ConnectError: [Errno 111] Connection refused
```

Compose place les deux services sur un même réseau privé, avec un DNS interne qui associe le nom de service `api` à l'adresse IP du conteneur de l'API. Dans le conteneur `ui`, `localhost` désigne le conteneur `ui` lui-même, où rien n'écoute sur le port 8000 : la connexion est refusée. Chaque conteneur a son propre `localhost`.

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
38 passed, 4 warnings in 19.68s
```

## 6. Décision : l'ADR 005

Dans `docs/adr/005-image-docker.md`. Résumez ici votre décision en deux phrases :

L'image `maintai:0.4.0` ne contient que le code et les bibliothèques aux versions figées (`scikit-learn==1.8.0`, sans mlflow, dvc ni pytest). Le modèle, les données et la clé API arrivent au lancement par des volumes en lecture seule et `env_file`. Une seule image sert à la fois l'API et l'interface : l'image ne contient aucun secret, un nouveau modèle se déploie sans rebuild, et le projet reste simple.

## 7. Questions de compréhension

1. Qu'est-ce qui entre dans l'image, et qu'est-ce qui arrive au lancement ? Donnez le moyen pour chaque élément.
   - **Dans l'image**, par `docker build` :
     - le système et Python (`FROM python:3.11-slim`) ;
     - les bibliothèques (`COPY requirements-docker.txt` puis `RUN pip install`) ;
     - le code (`COPY maintai`, `COPY ui`) ;
     - les chemins par défaut (`ENV`) et la commande de démarrage (`CMD`).
   - **Au lancement**, par `docker run` ou `compose` :
     - le modèle, par un volume (`-v ./models:/app/models:ro`) ;
     - les données, par un volume (`./data:/app/data:ro`) ;
     - la clé API et les origines CORS, par `--env-file .env` / `env_file` ;
     - l'URL de l'API pour l'interface, par `environment: MAINTAI_API_URL` ;
     - les ports, par `-p` / `ports`.
2. Pourquoi la clé API n'est-elle jamais dans l'image ?
   Une image se partage : on la pousse sur un registre, on la donne à un collègue, on la déploie sur plusieurs serveurs. Tout ce qu'elle contient est lisible, avec `docker history`, `docker cp` ou en extrayant ses couches. Supprimer le fichier dans une couche ultérieure ne l'efface pas des couches précédentes. La clé mettrait donc l'API à la merci de quiconque obtient l'image, et on ne pourrait pas la changer sans reconstruire. En la passant au lancement (`.env`, exclu par le `.dockerignore` et le `.gitignore`), chaque environnement a sa propre clé, et la même image sert partout.
3. Livrer un modèle (TP4, TP5) : qu'est-ce que Docker ajoute à la liste ?
   Le TP4 livrait le code et les versions figées des bibliothèques (wheel, `requirements.txt`), et le TP5 livrait la traçabilité du modèle et des données (MLflow, DVC). Docker ajoute **l'environnement d'exécution complet** : le système, la version de Python et les bibliothèques exactes, dans un artefact unique (`maintai:0.4.0`) qui tourne à l'identique sur toute machine équipée de Docker, sans `pip install` ni venv. Il ajoute aussi la description du déploiement : les ports, les volumes, les variables d'environnement, et l'assemblage de plusieurs services dans `compose.yaml`.

## 8. Le rendu Git

- Lien de la pull request : …
- Le tag `tp6` existe sur GitHub : oui / non
- `git status` avant le commit : `.env`, `models/` ou `data/*.csv` apparaissaient-ils ? oui / non

## 9. Ce qui reste flou

- La taille de l'image : 1,13 GB sur le disque pour une API de quelques centaines de lignes. Une grande partie vient de Streamlit, dont l'API n'a pas besoin. Faut-il deux images séparées, ou un build multi-étapes ?
- `depends_on` démarre l'interface après le conteneur de l'API, mais n'attend pas que l'API soit prête à répondre. Comment bien utiliser un `healthcheck` dans Compose ?
- Le conteneur tourne en `root` : quel est le risque concret, et comment ajouter un utilisateur non privilégié (`USER`) sans casser les volumes ?
