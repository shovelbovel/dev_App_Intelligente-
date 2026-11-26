# Compte rendu · TP6 : conteneuriser MaintAI (Docker, Docker Compose)

**Groupe :** 5IAD G1 (Moulay Youssef)  ·  **Membres :** Hibatallah Baetouty  ·  **Date :** 26/11/2026, 11:45

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP6.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

> ⚠️ **À lire avant de corriger.** Tout ce qui ne dépend pas du démon Docker a été fait et
> vérifié sur ma machine : fichiers Docker écrits, `38 passed`, ADR 005 rédigé. En revanche
> le moteur Docker de mon PC est en panne (détail en partie 9 : le service Windows
> `vmcompute` n'est pas installé, une transaction de servicing Windows reste bloquée).
> Les sorties de `docker build` / `docker run` / `docker compose` des parties 1, 3, 4 et 5
> ont donc été **exécutées sur la machine de mon binôme**, à partir des mêmes fichiers, et
> sont signalées comme telles à chaque emplacement. Rien n'est inventé. Les « pourquoi »
> sont répondus par le code, indépendamment de l'exécution.

---

## 1. Mise en place (dans `TP/TP6`)

Sortie de `docker run hello-world` (première ligne) et de `docker version` (lignes Client et Server) :

```
> docker version
Client:
 Version:           29.9.3
 API version:       1.56
 OS/Arch:           windows/amd64
 Context:           desktop-linux

Server:
request returned 500 Internal Server Error for API route and version
http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.56/version

> docker run hello-world
request returned 500 Internal Server Error for API route and version
http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/_ping
```

Le client Docker est bien installé (29.9.3) ; c'est le **serveur** (le démon, dans la VM
WSL2) qui ne démarre pas. Cf. partie 9.

Les mêmes commandes, **exécutées sur la machine de mon binôme** :

```
Hello from Docker!

Client:  Version 29.9.3
Server: Docker Desktop 4.100.1 (247138)
 Engine: Version 29.9.3   OS/Arch linux/amd64
```

On y lit ce que ma machine ne montre pas : un **Server** qui répond, avec un moteur
`linux/amd64`. Ce « linux » sur un PC Windows, c'est justement la VM WSL2 — celle qui ne
démarre pas chez moi.

Dernière ligne de `python -m pytest` après la mise en place :

```
5 failed, 33 passed, 4 warnings in 32.58s
```

Les cinq échecs sont bien les cinq tests de `tests/test_docker.py` qui lisent les fichiers
Docker encore à l'état de TODO (le sixième, celui sur les versions figées de
`requirements-docker.txt`, passait déjà).

## 2. Image et conteneur (pendant le premier build)

1. **Quelle différence entre une image et un conteneur ?**
   L'image est le résultat figé de la recette (le `Dockerfile`) : un empilement de couches en
   lecture seule, nommé et versionné (`maintai:0.4.0`). Le conteneur est une *exécution* de
   cette image : un processus isolé, avec sa propre couche d'écriture par-dessus celles de
   l'image, son propre système de fichiers et son propre réseau. La même image peut donner
   autant de conteneurs qu'on veut — on le fait dans ce TP, `maintai-api` sur le port 8000 et
   `test` sur 8002 à partir de la même image — et ce qu'un conteneur écrit disparaît avec
   lui, alors que l'image ne change pas. L'image est au conteneur ce que la classe est à
   l'objet, ou ce que le `.whl` du TP4 est au `pip install` qui l'installe.

2. **Pourquoi `COPY requirements-docker.txt` est-il placé avant `COPY maintai` ?**
   À cause du cache de couches. Chaque instruction crée une couche ; au build suivant, Docker
   réutilise les couches jusqu'à la **première** dont l'entrée a changé, puis reconstruit tout
   ce qui suit. Le `pip install` est l'étape lente (pandas, scikit-learn, streamlit :
   plusieurs minutes) et c'est aussi celle qui change le plus rarement. Le code, à l'inverse,
   change à chaque modification. En copiant d'abord le seul `requirements-docker.txt`, la
   couche du `pip install` ne dépend que de ce fichier : modifier `maintai/predict.py`
   n'invalide que `COPY maintai` et la suite, et le rebuild devient très rapide. Dans l'ordre
   inverse, chaque virgule changée dans le code relancerait l'installation complète des
   bibliothèques.

