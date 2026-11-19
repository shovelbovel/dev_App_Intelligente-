# Compte rendu · TP5 : suivre les entraînements (MLflow) et versionner les données (DVC)

**Groupe :** G1  ·  **Membres :** SAHIA ABDELALI  ·  **Date :** 19/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP5.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP5`)

Dernière ligne de `python -m pytest` après `pip install -r requirements.txt` et `pip install -e .` :

```
5 failed, 27 passed, 1 warning in 10.50s
```

Quels tests échouent, et pourquoi ?

Les 5 tests de `tests/test_tracking.py`. `log_run` n'est pas encore écrite (elle renvoie juste `""`), donc aucun run n'arrive dans MLflow et les tests tombent sur « aucun run MLflow : log_run n'a rien enregistré ».

Avant d'en arriver là, on a eu un souci avec Smart App Control (Windows). Il bloquait `pip.exe`, puis des DLL de `pyarrow` 26.0.1 et de `SQLAlchemy` 2.1.9, ce qui faisait planter l'import de scikit-learn et de MLflow. On est passés par `python -m pip` et on a installé des versions un peu plus anciennes (`pyarrow==21.0.0`, `sqlalchemy==2.0.41`). Même histoire qu'avec pandas au TP4.

Avant `pip install -e .`, où pointait le package `maintai` installé dans l'environnement ? Et après ?

On a créé un `.venv` neuf pour le TP5, donc avant `pip install -e .` maintai n'y était pas installé du tout. Dans l'environnement du TP4, il pointait encore vers le dossier du TP4 (`...\TP4\maintai-starter-tp4`). Après, il pointe vers le dossier du TP5 (`...\TP5\TP5`) en mode éditable : c'est bien le code du TP5 qui tourne.

## 2. Sprint 1 : MLflow

Votre fonction `log_run` (`maintai/tracking.py`) :

```python
def log_run(params: dict, metrics: dict, model, X_example, data_path: Path, experiment: str = EXPERIMENT) -> str:
    """Enregistre un entraînement : paramètres, version des données, métriques et modèle. Renvoie l'id du run."""
    mlflow.set_experiment(experiment)
    with mlflow.start_run() as run:
        mlflow.log_params(params)
        mlflow.log_param("data_md5", file_md5(data_path))
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(
            model,
            name="model",
            input_example=X_example,
            skops_trusted_types=TRUSTED_TYPES,
        )
    return run.info.run_id
```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
32 passed, 3 warnings in 24.87s
```

Vos runs (au moins quatre), relevés dans `mlflow ui` (mode « Model training ») :

| Commande | recall | precision | accuracy |
|---|---|---|---|
| `python -m maintai.train` | 0.750 | 0.622 | 0.904 |
| `python -m maintai.train --C 0.01` | 0.691 | 0.653 | 0.908 |
| `python -m maintai.train --threshold 0.2` | 0.838 | 0.543 | 0.882 |
| `python -m maintai.train --model forest` | 0.728 | 0.562 | 0.886 |
| `python -m maintai.train --model forest --threshold 0.2` | 0.831 | 0.479 | 0.854 |

Quel run choisiriez-vous pour MaintAI, et pourquoi ? (Rappel : une panne manquée coûte plus cher qu'une fausse alerte.)

Le run `--threshold 0.2` (régression logistique, C = 1.0). C'est celui qui rate le moins de pannes : 22 sur les 136 du jeu de test, contre 34 avec le réglage par défaut. On a plus de fausses alertes (précision 0.543), mais ça reste le bon choix puisqu'une panne manquée coûte plus cher. Notre essai, la forêt au même seuil, fait moins bien sur les trois métriques, donc pas de raison de prendre un modèle plus lourd.

Dans `mlflow ui`, ouvrez le modèle d'un run. Quelle version de scikit-learn est indiquée dans son `requirements.txt` ? Quel problème du TP4 cela règle-t-il ?

`scikit-learn==1.8.0`. Au TP4, le wheel installé seul récupérait scikit-learn 1.9.1, et le modèle entraîné en 1.8.0 donnait un `InconsistentVersionWarning`. Maintenant les versions exactes sont rangées avec le modèle, on sait dans quel environnement le recharger.

Où MLflow enregistre-t-il les runs sur votre disque ? Ces fichiers vont-ils dans Git ? Pourquoi ?

Dans `mlflow.db` à la racine du projet (paramètres et métriques) et dans `mlruns/` (les modèles). Ils ne vont pas dans Git, ils sont dans le `.gitignore`. Ce sont des fichiers générés, qui grossissent à chaque run, et un modèle n'a rien à faire dans un dépôt de code.

## 3. Sprint 2 : DVC

Contenu de `data/sensors.csv.dvc` après `dvc add data/sensors.csv` :

```
outs:
- md5: 73e0b7cb3c6f795c70c3ddf970b99c15
  size: 126815
  hash: md5
  path: sensors.csv
```

Comparez la valeur `md5` de ce fichier au paramètre `data_md5` de votre dernier run MLflow. Que constatez-vous ?

C'est exactement la même valeur, `73e0b7cb3c6f795c70c3ddf970b99c15`. `file_md5` calcule l'empreinte de la même façon que DVC, donc depuis un run MLflow on retrouve directement la version des données qui a servi.

Pourquoi `data/sensors.csv` ne va pas dans Git, alors que `data/sensors.csv.dvc` y va ?

Le CSV est gros et change à chaque nouvelle version, Git n'est pas fait pour ça (il est d'ailleurs dans le `.gitignore`). Le `.dvc` fait 5 lignes : juste l'empreinte qui pointe vers le fichier dans le stockage DVC. En le commitant, chaque commit sait quelle version des données il utilise.

