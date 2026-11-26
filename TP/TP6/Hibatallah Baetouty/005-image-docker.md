# ADR 005 : le modèle n'entre pas dans l'image, il arrive par un volume

Date : 26/11/2026 · Auteurs : Hibatallah Baetouty

## Contexte

MaintAI doit tourner sur un serveur où personne ne prépare de `.venv`. On emballe donc le
code et les bibliothèques dans une image Docker (`maintai:0.4.0`). Reste une question :
le modèle entraîné (`models/model.joblib`, ~ quelques centaines de ko, plus
`model_info.json` et `metrics.json`) fait-il partie de l'image, ou arrive-t-il au
lancement du conteneur ?

Deux contraintes du projet pèsent sur la réponse :
- le modèle est réentraîné bien plus souvent que le code ne change (TP5 : plusieurs runs,
  seuils et hyperparamètres différents) ;
- une image peut être poussée sur un registre et partagée, alors que les données et la clé
  API sont privées.

## Options étudiées

1. **Le modèle dans l'image** (`COPY models/ ./models/` dans le Dockerfile)
   - Avantages : un seul objet à déployer, le conteneur démarre sans rien monter, la
     version du modèle est tracée avec la version de l'image (`maintai:0.4.0` = ce code +
     ce modèle), et on ne peut pas se tromper de chemin au `docker run`.
   - Inconvénients : chaque réentraînement oblige à reconstruire et repousser l'image
     alors que *pas une ligne de code* n'a changé ; l'image grossit ; le modèle est entraîné
     sur des données clients, donc il ne doit pas partir dans une image qu'on partage.

2. **Le modèle par un volume** (`-v "%cd%\models:/app/models:ro"`, ou `./models:/app/models:ro`
   dans `compose.yaml`)
   - Avantages : le modèle se remplace sans rebuild (on redémarre le conteneur) ; l'image
     reste légère et partageable ; `:ro` garantit que le conteneur ne peut pas écraser le
     modèle ; c'est la suite logique de la séance 7 (le modèle est une donnée, pas du code).
   - Inconvénients : le conteneur ne démarre plus "tout seul" — il faut penser au `-v`, et
     si on l'oublie l'API répond `"model_loaded": false` puis 503 (on l'a vu, piège 1) ;
     la correspondance image ↔ modèle n'est plus automatique, il faut la noter ailleurs
     (`model_info.json`).

## Décision

**Option 2 : le modèle arrive par un volume en lecture seule.** La raison principale est
le rythme : le modèle change à chaque entraînement, le code non. Reconstruire l'image pour
remplacer un fichier `.joblib` ferait payer un build complet à chaque expérience du TP5 —
**69,4 s mesurées**, contre 3,3 s lorsque seul le code change (mesures exécutées sur la
machine de mon binôme, mon moteur Docker étant en panne ; cf. §9 du compte rendu).
S'ajoute la raison de confidentialité : une image peut être partagée, un modèle entraîné
sur les relevés d'un client ne doit pas l'être.

Même raisonnement pour les deux autres éléments variables :
- les **données** (`data/sensors.csv`) : volume aussi (`./data:/app/data:ro` pour le service
  `ui`, qui en a besoin pour l'onglet « Données ») ;
- la **clé API** : `--env-file .env` / `env_file: .env`. Un secret écrit dans une image y
  reste, dans l'historique des couches, même si une instruction suivante le supprime.

### Ce que `.dockerignore` laisse dehors, et pourquoi

| Laissé dehors | Pourquoi |
|---|---|
| `data/` | lourd et privé ; arrive par un volume |
| `models/` | change à chaque entraînement ; arrive par un volume (cet ADR) |
| `.env` | secret : il ne doit jamais se retrouver dans une couche partageable |
| `mlflow.db`, `mlruns/` | le suivi des entraînements n'a aucun rôle pour *servir* l'API |
| `.dvc/` | cache de versionnement des données, inutile et volumineux dans l'image |
| `.venv/` | l'environnement du PC (Windows) ne fonctionnerait pas dans une image Linux ; l'image refait son `pip install` |
| `tests/`, `*.egg-info/`, `dist/`, `build/`, `.git/`, caches | on ne teste ni ne construit dans l'image de production |

Ces exclusions ont aussi un effet direct sur le build : tout ce qui est ignoré n'est pas
envoyé au démon Docker comme contexte de build, donc le build démarre plus vite.

## Conséquences

**Ce que ça facilite.** Remplacer le modèle = déposer le nouveau `model.joblib` dans
`models/` et redémarrer le conteneur ; aucun rebuild. L'image reste la même pour tous les
environnements (dev, serveur) : seuls les volumes et le `.env` changent. L'image peut être
poussée sur un registre sans fuite de secret ni de données — et elle ne grossit pas à chaque
réentraînement, ce qui était l'objet de la décision.

**Ce que ça rend plus difficile.** Le lancement comporte une étape de plus, facile à
oublier : sans `-v`, l'API démarre mais répond `"model_loaded": false` puis 503 sur
`/v1/predict`. Il faut donc documenter la commande de lancement (README, `compose.yaml`)
et, idéalement, surveiller `/health` : c'est lui qui dit si le modèle a été trouvé.

**Ce qu'il faudra surveiller.** Deux points.

*La correspondance image ↔ modèle.* Rien n'empêche de monter un modèle entraîné avec une
autre version de scikit-learn que celle figée dans `requirements-docker.txt`
(`scikit-learn==1.8.0`). `model_info.json` doit rester à jour pour pouvoir vérifier, et un
`/health` qui renvoie aussi la version du modèle serait un bon ajout. L'exécution le montre
concrètement : sur la machine de mon binôme, `/v1/predict` renvoie
`"model_version":"2026-11-26T09:35:20Z"` — l'horodatage du modèle **monté**, pas de l'image.
Deux machines avec la même `maintai:0.4.0` ne renvoient donc pas la même valeur. C'est la
conséquence directe de cette décision, et la raison pour laquelle il faut exposer cette
information quelque part.

*La taille de l'image.* Sortir le modèle de l'image ne la rend pas petite pour autant :
mesurée, `maintai:0.4.0` pèse **1,13 GB sur le disque** (260 MB compressés), modèle et
données exclus. L'essentiel vient des bibliothèques, dont Streamlit, qui ne sert qu'à
l'interface et dont l'API n'a aucun besoin. Cet ADR ne tranche que la question du modèle ;
si la taille devient gênante, il faudra un ADR séparé sur le découpage — deux images (une
par service) ou un build multi-étapes.