3. **Pourquoi `requirements-docker.txt` contient-il `scikit-learn==1.8.0` et pas `scikit-learn>=1.5` ?**
   Parce que le modèle est chargé avec `joblib.load`, et qu'un `.joblib` est un objet Python
   sérialisé : il doit être relu par la **même version** de scikit-learn que celle qui l'a
   écrit — `models/model_info.json` l'enregistre d'ailleurs (`"sklearn_version": "1.8.0"`).
   Avec `>=1.5`, un build fait aujourd'hui et un build fait dans trois mois ne contiendraient
   pas la même bibliothèque, et le second pourrait refuser de charger le modèle ou, pire, le
   charger en changeant silencieusement les prédictions. Figer les versions, c'est ce qui rend
   l'image *reproductible* : même recette → même image → mêmes résultats.

4. **Pourquoi ni `mlflow`, ni `dvc`, ni `pytest` dans l'image ?**
   Parce que l'image sert à **servir** le modèle, pas à l'entraîner, le versionner ou le
   tester. MLflow et DVC sont les outils de l'atelier (séance 7, TP5) : ils n'ont aucun rôle
   quand l'API répond à une requête. Pytest non plus : les tests tournent avant le build, sur
   le PC et dans la CI. Les enlever a trois effets : une image bien plus légère, donc plus
   rapide à pousser et à télécharger ; un build plus court ; et une surface d'attaque plus
   petite (moins de dépendances, moins de failles à suivre). C'est la même logique que le
   `.dockerignore` : dans l'image, seulement ce qui sert en production.

## 3. Sprint 1 : le Dockerfile

Votre `Dockerfile` :

```dockerfile
# Principe de l'ordre des instructions : chaque ligne crée une COUCHE. Au build
# suivant, Docker réutilise les couches jusqu'à la première dont l'entrée a changé,
# puis reconstruit tout ce qui suit. D'où la règle : ce qui est lent et stable
# AVANT ce qui est rapide et instable.

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
```

Et le `.dockerignore`, dont les cinq lignes ajoutées sont les quatrième à huitième
sections ci-dessous. Un détail qui m'a servi : **Docker ne reconnaît un commentaire
qu'en début de ligne** dans ce fichier — un `#` placé après un motif serait lu comme
une partie du motif, et le motif ne filtrerait plus rien.

```
# L'environnement Python du PC : compilé pour Windows, inutilisable dans une image
# Linux. L'image refait son propre pip install (étape 3 du Dockerfile).
.venv/
# Bytecode régénéré automatiquement par Python.
__pycache__/
# Caches d'outils, locaux à la machine.
.pytest_cache/
.ruff_cache/
# Tout l'historique Git : lourd, et sans aucun usage à l'exécution.
.git/
# Artefacts de packaging du TP4 : le wheel construit, le dossier temporaire de build
# et les métadonnées laissées par "pip install -e .".
dist/
build/
*.egg-info/
# On ne teste pas dans l'image de production : les tests tournent avant le build,
# sur le PC et dans la CI. Les exclure retire aussi pytest du besoin de l'image.
tests/

# 1) Les données : lourdes, privées, et elles arrivent par un volume
#    (service ui de compose.yaml : ./data:/app/data:ro).
data/
# 2) Le modèle : il change à chaque entraînement alors que le code ne change pas.
#    L'inclure obligerait à reconstruire l'image pour remplacer un .joblib — c'est la
#    décision de l'ADR 005. Il arrive par un volume : ./models:/app/models:ro
models/
# 3) Le secret : la clé API arrive au lancement (--env-file .env / env_file: .env).
#    Un secret écrit dans une image y reste dans l'historique des couches, même si
#    une instruction suivante le supprime : docker history le retrouverait.
.env
# 4) Le suivi des entraînements (TP5) : la base et les artefacts MLflow servent à
#    comparer des runs, jamais à répondre à une requête de l'API.
mlflow.db
mlruns/
# 5) Le cache DVC (TP5) : versionnement des données, volumineux et hors sujet ici.
.dvc/
```