Après `python -m maintai.dataset --n 8000 --seed 7`, que dit `dvc status` ?

```
data\sensors.csv.dvc:
	changed outs:
		modified:           data\sensors.csv
```

| Version | Commit Git (`git log --oneline`) | md5 (8 premiers caractères) | Nombre de lignes |
|---|---|---|---|
| v1 | `1ddb987 Données v1` | `73e0b7cb` | 5001 (5 000 relevés + l'en-tête) |
| v2 | `731cabb Données v2` | `93fdeef2` | 8001 (8 000 relevés + l'en-tête) |

Revenez à la v1 (`git checkout <commit> -- data/sensors.csv.dvc`, puis `dvc checkout`). Combien de lignes contient `data/sensors.csv` ? Puis revenez à la v2.

5001 lignes, on retrouve bien la v1. Retour à la v2 avec `git checkout HEAD -- data/sensors.csv.dvc` puis `dvc checkout` : de nouveau 8001 lignes. Le changement est immédiat, DVC reprend le fichier dans son cache.

Supprimez `data/sensors.csv` et le dossier `.dvc/cache`, puis lancez `dvc pull`. Que se passe-t-il ?

`dvc status` indique « not in cache ». `dvc pull` va chercher le fichier dans le stockage (`1 file fetched and 1 file added`) et le remet en place : 8001 lignes, même md5 que la v2. Ça marche parce qu'on avait fait `dvc push` après chaque version. Sans ça, les données auraient été perdues.

## 4. Relier modèle et données

Entraînez un modèle sur la v2. Dans `mlflow ui`, comparez ce run à celui de la v1 avec les mêmes réglages :

| Run | data_md5 (8 caractères) | n_train | recall | precision |
|---|---|---|---|---|
| v1 (`e8edbce3`) | `73e0b7cb` | 4000 | 0.838 | 0.543 |
| v2 (`1928a9e0`) | `93fdeef2` | 6400 | 0.824 | 0.567 |

Réglages identiques pour les deux : régression logistique, C = 1.0, seuil 0.2.

Peut-on dire que le modèle v2 est « meilleur » ? Pourquoi faut-il être prudent en comparant deux runs entraînés sur des données différentes ?

Non, pas vraiment. Le recall baisse un peu et la précision monte, mais les deux runs ne sont pas notés sur le même jeu de test. La v2 a plus de relevés et un taux de panne différent (12,8 % au lieu de 13,6 %), donc les écarts peuvent venir des données autant que du modèle. Pour comparer proprement, il faut le même `data_md5`, ou au moins le même jeu de test.

## 4 bis. Recherche sur grille (25 entraînements)

Au lieu de tester les réglages un par un, on a essayé toutes les combinaisons de 5 valeurs de C et de 5 seuils, soit 25 runs. Le script est `maintai/grid_search.py` :

```
python -m maintai.grid_search
```

Chaque combinaison devient un run MLflow, dans une expérience à part (`maintai-grid`) pour ne pas mélanger avec le tableau de la partie 2. Régression logistique, données v2 (`data_md5` = `93fdeef2`), environ 1 min 20. `models/` n'est pas touché. On a ajouté deux tests dans `tests/test_grid_search.py` : `34 passed`.

Recall / précision de chaque combinaison (jeu de test : 1 600 relevés, 205 pannes) :

| C \ seuil | 0.1 | 0.15 | 0.2 | 0.25 | 0.3 |
|---|---|---|---|---|---|
| 0.001 | 1.000 / 0.253 | 0.917 / 0.437 | 0.737 / 0.616 | 0.517 / 0.774 | 0.400 / 0.872 |
| 0.01 | 0.966 / 0.384 | 0.893 / 0.470 | 0.829 / 0.547 | 0.761 / 0.612 | 0.698 / 0.688 |
| 0.1 | 0.922 / 0.445 | 0.863 / 0.496 | 0.829 / 0.559 | 0.790 / 0.625 | 0.732 / 0.652 |
| 1.0 | 0.907 / 0.458 | 0.859 / 0.506 | 0.824 / 0.567 | 0.780 / 0.620 | 0.741 / 0.650 |
| 10.0 | 0.902 / 0.457 | 0.859 / 0.507 | 0.824 / 0.567 | 0.780 / 0.620 | 0.741 / 0.650 |

Ce qu'on en retient :

- C change peu de chose dès qu'il vaut 0.1 ou plus, et entre 1 et 10 les résultats sont presque identiques. C'est le seuil qui fait tout.
- Avec C = 0.001 le modèle est trop régularisé. Au seuil 0.1 il alerte presque tout le temps : recall 1.0, mais précision 0.25.
- On retrouve le run de la partie 4 (C = 1.0, seuil 0.2 : 0.824 / 0.567), donc c'est cohérent.

Pour choisir, on a pris le meilleur recall avec une précision d'au moins 0.5, c'est-à-dire pas plus d'une fausse alerte par panne détectée. La grille sort C = 10, seuil 0.15 : recall 0.859, précision 0.507 (run `b96b01c1`). Par rapport à notre choix de l'ADR (seuil 0.2), ça fait 7 pannes détectées en plus (176 au lieu de 169), mais 42 fausses alertes en plus (171 au lieu de 129). On garde 0.2 : on est juste à la limite de la règle, et le seuil est choisi sur le jeu de test, donc ce petit gain est fragile. Le seuil 0.15 reste une piste si l'équipe de maintenance accepte plus d'alertes.

## 5. Décision : l'ADR 004

Dans `docs/adr/004-choix-du-modele.md` : le modèle et le seuil retenus, à partir de votre tableau MLflow. Indiquez l'identifiant du run et le `data_md5` de la version des données utilisée.

Fait : régression logistique, C = 1.0, seuil 0.2. Run `e8edbce38b04411898929d27fb75cc93`, `data_md5` = `73e0b7cb3c6f795c70c3ddf970b99c15`.

## 6. Questions de compréhension

1. Quelle différence entre Git, DVC et MLflow ? Que versionne chacun ?
   Git versionne le code, plus les petits fichiers `.dvc`. DVC versionne les données : Git ne garde que leur empreinte, le vrai fichier est dans le stockage DVC. MLflow garde l'historique des entraînements : réglages, métriques, modèle et versions des bibliothèques.
2. Pourquoi le stockage DVC est-il ajouté avec `--local` dans ce TP ? Que faudrait-il pour que tout le groupe partage les mêmes données ?
   Avec `--local`, l'adresse du stockage va dans `.dvc/config.local`, qui n'est pas commité. C'est logique, notre dossier `%USERPROFILE%\dvc-stockage` n'existe que sur notre PC. Pour partager avec le groupe, il faudrait un stockage commun (S3, Google Drive, un serveur SSH…) ajouté sans `--local`, pour que la config parte dans Git.
3. Livrer un modèle, c'est trois choses (TP4). Lesquelles, et où sont-elles maintenant ?
   Le modèle, son contrat d'entrée (les variables et le seuil) et les versions exactes des bibliothèques. Maintenant tout est dans le run MLflow : le modèle, sa signature avec un exemple d'entrée, le seuil en paramètre et le `requirements.txt`. En plus, `data_md5` dit sur quelles données il a été entraîné.

## 7. Le rendu Git

- Lien de la pull request : …
- Le tag `tp5` existe sur GitHub : oui / non
- `git status` avant le commit : `mlflow.db`, `mlruns/`, `data/sensors.csv` ou `.dvc/cache` apparaissaient-ils ? non, ils sont tous ignorés (`.gitignore` pour `mlflow.db`, `mlruns/` et `data/*.csv`, `.dvc/.gitignore` pour le cache)

## 8. Ce qui reste flou

- On a choisi le seuil en regardant le jeu de test. On ne sait pas trop si c'est correct, ou s'il faudrait un jeu à part juste pour régler le seuil.
- Smart App Control bloque les versions trop récentes de certains paquets. À part figer des versions plus anciennes, on ne voit pas de solution propre.
