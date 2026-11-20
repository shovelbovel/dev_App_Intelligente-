# Compte rendu · TP5 : suivre les entraînements (MLflow) et versionner les données (DVC)

**Groupe :** Iktache Chouaib (seul)  ·  **Membres :** Iktache Chouaib  ·  **Date :** 19/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP5.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP5`)

Dernière ligne de `python -m pytest` après `pip install -r requirements.txt` et `pip install -e .` :

```
5 failed, 27 passed, 2 warnings in 10.53s
```

Quels tests échouent, et pourquoi ?

Les 5 tests de `tests/test_tracking.py` (`test_training_creates_a_run`, `test_run_records_metrics`,
`test_run_records_data_version`, `test_run_stores_the_model`, `test_options_change_the_run`).
Ils cherchent le dernier run MLflow de l'expérience `maintai`, mais `log_run` n'était pas encore écrite :
elle renvoyait `""` sans rien enregistrer (« aucun run MLflow : log_run n'a rien enregistré »).
Les 27 autres tests (données, modèle, API, package) passent : le code du TP4 fonctionne toujours.

Avant `pip install -e .`, où pointait le package `maintai` installé dans l'environnement ? Et après ?

Avant, le package `maintai` de l'environnement était celui du TP4 (installé avec `pip install -e .` dans `TP\TP4`) :
`import maintai` aurait chargé le code du TP4, sans `tracking.py`. Après `pip install -e .` dans `TP\TP5`,
il pointe vers `TP5\maintai\` (« Editable project location : …\TP5\TP5 », version 0.3.0).

## 2. Sprint 1 : MLflow

Votre fonction `log_run` (`maintai/tracking.py`) :

```python
def log_run(params: dict, metrics: dict, model, X_example, data_path: Path) -> str:
    """Enregistre un entraînement : paramètres, version des données, métriques et modèle. Renvoie l'id du run."""
    mlflow.set_experiment(EXPERIMENT)
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
32 passed, 4 warnings in 25.64s
```

Vos runs (au moins quatre), relevés dans `mlflow ui` (mode « Model training ») :

| Commande | recall | precision | accuracy |
|---|---|---|---|
| `python -m maintai.train` | 0.750 | 0.622 | 0.904 |
| `python -m maintai.train --C 0.01` | 0.691 | 0.653 | 0.908 |
| `python -m maintai.train --threshold 0.2` | **0.838** | 0.543 | 0.882 |
| `python -m maintai.train --model forest` | 0.728 | 0.562 | 0.886 |
| `python -m maintai.train --model forest --threshold 0.2` | 0.831 | 0.479 | 0.854 |

Tous les runs : données v1 (`data_md5` = `73e0b7cb…`, 4000 lignes d'entraînement, 1000 de test). Seuil par défaut : 0.3. Baseline : recall 0.0.

Quel run choisiriez-vous pour MaintAI, et pourquoi ? (Rappel : une panne manquée coûte plus cher qu'une fausse alerte.)

La régression logistique avec `C = 1.0` et le seuil 0.2 (run `3747245dab5e46288151105f3e8894fd`).
Une panne manquée coûte plus cher qu'une fausse alerte : on maximise donc le **recall**. Ce run a le meilleur recall (0.838,
soit environ 84 % des pannes détectées contre 75 % au seuil 0.3). En échange, la precision baisse (0.543 : environ une alerte
sur deux est fausse), ce qu'on accepte.
La forêt aléatoire n'est pas meilleure : au seuil 0.3 elle fait moins bien que la régression logistique sur le recall (0.728 contre 0.750)
et sur la precision ; au seuil 0.2 elle a un recall voisin (0.831) mais une precision plus faible (0.479). Elle est aussi plus lourde
et moins lisible. Baisser `C` à 0.01 (régularisation forte) fait perdre du recall (0.691) : à écarter.

Dans `mlflow ui`, ouvrez le modèle d'un run. Quelle version de scikit-learn est indiquée dans son `requirements.txt` ? Quel problème du TP4 cela règle-t-il ?

`scikit-learn==1.8.0` (avec `numpy==2.4.4`, `pandas==3.0.2`, `skops==0.16.0`, `mlflow==3.18.0`).
Au TP4, le fichier `model.joblib` ne disait pas avec quelle version de scikit-learn il avait été entraîné : le recharger
avec une autre version pouvait échouer ou donner des avertissements/résultats différents. Désormais chaque modèle
est enregistré avec les versions exactes de ses bibliothèques : on peut recréer le bon environnement pour le recharger.

Où MLflow enregistre-t-il les runs sur votre disque ? Ces fichiers vont-ils dans Git ? Pourquoi ?

Dans `TP\TP5` : la base SQLite `mlflow.db` (paramètres, métriques, tags des runs) et le dossier `mlruns/`
(les artefacts : `mlruns/1/models/m-…/artifacts/` contient le modèle `model.skops`, son `MLmodel` et son `requirements.txt`).
Ils ne vont pas dans Git : ils sont dans le `.gitignore`. Ce sont des fichiers générés, binaires, qui grossissent à chaque
entraînement et changent tout le temps ; ils provoqueraient des conflits entre membres du groupe. Git garde le code
qui permet de les reproduire ; pour partager les runs en équipe, on utiliserait un serveur MLflow commun.

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

Ce sont exactement les mêmes : `73e0b7cb3c6f795c70c3ddf970b99c15`. `file_md5()` de `tracking.py` calcule le même md5 que DVC.
C'est ce qui relie un run MLflow à une version des données : à partir du `data_md5` d'un run, on retrouve le commit
du reçu `.dvc` correspondant, donc les données exactes avec lesquelles le modèle a été entraîné.

Pourquoi `data/sensors.csv` ne va pas dans Git, alors que `data/sensors.csv.dvc` y va ?

Un fichier de données peut être gros (ici 127 Ko, en vrai 100 Mo ou plus) : Git le gère mal et garderait chaque version
pour toujours dans l'historique. DVC garde le fichier hors de Git (cache, puis stockage) et ne met dans Git que le reçu
`.dvc` : quelques lignes (md5 + taille), qui suffisent à savoir quelle version des données va avec quel commit.
`data/*.csv` est d'ailleurs dans le `.gitignore`.

Après `python -m maintai.dataset --n 8000 --seed 7`, que dit `dvc status` ?

```
data\sensors.csv.dvc:
	changed outs:
		modified:           data\sensors.csv
```

| Version | Commit Git (`git log --oneline`) | md5 (8 premiers caractères) | Nombre de lignes |
|---|---|---|---|
| v1 | `d2e89bc` Données v1 | `73e0b7cb` | 5000 |
| v2 | `cdbc10f` Données v2 | `93fdeef2` | 8000 |

Revenez à la v1 (`git checkout <commit> -- data/sensors.csv.dvc`, puis `dvc checkout`). Combien de lignes contient `data/sensors.csv` ? Puis revenez à la v2.

Après `git checkout d2e89bc -- data/sensors.csv.dvc` puis `dvc checkout` : **5000 lignes** (md5 `73e0b7cb`).
Git remet l'ancien reçu, DVC ramène le fichier qui lui correspond depuis le cache. `git status` montre alors
`data/sensors.csv.dvc` modifié (c'est l'ancien reçu) : on ne le commite pas.
Retour à la v2 avec `git checkout HEAD -- data/sensors.csv.dvc` puis `dvc checkout` : **8000 lignes** (md5 `93fdeef2`), `git status` propre.

Supprimez `data/sensors.csv` et le dossier `.dvc/cache`, puis lancez `dvc pull`. Que se passe-t-il ?

```
A       data\sensors.csv
1 file fetched and 1 file added
```

DVC lit le reçu `.dvc`, va chercher le fichier correspondant dans le stockage (`%USERPROFILE%\dvc-stockage`), le remet
dans le cache puis dans `data/` (`dvc pull` = `dvc fetch` + `dvc checkout`). On retrouve la v2 complète :
8000 lignes, md5 `93fdeef2`. C'est ce que ferait un coéquipier qui vient de cloner le dépôt sans les données.

## 4. Relier modèle et données

Entraînez un modèle sur la v2. Dans `mlflow ui`, comparez ce run à celui de la v1 avec les mêmes réglages :

Mêmes réglages pour les deux runs : `python -m maintai.train` (régression logistique, `C = 1.0`, seuil 0.3).

| Run | data_md5 (8 caractères) | n_train | recall | precision |
|---|---|---|---|---|
| v1 (`1170b800…`) | `73e0b7cb` | 4000 | 0.750 | 0.622 |
| v2 (`8201d9c7…`) | `93fdeef2` | 6400 | 0.741 | 0.650 |

Peut-on dire que le modèle v2 est « meilleur » ? Pourquoi faut-il être prudent en comparant deux runs entraînés sur des données différentes ?

Non. Le run v2 a un recall un peu plus bas (0.741 contre 0.750) et une precision un peu plus haute (0.650 contre 0.622) :
les écarts sont faibles, et surtout les deux runs ne sont **pas évalués sur le même jeu de test**. Le test du v1 contient
1000 lignes tirées des données v1, celui du v2 1600 lignes tirées des données v2 (autre graine, autre taux de panne : 12,8 %).
Les métriques mesurent donc à la fois le modèle et la difficulté de son jeu de test ; l'écart peut venir des données
et du hasard du découpage, pas du modèle. Pour comparer honnêtement, il faudrait évaluer les deux modèles sur un même
jeu de test fixe (ou faire une validation croisée et regarder la dispersion). C'est justement pour ça que chaque run
garde son `data_md5` : on sait toujours sur quelles données une métrique a été obtenue.

## 4 bis. Grid search (ajout)

Au lieu d'essayer les réglages un par un, `maintai/grid_search.py` teste **25 combinaisons** de la régression logistique :
5 valeurs de `C` (0.01, 0.1, 1, 10, 100) × 5 seuils (0.1, 0.2, 0.3, 0.4, 0.5).

```
python -m maintai.grid_search                    # --min-precision 0.5 par défaut
```

Méthode :
- **Validation croisée à 5 plis sur les données d'entraînement uniquement.** Si l'on choisissait la combinaison
  d'après le jeu de test, on choisirait « sur le test » et son score serait trop optimiste. Le test ne sert qu'une fois,
  à la fin, pour mesurer la combinaison retenue.
- Le seuil ne change pas le modèle : pour chaque pli, on entraîne une fois par `C`, puis on évalue les 5 seuils.
- **Règle de choix** : le meilleur recall moyen parmi les combinaisons dont la precision moyenne est d'au moins 0.5
  (au plus une fausse alerte par vraie alerte). Sans cette contrainte, le seuil le plus bas gagnerait toujours :
  alerter sur tout donne un recall de 1.
- Dans MLflow : un run parent `grid-search` (meilleure combinaison, métriques sur le test, modèle) et ses
  25 runs enfants (`cv_recall`, `cv_recall_std`, `cv_precision`), visibles en dépliant le run parent dans `mlflow ui`.

Données : v2 (`data_md5` = `93fdeef2…`, 6400 lignes d'entraînement). Run parent : `d56aac696dfc48408d6fb2b85219b927`.

| C \ seuil | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 |
|---|---|---|---|---|---|
| 0.01 | 0.956 / *0.374* | **0.831 / 0.550** | 0.681 / 0.694 | 0.561 / 0.780 | 0.446 / 0.867 |
| 0.1 | 0.916 / *0.436* | 0.821 / 0.556 | 0.735 / 0.657 | 0.637 / 0.733 | 0.565 / 0.777 |
| 1 | 0.906 / *0.453* | 0.815 / 0.560 | 0.740 / 0.651 | 0.650 / 0.717 | 0.583 / 0.764 |
| 10 | 0.905 / *0.454* | 0.815 / 0.560 | 0.740 / 0.650 | 0.650 / 0.717 | 0.584 / 0.763 |
| 100 | 0.905 / *0.456* | 0.815 / 0.560 | 0.740 / 0.650 | 0.650 / 0.716 | 0.584 / 0.762 |

Chaque case : recall moyen / precision moyenne en validation croisée. *En italique* : precision < 0.5, combinaison écartée.
Écart-type du recall entre les plis : de 0.015 à 0.040.

Meilleure combinaison : `C = 0.01`, seuil 0.2 (cv : recall 0.831 ± 0.016, precision 0.550).
Sur le jeu de test, mesurée une seule fois : **recall 0.829, precision 0.547, accuracy 0.890**, proche de la validation croisée,
donc pas de sur-ajustement au choix des réglages.

Ce qu'on en retient :
- **Le seuil compte beaucoup plus que `C`.** À seuil égal, le recall ne varie que de 0.815 à 0.831 selon `C`, un écart du
  même ordre que l'écart-type entre plis (environ 0.02) : la différence entre `C = 0.01` et `C = 1` n'est pas significative.
  Entre les seuils 0.2 et 0.3, le recall perd environ 0.08 à 0.15.
- Au-delà de `C = 1`, les résultats ne bougent presque plus : la régularisation n'a alors plus d'effet.
- Le grid search **confirme le seuil 0.2** retenu dans l'ADR 004. C'est le seul qui garde une precision ≥ 0.5 tout en
  dépassant 0.8 de recall. Le seuil 0.1 détecte plus de pannes (≈ 0.9), mais avec plus d'une fausse alerte sur deux.
- Attention : ce grid search est fait sur la v2, alors que les runs de la partie 2 étaient sur la v1. Les chiffres ne se comparent
  pas directement (partie 4).

## 5. Décision : l'ADR 004

Dans `docs/adr/004-choix-du-modele.md` : le modèle et le seuil retenus, à partir de votre tableau MLflow. Indiquez l'identifiant du run et le `data_md5` de la version des données utilisée.

## 6. Questions de compréhension

1. Quelle différence entre Git, DVC et MLflow ? Que versionne chacun ?
   **Git** versionne le code (et les petits fichiers texte : `requirements.txt`, `pyproject.toml`, les reçus `.dvc`).
   **DVC** versionne les fichiers de données : le fichier lui-même va dans un cache puis un stockage, et Git ne garde qu'un reçu
   (md5 + taille). **MLflow** garde chaque entraînement : paramètres, `data_md5`, métriques, le modèle et les versions exactes
   de ses bibliothèques. Le `data_md5` d'un run est égal au md5 du reçu `.dvc` : c'est ce qui relie un modèle à ses données.
2. Pourquoi le stockage DVC est-il ajouté avec `--local` dans ce TP ? Que faudrait-il pour que tout le groupe partage les mêmes données ?
   Le stockage est un dossier de **mon** PC (`%USERPROFILE%\dvc-stockage`) : son chemin n'a pas de sens chez les autres.
   `--local` l'écrit dans `.dvc/config.local`, ignoré par Git, au lieu de `.dvc/config` qui est commité.
   Pour partager les données, il faudrait un stockage accessible à tout le groupe (S3, Google Drive, un serveur SSH,
   Azure…), déclaré sans `--local` dans `.dvc/config` et commité : chacun ferait alors `dvc pull`.
3. Livrer un modèle, c'est trois choses (TP4). Lesquelles, et où sont-elles maintenant ?
   Le **code** : dans Git (et le wheel du TP4). Les **données** : dans DVC (le reçu `data/sensors.csv.dvc` dans Git,
   le fichier dans le stockage). Le **modèle** : dans MLflow, un run identifié par son `run_id`, avec ses **versions exactes**
   dans le `requirements.txt` du modèle.

## 7. Le rendu Git

- Lien de la pull request :[https://github.com/shovelbovel/dev_App_Intelligente-.git]
- Le tag `tp5` existe sur GitHub : oui / non
- `git status` avant le commit : `mlflow.db`, `mlruns/`, `data/sensors.csv` ou `.dvc/cache` 

## 8. Ce qui reste flou

…