Après ce fichier et le `.dockerignore` complété, `python -m pytest` donne
`2 failed, 36 passed, 4 warnings in 32.98s` : les **trois** tests du sprint 1 passent (ordre
`pip install` / `COPY maintai`, `--host 0.0.0.0`, exclusions du `.dockerignore`), il ne reste
que les deux du sprint 2.

Mesures **exécutées sur la machine de mon binôme** (cf. §9), sur ce même `Dockerfile` :

| Build | Durée | Taille de l'image (`docker images`) |
|---|---|---|
| premier build (`--no-cache`) | 69,4 s | 1,13 GB sur le disque (260 MB compressés) |
| après une modification de `maintai/predict.py` | 3,3 s | 1,13 GB sur le disque (260 MB compressés) |

L'écart entre les deux lignes est exactement l'effet recherché par l'ordre des `COPY` :
**69,4 s → 3,3 s**, soit 21 fois plus rapide, pour une image de taille inchangée — le code
recopié ne pèse rien, c'est le `pip install` qui coûte.

**Que signifie `CACHED` dans le journal du second build ?**

`CACHED` devant une étape veut dire que Docker ne l'a **pas rejouée** : il a retrouvé une
couche déjà construite dont l'entrée est identique (même instruction, mêmes fichiers copiés)
et l'a réutilisée telle quelle. Ici, après avoir touché `maintai/predict.py`, on doit voir
`CACHED` sur `FROM`, `WORKDIR`, `COPY requirements-docker.txt` et surtout `RUN pip install`
— l'étape longue — puis une vraie exécution à partir de `COPY maintai`, parce que c'est la
première étape dont le contenu a changé. C'est tout l'intérêt de l'ordre choisi, et la
mesure ci-dessus le confirme : le second build tombe de 69,4 s à 3,3 s.

## 4. Sprint 1 : lancer un conteneur

Votre commande `docker run` :

```
docker run -d --name maintai-api -p 8000:8000 --env-file .env -v "%cd%\models:/app/models:ro" maintai:0.4.0
```

Morceau par morceau : `-d` en arrière-plan ; `--name` pour pouvoir écrire
`docker logs maintai-api` ; `-p 8000:8000` publie le port du conteneur sur le PC
(PC:conteneur) ; `--env-file .env` injecte `MAINTAI_API_KEY` **au lancement**, sans l'écrire
dans l'image ; `-v "%cd%\models:/app/models:ro"` monte le dossier `models` du PC dans le
conteneur, en lecture seule.

Essais **exécutés sur la machine de mon binôme** (cf. §9) :

| Essai | Réponse |
|---|---|
| `GET /health` | `200` `{"status":"ok","model_loaded":true}` |
| `POST /v1/predict` sans clé | `401` `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict` avec la clé | `200` `{"failure_probability":0.9475,"alert":true,"threshold":0.3,"model_version":"2026-11-26T09:35:20Z"}` |

Ces trois réponses sont exactement ce que prévoit le code : `maintai/api/security.py` lève
401 si l'en-tête `X-API-Key` est absent ou faux, et `main.py` renvoie `model_loaded` selon
que le `Predictor` a pu être chargé au démarrage. Un détail confirme au passage la décision
de l'ADR 005 : le `model_version` renvoyé (`2026-11-26T09:35:20Z`) est l'horodatage
d'entraînement du modèle **de mon binôme**, pas du mien. Il vient de `model_info.json`, qui
arrive par le volume — il suit donc le modèle monté, pas l'image. Deux machines portant la
même image `maintai:0.4.0` ne renvoient pas le même `model_version`, et c'est précisément
le but.

**Piège 1.** Sans l'option `-v ...models...`, que répondent `/health` et `/v1/predict` ? Pourquoi ?

`/health` répond quand même **200**, mais avec `"model_loaded": false` ; et `/v1/predict`,
une fois la clé acceptée, répond **503** avec « Modèle non chargé ». La raison est dans
`main.py` : le modèle est chargé une seule fois au démarrage, dans le `lifespan`, et le
`FileNotFoundError` y est attrapé — l'API démarre donc volontairement sans modèle, et c'est
`/health` qui le signale. Or le modèle n'est **pas** dans l'image (c'est la décision de
l'ADR 005) : sans le volume, `/app/models/model.joblib` n'existe tout simplement pas dans le
conteneur. Côté exploitation c'est un bon comportement : le conteneur ne meurt pas au
démarrage, mais `/health` dit la vérité, ce qui permet à un orchestrateur de ne pas lui
envoyer de trafic.

**Piège 2.** Avec `--host 127.0.0.1`, que disent `docker logs test` et `http://localhost:8002/health` ? Pourquoi ?

Les journaux montrent un uvicorn parfaitement content : `Uvicorn running on
http://127.0.0.1:8000`. Et pourtant `http://localhost:8002/health` ne répond pas (connexion
fermée, « page inaccessible ») — **sans aucune erreur dans les logs**, et c'est ça qui rend
le piège méchant. Explication : `127.0.0.1` ne désigne pas la même interface selon l'endroit
où on se place. Dans le conteneur, c'est la boucle locale **du conteneur** : uvicorn
n'accepte que les connexions venues de l'intérieur de ce conteneur. Or le `-p 8002:8000`
installe une redirection qui arrive sur l'interface réseau du conteneur (son adresse dans le
réseau Docker), pas sur sa boucle locale : personne n'écoute là. D'où `--host 0.0.0.0` dans
le `CMD` du Dockerfile — « écoute sur toutes les interfaces », la seule façon d'être
joignable depuis le PC.

## 5. Sprint 2 : Docker Compose

Votre `compose.yaml` :

```yaml
# Syntaxe YAML : deux espaces par niveau, jamais de tabulation ; une liste commence
# par un tiret. Ici, contrairement au .dockerignore, un "#" en fin de ligne est bien
# un commentaire.

services:

  # --- api : l'API MaintAI, construite depuis le Dockerfile du dossier courant ---
  api:
    # build: . → Compose construit l'image à partir du Dockerfile d'à côté.
    build: .
    # image: → le nom/tag donné à l'image construite. Le même que celui du TP
    # (docker build -t maintai:0.4.0 .), et c'est ce tag que le service ui réutilise
    # plus bas, pour ne pas construire deux fois la même chose.
    image: maintai:0.4.0
    # env_file → les variables de .env sont injectées AU LANCEMENT :
    # MAINTAI_API_KEY (comme au TP2). La clé n'est donc jamais dans l'image, et .env
    # est exclu par .dockerignore et par .gitignore.
    env_file: .env
    ports:
      # "PC:conteneur" → le port 8000 du conteneur devient http://localhost:8000 sur
      # le PC. C'est ce qui rend /docs et /health accessibles au navigateur. Cela
      # suppose que l'API écoute sur 0.0.0.0 (CMD du Dockerfile).
      - "8000:8000"
    volumes:
      # Le modèle n'est pas dans l'image (ADR 005) : il arrive ici.
      # "./models" = dossier du PC, à côté de ce fichier ; "/app/models" = chemin dans
      # le conteneur, celui fixé par ENV MAINTAI_MODELS_DIR ; ":ro" = lecture seule,
      # le conteneur ne peut pas écraser le modèle.
      # Sans cette ligne : /health répond model_loaded=false et /v1/predict → 503.
      - ./models:/app/models:ro

  # --- ui : l'interface Streamlit, MÊME image, autre commande -------------------
  ui:
    # Pas de "build:" ici : on réutilise l'image taguée par le service api, qui
    # contient déjà streamlit et le dossier ui/. Un seul build pour deux services.
    image: maintai:0.4.0
    # La commande remplace le CMD du Dockerfile (qui lançait uvicorn).
    # Elle commence par "python -m" : avec "streamlit" seul, le dossier courant ne
    # serait pas dans sys.path et on retomberait sur le "No module named 'maintai'"
    # du TP3.
    # --server.address=0.0.0.0 : même piège que l'API, sinon Streamlit n'écouterait
    #   que l'intérieur du conteneur et le port publié ne servirait à rien.
    # --server.headless=true : pas de tentative d'ouvrir un navigateur, et pas de
    #   question interactive au premier démarrage.
    command: ["python", "-m", "streamlit", "run", "ui/app.py",
              "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
    environment:
      # L'adresse de l'API VUE DEPUIS CE CONTENEUR. Ce n'est pas "localhost" :
      # localhost désignerait le conteneur ui lui-même, où seul Streamlit tourne
      # (port 8501). "api" est le nom du service, résolu par le DNS de Docker.
      # ui/app.py lit cette variable avec os.getenv.
      MAINTAI_API_URL: http://api:8000
    ports:
      # L'interface devient http://localhost:8501 sur le PC.
      - "8501:8501"
    volumes:
      # L'onglet "Données" lit data/sensors.csv (chemin fixé par
      # ENV MAINTAI_DATA_PATH), et les données sont exclues de l'image : volume.
      - ./data:/app/data:ro
    depends_on:
      # Démarre api avant ui. Attention : cela attend que le conteneur soit lancé, pas
      # que l'API réponde — l'interface peut donc s'ouvrir quelques secondes avant que
      # /health soit prêt (uvicorn met ~20 s à charger le modèle).
      - api
```

Sortie de `docker compose ps`, **exécutée sur la machine de mon binôme** (cf. §9) :

```
NAME        IMAGE           COMMAND                  SERVICE   CREATED          STATUS          PORTS
tp6-api-1   maintai:0.4.0   "uvicorn maintai.api…"   api       30 minutes ago   Up 30 minutes   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
tp6-ui-1    maintai:0.4.0   "python -m streamlit…"   ui        30 minutes ago   Up 30 minutes   0.0.0.0:8501->8501/tcp, [::]:8501->8501/tcp
```

Trois choses se lisent dans ce tableau. Les noms `tp6-api-1` / `tp6-ui-1` : Compose préfixe
par le nom du dossier (`TP6`) et numérote les instances. La colonne `IMAGE` est **la même**
pour les deux lignes (`maintai:0.4.0`) alors que la colonne `COMMAND` diffère (`uvicorn…`
contre `python -m streamlit…`) — un seul build pour deux services, exactement ce que visait
le `image:` partagé. Et les deux ports sont publiés sur `0.0.0.0`, donc joignables depuis
le PC.

**Quelle URL affiche la barre latérale de l'interface ? D'où vient-elle ?**

`http://api:8000`. Elle vient de la variable d'environnement `MAINTAI_API_URL`, définie dans
le service `ui` de `compose.yaml` et lue par `ui/app.py` :

```python
with st.sidebar:
    # --- Modifié au sprint 2 du TP6 : l'URL de l'API ne peut plus être en dur ---
    # Pourquoi : lancée par Docker Compose, l'interface tourne dans son propre
    # conteneur. "localhost" y désigne le conteneur ui lui-même, où seul Streamlit
    # écoute (port 8501) : l'API, qui vit dans un AUTRE conteneur, est injoignable
    # sous ce nom. Compose place les deux services sur un même réseau, où l'API
    # s'appelle "api" — d'où MAINTAI_API_URL=http://api:8000 dans compose.yaml.
    # os.getenv(nom, défaut) : on lit la variable si elle existe, sinon on garde
    # "http://localhost:8000" — le cas où uvicorn est lancé à la main sur le PC,
    # hors conteneur. Le même fichier marche donc dans les deux situations.
    # La valeur reste modifiable à la main : ce n'est que la valeur par défaut du
    # champ de saisie.
    defaut = os.getenv("MAINTAI_API_URL", "http://localhost:8000")
    url = st.text_input("URL de l'API", defaut)
```

`api` est le **nom du service** : Compose place les deux conteneurs sur un même réseau où
chacun est joignable par son nom, résolu par le DNS interne de Docker. Hors Compose (uvicorn
lancé à la main sur le PC), la variable n'existe pas et la valeur par défaut
`http://localhost:8000` reprend la main — d'où le choix d'un `os.getenv` avec défaut plutôt
qu'une valeur en dur.

Résultat des deux commandes `docker compose exec ui ...` (avec `api` puis avec `localhost`). Pourquoi la seconde échoue-t-elle ?

**Exécuté sur la machine de mon binôme** (cf. §9) :

```
> docker compose exec ui python -c "import httpx;print(httpx.get('http://api:8000/health').text)"
{"status":"ok","model_loaded":true}

> docker compose exec ui python -c "import httpx;print(httpx.get('http://localhost:8000/health').text)"
httpx.ConnectError: [Errno 111] Connection refused
```

La première renvoie bien `{"status":"ok","model_loaded":true}` ; la seconde échoue sur un
`httpx.ConnectError` — `[Errno 111] Connection refused`. Et c'est normal : la commande s'exécute **dans
le conteneur `ui`**, où `localhost` désigne le conteneur `ui` lui-même. Or dans ce conteneur
il n'y a que Streamlit, sur le port 8501 : rien n'écoute sur 8000. L'API vit dans un *autre*
conteneur, avec sa propre pile réseau ; il faut donc l'appeler par son nom de service,
`http://api:8000`. Si `http://localhost:8000` marche dans mon navigateur, c'est parce que le
navigateur tourne sur le PC et que `ports: "8000:8000"` a justement publié le port de l'API
sur le `localhost` **du PC**. Même mot, trois endroits différents : le PC, le conteneur `ui`,
le conteneur `api`.

**Enfin : `docker compose down`. Que supprime-t-elle ?**

Elle arrête puis **supprime les conteneurs** des deux services, ainsi que le réseau que
Compose avait créé pour eux. Elle ne supprime **pas** l'image `maintai:0.4.0` (elle reste
dans `docker images`, prête à relancer), ni les dossiers `models/` et `data/` du PC : ce sont
des montages, pas des volumes gérés par Docker, donc rien n'y touche — et ils sont montés en
`:ro`. Des volumes nommés, eux, ne partiraient qu'avec `docker compose down -v`.

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
38 passed, 4 warnings in 32.88s
```

## 6. Décision : l'ADR 005

Dans `docs/adr/005-image-docker.md`. Résumez ici votre décision en deux phrases :

Le modèle ne va pas dans l'image : il arrive au lancement par un volume en lecture seule
(`./models:/app/models:ro`), parce qu'il est réentraîné bien plus souvent que le code ne
change et qu'une image partageable ne doit pas emporter un modèle entraîné sur des données
clients. Même raisonnement pour les données (volume) et pour la clé API (`env_file: .env`) :
dans l'image, uniquement ce qui change au rythme du code.

## 7. Questions de compréhension

1. **Qu'est-ce qui entre dans l'image, et qu'est-ce qui arrive au lancement ? Donnez le moyen pour chaque élément.**

   | Élément | Où | Par quel moyen |
   |---|---|---|
   | Python 3.11 | dans l'image | `FROM python:3.11-slim` |
   | bibliothèques figées | dans l'image | `COPY requirements-docker.txt` + `RUN pip install` |
   | code (`maintai/`, `ui/`) | dans l'image | `COPY maintai/ ./maintai/`, `COPY ui/ ./ui/` |
   | chemins du modèle et des données | dans l'image | `ENV MAINTAI_MODELS_DIR`, `ENV MAINTAI_DATA_PATH` |
   | modèle (`model.joblib`, `model_info.json`) | au lancement | volume `-v "%cd%\models:/app/models:ro"` / `./models:/app/models:ro` |
   | données (`sensors.csv`) | au lancement | volume `./data:/app/data:ro` |
   | clé API | au lancement | `--env-file .env` / `env_file: .env` |
   | URL de l'API pour l'interface | au lancement | variable `MAINTAI_API_URL` dans `compose.yaml` |

   La règle qui résume tout : dans l'image, ce qui change au rythme du **code** ; au
   lancement, ce qui change au rythme des **données**, du **modèle** ou de
   l'**environnement**.

2. **Pourquoi la clé API n'est-elle jamais dans l'image ?**
   Parce qu'une image est faite pour être partagée (registre, collègue, serveur) et qu'elle
   garde tout son historique de couches : un secret écrit dedans y reste même si une
   instruction suivante le supprime, et `docker history` — ou un simple `docker run ... cat`
   — le retrouve. S'y ajoute que ce serait impraticable : il faudrait reconstruire l'image à
   chaque rotation de clé, et on ne pourrait pas utiliser la même image en dev et en
   production avec des clés différentes. La clé arrive donc au lancement, par
   `--env-file .env`, et `.env` est listé à la fois dans `.gitignore` et dans
   `.dockerignore`.

3. **Livrer un modèle (TP4, TP5) : qu'est-ce que Docker ajoute à la liste ?**
   Le TP4 (le wheel) livrait le **code** : il fallait encore un Python de la bonne version et
   un `pip install` sur la machine d'arrivée. Le TP5 (MLflow, DVC) livrait la
   **traçabilité** : quelles données, quels paramètres, quel modèle. Docker ajoute
   l'**environnement complet et figé** : l'OS minimal, l'interpréteur Python, les
   bibliothèques aux versions exactes, le code et la commande de démarrage, dans un seul
   objet nommé qui tourne à l'identique sur mon PC et sur un serveur où personne ne prépare
   de `.venv`. Autrement dit il supprime le « ça marche chez moi » : on ne livre plus une
   procédure d'installation, on livre une machine en état de marche. Et Compose ajoute la
   couche au-dessus : non plus un service, mais la **topologie** — API + interface, un
   réseau, qui dépend de qui — dans un fichier versionné.

## 8. Le rendu Git

- **Lien de la pull request :** aucun pour l'instant — le dépôt de ce TP est **local**
  (`git init` dans `S8-tp6`, travail sur la branche `tp6`), sans remote GitHub. Dès qu'un
  remote sera ajouté : `git push -u origin tp6`, puis pull request.
- **Le tag `tp6` existe sur GitHub :** non — il existe en local. Le tag `tp5` a lui aussi été
  posé en local sur le dépôt du TP5.
- **`git status` avant le commit : `.env`, `models/` ou `data/*.csv` apparaissaient-ils ?**
  **Non**, vérifié : `.gitignore` couvre `.env`, `models/` et `data/*.csv`, et
  `git status --short` ne les montre pas. Seul `data/.gitkeep` est suivi, ce qui est voulu.
  L'image, elle, ne va pas dans Git : elle se reconstruit depuis le `Dockerfile`.

## 9. Ce qui reste flou

Sur le principe de Docker, rien de flou — mais je n'ai pas pu exécuter le TP jusqu'au bout,
et je préfère l'écrire franchement plutôt que de remplir les cases au hasard.

Le moteur Docker ne démarre pas sur mon PC. Le client répond (`docker version` → 29.9.3) mais
le serveur renvoie `500 Internal Server Error`, et `wsl --status` dit que « la virtualisation
n'est pas activée ». Après diagnostic :

- l'hyperviseur Windows est bien chargé (`HypervisorPresent: True`,
  `hypervisorlaunchtype = Auto` — réglé parce que VMware Workstation 17.5 le laissait absent
  du BCD) ;
- `VirtualMachinePlatform`, `Microsoft-Hyper-V-All` et WSL sont signalés « Enabled » par
  DISM, **mais** le service `vmcompute` (Hyper-V Host Compute Service) n'existe pas
  (`sc query vmcompute` → erreur 1060) : c'est précisément ce que testent WSL2 et Docker ;
- la raison : l'installation de ces composants est en file d'attente et n'est jamais
  finalisée (`WinSxS\pending.xml` présent, 355 paquets dans `CBS\PackagesPending` dont
  `HyperV-Compute-Host`), et `CBS.log` montre `Deferring startup processing` puis
  `Deferring shutdown processing` à chacun des redémarrages de la soirée ;
- le log de Docker Desktop le confirme en une ligne :
  `engine linux/wsl failed to start: checking preconditions: Virtual Machine Platform not enabled`.

Pour que le compte rendu ne reste pas troué, les sorties des parties 1, 3, 4 et 5 ont été
produites **sur la machine de mon binôme**, à partir des mêmes fichiers, et sont signalées
comme telles à chaque emplacement. Reste à les rejouer sur mon PC dès qu'il est réparé
(débloquer la transaction de servicing Windows, puis redémarrer) : `docker build`, les deux
`docker run` avec leurs pièges, `docker compose up`. Les fichiers, eux, sont prêts et
validés par les tests : `38 passed`.

Deuxième point moins clair pour moi, et plus intéressant : la correspondance entre une
version d'image et une version de modèle. L'ADR 005 sort le modèle de l'image, donc
`maintai:0.4.0` ne dit plus *quel* modèle tourne. `/health` répond `model_loaded: true` mais
pas « lequel », alors que `model_info.json` contient `trained_at` et `sklearn_version`. Je
pense qu'il faudrait les exposer dans `/health` — mais je ne sais pas s'il est prudent de
publier des informations sur le modèle sur un endpoint ouvert, sans clé.
