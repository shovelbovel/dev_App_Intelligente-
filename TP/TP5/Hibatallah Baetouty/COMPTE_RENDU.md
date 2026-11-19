# Compte rendu · TP5 : suivre les entraînements (MLflow) et versionner les données (DVC)

**Groupe :** 5IAD G1  ·  **Membres :** hibatallah baetouty  ·  **Date :** 18/11/2026 . temps : 12:00

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP5.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP5`)

Dernière ligne de `python -m pytest` après `pip install -r requirements.txt` et `pip install -e .` :

```
================== 5 failed, 27 passed, 2 warnings in 24.82s ==================
```

Quels tests échouent, et pourquoi ?

Les cinq tests de `tests/test_tracking.py` :

```
FAILED tests/test_tracking.py::test_training_creates_a_run
FAILED tests/test_tracking.py::test_run_records_metrics
FAILED tests/test_tracking.py::test_run_records_data_version
FAILED tests/test_tracking.py::test_run_stores_the_model
FAILED tests/test_tracking.py::test_options_change_the_run
```

Ils échouent tous pour la même raison : la fonction `log_run` de `maintai/tracking.py` n'était pas
encore écrite. C'était un `TODO` qui renvoyait une chaîne vide, donc aucun run n'était enregistré
dans MLflow. Les tests cherchaient un run, n'en trouvaient aucun, et s'arrêtaient sur le message
`aucun run MLflow : log_run n'a rien enregistré`. Le terminal affichait aussi l'avertissement
`Cannot retrieve experiment by name maintai` : l'expérience n'avait jamais été créée.

Les 27 autres tests passaient déjà, parce que le reste du projet (API, CLI, données, modèle) ne
dépend pas de MLflow.

Avant `pip install -e .`, où pointait le package `maintai` installé dans l'environnement ? Et après ?

Sur notre machine, l'environnement du TP4 n'était plus disponible : nous avons donc créé un nouvel
environnement dans `TP5/.venv`. Avant `pip install -e .`, le package `maintai` n'y était pas
installé du tout. Seul le fichier `pytest.ini`, avec sa ligne `pythonpath = .`, permettait aux
tests de trouver le code. Après `pip install -e .`, `pip show maintai` répond :

```
Name: maintai
Version: 0.3.0
Location: C:\Users\HP\Desktop\TP5\TP5\.venv\Lib\site-packages
Editable project location: C:\Users\HP\Desktop\TP5\TP5
```

La ligne importante est la dernière : le package ne contient pas une copie du code, il pointe vers
le dossier du TP5. Quand on réutilise l'environnement du TP4, c'est exactement le problème que
règle cette commande : `maintai` pointait encore vers le dossier du TP4, et on travaillait donc
sans le savoir sur l'ancien code. Le `pip install -e .` fait basculer ce pointeur vers TP5.

## 2. Sprint 1 : MLflow

Votre fonction `log_run` (`maintai/tracking.py`) :

```python
def log_run(params: dict, metrics: dict, model, X_example, data_path: Path) -> str:
    """Enregistre un entraînement : paramètres, version des données, métriques et modèle. Renvoie l'id du run."""
    # 1. L'expérience regroupe tous les runs du projet : elle est créée au premier appel.
    mlflow.set_experiment(EXPERIMENT)

    # 2. Le with ouvre un run et le ferme proprement, même si l'entraînement lève une erreur.
    with mlflow.start_run() as run:
        # 3a. Les réglages de l'entraînement (modèle, C, seuil, taille du train).
        mlflow.log_params(params)

        # 3b. L'empreinte des données : deux runs comparables doivent avoir le même data_md5.
        #     C'est la même empreinte que celle écrite par DVC dans data/sensors.csv.dvc.
        mlflow.log_param("data_md5", file_md5(data_path))

        # 3c. Les résultats mesurés sur le jeu de test, baseline comprise.
        mlflow.log_metrics(metrics)

        # 3d. Le modèle lui-même (scaler + classifieur). input_example fige le contrat d'entrée ;
        #     skops_trusted_types autorise la sérialisation des arbres pour --model forest.
        mlflow.sklearn.log_model(
            model,
            name="model",
            input_example=X_example,
            skops_trusted_types=TRUSTED_TYPES,
        )

        # 4. L'identifiant sert à retrouver le run (mlflow ui) et à recharger le modèle.
        return run.info.run_id
```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
======================= 32 passed, 4 warnings in 42.96s =======================
```

Vos runs (au moins quatre), relevés dans `mlflow ui` (mode « Model training ») :

| Commande | recall | precision | accuracy |
|---|---|---|---|
| `python -m maintai.train` | 0.750 | 0.622 | 0.904 |
| `python -m maintai.train --C 0.01` | 0.691 | 0.653 | 0.908 |
| `python -m maintai.train --threshold 0.2` | 0.838 | 0.543 | 0.882 |
| `python -m maintai.train --model forest` | 0.728 | 0.562 | 0.886 |
| `python -m maintai.train --threshold 0.15` (notre essai) | 0.875 | 0.500 | 0.864 |

Les cinq runs ont tourné sur la version v1 des données (`data_md5 = 73e0b7cb…`, 4000 relevés
d'entraînement) : ils sont donc comparables entre eux. La baseline, qui consiste à toujours prédire
« pas de panne », a un recall de 0.0 — elle ne détecte aucune panne. N'importe lequel de nos cinq
modèles fait mieux.

Notre essai consistait à descendre le seuil encore plus bas que 0.2, pour voir jusqu'où le recall
pouvait monter. Il monte bien, à 0.875, mais la precision tombe pile à 0.500 : une alerte sur deux
est une fausse alerte. Et son accuracy, 0.864, est exactement celle de la baseline — à force
d'alerter, le modèle se trompe aussi souvent qu'une machine qui ne prédirait jamais rien. C'est le
point où le gain en recall commence à coûter trop cher, et c'est pour cela que nous nous arrêtons à
0.2.

Quel run choisiriez-vous pour MaintAI, et pourquoi ? (Rappel : une panne manquée coûte plus cher qu'une fausse alerte.)

Le run `--threshold 0.2`, identifiant `c661c909`. Son recall est de 0.838 contre 0.750 pour le
réglage par défaut : il rattrape environ 9 pannes sur 100 que les autres laissent passer. En
échange, sa precision tombe à 0.543, donc un peu moins d'une alerte sur deux est une fausse alerte.

C'est le bon compromis ici. Une fausse alerte coûte un déplacement de technicien ; une panne
manquée coûte un arrêt de production. Tant que le premier coût reste très inférieur au second, il
faut privilégier le recall.

Le détail à remarquer : entre le run par défaut et celui-ci, **le modèle est exactement le même**.
Seul le seuil de décision change, 0.2 au lieu de 0.3. On n'a pas amélioré le modèle, on a déplacé
le curseur entre prudence et fausses alertes. C'est le réglage le plus facile à ajuster en
production, puisqu'il ne demande aucun réentraînement.

Nous avons aussi écarté `--model forest` : plus lourd, plus lent, et il ne fait pas mieux que la
régression logistique (recall 0.728 contre 0.750). Autant garder le modèle simple.

Dans `mlflow ui`, ouvrez le modèle d'un run. Quelle version de scikit-learn est indiquée dans son `requirements.txt` ? Quel problème du TP4 cela règle-t-il ?

Onglet « Artifacts », fichier `model/requirements.txt` :

```
mlflow==3.18.0
numpy==2.4.4
pandas==3.0.2
psutil==7.2.2
pyarrow==26.0.1
pytest==9.1.1
scikit-learn==1.8.0
scipy==1.18.1
skops==0.16.0
```

C'est **scikit-learn 1.8.0**.

Au TP4, le wheel contenait le code mais pas le modèle, et surtout il ne disait pas avec quelle
version de scikit-learn ce modèle avait été entraîné. Or un `model.joblib` chargé avec une autre
version peut déclencher un avertissement, se comporter différemment, ou refuser de se charger. Il
fallait noter la version à la main dans `model_info.json` et espérer que personne n'oublie de la
mettre à jour.

Avec MLflow, chaque run enregistre tout seul les versions exactes au moment de l'entraînement. On
peut reconstituer l'environnement d'un modèle des mois plus tard sans avoir rien noté.

Où MLflow enregistre-t-il les runs sur votre disque ? Ces fichiers vont-ils dans Git ? Pourquoi ?

À deux endroits, tous les deux dans `TP/TP5` :

- `mlflow.db` : une base SQLite qui contient les paramètres, les métriques et les tags de chaque run.
- `mlruns/` : les artefacts, c'est-à-dire les modèles eux-mêmes, leurs `requirements.txt` et leurs
  exemples d'entrée. Le chemin exact est `mlruns/1/`, où 1 est l'identifiant de l'expérience `maintai`.

Non, ils ne vont pas dans Git, et ils sont déjà listés dans `.gitignore`. Pour trois raisons :

1. Ce sont des fichiers binaires. Git ne sait pas en faire de diff, et chaque entraînement
   ajouterait une copie complète au dépôt, qui grossirait très vite.
2. Ils sont régénérables : le code et les données versionnées suffisent à les reproduire.
3. `mlflow.db` est réécrite à chaque run. Deux membres du groupe qui entraînent un modèle en même
   temps obtiendraient un conflit à chaque fois.

Git garde le code, qui se lit et se fusionne. Le reste a d'autres outils.

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

Les deux valeurs sont identiques : `73e0b7cb3c6f795c70c3ddf970b99c15`. Ce n'est pas un hasard — la
fonction `file_md5` de `maintai/tracking.py` calcule le MD5 du fichier exactement comme DVC.

C'est ce qui relie les deux outils. Devant un run MLflow, on lit son `data_md5`, on le cherche dans
l'historique Git des fichiers `.dvc`, et on sait précisément sur quelles données ce modèle a été
entraîné. Et dans l'autre sens : à partir d'une version des données, on retrouve tous les modèles
qui en sont issus. Sans cela, « le modèle de mardi » ne veut rien dire.

Pourquoi `data/sensors.csv` ne va pas dans Git, alors que `data/sensors.csv.dvc` y va ?

Parce qu'ils n'ont ni la même taille ni le même rôle.

`data/sensors.csv` fait 127 Ko en v1 et 203 Ko en v2 — et sur un vrai projet ce serait des
gigaoctets. Git conserve chaque version pour toujours : le dépôt deviendrait vite impossible à
cloner. Et comme c'est un fichier de données, un diff Git dessus n'apprend rien à personne.

`data/sensors.csv.dvc` fait quatre lignes. Il contient l'empreinte, la taille et le nom du fichier
réel. C'est une étiquette, et une étiquette se versionne très bien. Git garde l'étiquette, DVC garde
le contenu, dans son cache et dans le stockage distant.

On a donc dans Git l'historique complet des versions des données, sans les données elles-mêmes.

Après `python -m maintai.dataset --n 8000 --seed 7`, que dit `dvc status` ?

```
data\sensors.csv.dvc:
	changed outs:
		modified:           data\sensors.csv
```

DVC a recalculé l'empreinte du fichier et l'a trouvée différente de celle notée dans le `.dvc`. Il
ne regarde ni la date ni la taille, uniquement le contenu : si on régénérait exactement les mêmes
données, il ne dirait rien.

| Version | Commit Git (`git log --oneline`) | md5 (8 premiers caractères) | Nombre de lignes |
|---|---|---|---|
| v1 | `bc0f0a4 Donnees v1` | `73e0b7cb` | 5000 |
| v2 | `a14b446 Donnees v2` | `93fdeef2` | 8000 |

Revenez à la v1 (`git checkout <commit> -- data/sensors.csv.dvc`, puis `dvc checkout`). Combien de lignes contient `data/sensors.csv` ? Puis revenez à la v2.

**5000 lignes.**

Le détail intéressant est l'ordre des deux commandes. `git checkout bc0f0a4 -- data/sensors.csv.dvc`
ne restaure qu'un fichier texte de quatre lignes : à ce stade le CSV sur le disque contient toujours
8000 lignes, Git n'y a pas touché. C'est `dvc checkout` qui lit la nouvelle empreinte, va chercher
le fichier correspondant dans le cache et remplace le CSV :

```
M       data\sensors.csv
```

Ensuite `git checkout HEAD -- data/sensors.csv.dvc` puis `dvc checkout` nous ont ramenés à la v2, et
`python -c "import pandas as pd; print(len(pd.read_csv('data/sensors.csv')))"` a bien répondu 8000.

À retenir : Git déplace l'étiquette, DVC déplace les données. Oublier le `dvc checkout` est l'erreur
classique — on croit avoir changé de version alors que le CSV est resté le même.

Supprimez `data/sensors.csv` et le dossier `.dvc/cache`, puis lancez `dvc pull`. Que se passe-t-il ?

Après la suppression, `dvc status` dit :

```
data\sensors.csv.dvc:
	changed outs:
		not in cache:       data\sensors.csv
```

Le message a changé : ce n'est plus `modified` mais `not in cache`. DVC sait quel fichier il lui
manque, grâce au `.dvc` resté dans Git, mais il ne l'a plus ni sur le disque ni dans son cache local.

`dvc pull` va le rechercher dans le stockage :

```
A       data\sensors.csv
1 file fetched and 1 file added
```

Et le fichier contient de nouveau ses 8000 lignes. Rien n'a été perdu, parce que `dvc push` avait
déjà copié les données dans `C:\Users\HP\dvc-stockage`. Elles y sont rangées par empreinte :

```
C:\Users\HP\dvc-stockage\files\md5\73\e0b7cb3c6f795c70c3ddf970b99c15   (v1)
C:\Users\HP\dvc-stockage\files\md5\93\fdeef2cac1893c4f720c16457eea75   (v2)
```

Pas de noms de fichiers, pas de dossiers « v1 » et « v2 » : seulement le contenu, classé par son
empreinte. Deux fichiers identiques ne sont donc stockés qu'une seule fois.

C'est le scénario du nouveau collègue : il clone le dépôt Git — du code et des étiquettes, quelques
centaines de kilo-octets — lance `dvc pull`, et obtient exactement les données de l'équipe.

## 4. Relier modèle et données

Entraînez un modèle sur la v2. Dans `mlflow ui`, comparez ce run à celui de la v1 avec les mêmes réglages :

| Run | data_md5 (8 caractères) | n_train | recall | precision |
|---|---|---|---|---|
| v1 (`d6f8e2f1`) | `73e0b7cb` | 4000 | 0.750 | 0.622 |
| v2 (`28360bc2`) | `93fdeef2` | 6400 | 0.741 | 0.650 |

Peut-on dire que le modèle v2 est « meilleur » ? Pourquoi faut-il être prudent en comparant deux runs entraînés sur des données différentes ?

Non, on ne peut pas le dire. Les deux runs utilisent les mêmes réglages, mais tout le reste a bougé
en même temps.

D'abord, ils ne passent pas le même examen. Le run v1 est évalué sur 1000 relevés, le run v2 sur
1600 autres relevés. Comparer leurs notes revient à comparer deux élèves qui ont passé des épreuves
différentes.

Ensuite, deux choses ont changé d'un coup : la quantité de données, 4000 puis 6400 à
l'entraînement, et les données elles-mêmes, puisque `--seed 7` tire un autre échantillon, avec
12,8 % de pannes contre 13,6 %. Même si v2 était meilleur, on ne saurait pas laquelle des deux
causes en est responsable.

Enfin, les écarts sont minuscules : 0,009 de recall en moins, 0,028 de precision en plus. C'est de
l'ordre du bruit d'échantillonnage. Avec une autre graine aléatoire, les deux chiffres pourraient
très bien s'inverser.

La règle qu'on en tire : pour comparer deux modèles, on fixe les données et on ne fait varier que
les réglages. C'est précisément à cela que sert `data_md5` — en un coup d'œil dans MLflow, on voit
si deux runs sont comparables ou non.

## 5. Décision : l'ADR 004

Dans `docs/adr/004-choix-du-modele.md` : le modèle et le seuil retenus, à partir de votre tableau MLflow. Indiquez l'identifiant du run et le `data_md5` de la version des données utilisée.

Fait : voir `docs/adr/004-choix-du-modele.md`. En résumé, une régression logistique avec `C = 1.0`
et un seuil d'alerte à 0.2, run `c661c909a61249ad9b14b366410e4556`, entraînée sur les données
`73e0b7cb…` (version v1).

## 6. Questions de compréhension

1. Quelle différence entre Git, DVC et MLflow ? Que versionne chacun ?

   Les trois versionnent, mais pas la même chose.

   **Git** versionne le code : des fichiers texte, petits, qu'on lit, qu'on compare et qu'on
   fusionne. Il garde tout l'historique à l'intérieur du dépôt.

   **DVC** versionne les données : des fichiers lourds et binaires. Il range le contenu ailleurs —
   cache local et stockage distant — et ne met dans Git qu'une étiquette de quatre lignes contenant
   l'empreinte. Git garde donc l'historique des versions, sans leur poids.

   **MLflow** versionne les entraînements : pour chaque run, les réglages utilisés, les résultats
   obtenus, le modèle produit et les versions des bibliothèques. Il répond à la question « qu'est-ce
   qu'on a essayé, et qu'est-ce que ça a donné ? », ce que ni Git ni DVC ne savent faire.

   Les trois se complètent : le code (Git), les données (DVC) et les réglages (MLflow) sont ce qu'il
   faut réunir pour refaire un modèle à l'identique. Et c'est le `data_md5` qui fait le lien entre
   eux.

2. Pourquoi le stockage DVC est-il ajouté avec `--local` dans ce TP ? Que faudrait-il pour que tout le groupe partage les mêmes données ?

   Avec `--local`, l'adresse du stockage est écrite dans `.dvc/config.local`, qui n'est pas
   versionné, au lieu de `.dvc/config`, qui l'est. Dans ce TP le stockage est un simple dossier,
   `C:\Users\HP\dvc-stockage`. Ce chemin n'existe que sur notre machine : le mettre dans Git
   casserait le dépôt pour tous les autres. `--local` est donc exactement ce qu'il faut pour un
   stockage personnel.

   Pour partager les données à plusieurs, il faudrait un stockage que tout le monde peut atteindre :
   un bucket S3, un Google Drive partagé, un serveur SSH, ou un simple dossier réseau de l'école. On
   l'ajouterait cette fois sans `--local`, pour que l'adresse parte dans Git et que chacun la
   récupère au clone. Chaque membre configurerait ensuite ses identifiants de son côté — les
   identifiants, eux, restent toujours en local. Après quoi `dvc push` et `dvc pull` suffisent à
   garder tout le groupe sur les mêmes données.

3. Livrer un modèle, c'est trois choses (TP4). Lesquelles, et où sont-elles maintenant ?

   Le code, le modèle entraîné et le contrat d'entrée. Au TP4 on les gérait à la main ; ils sont
   maintenant tous les trois suivis automatiquement.

   | Quoi | Où c'était au TP4 | Où c'est maintenant |
   |---|---|---|
   | Le code | le wheel `maintai-0.2.0-py3-none-any.whl` | versionné dans Git, installé par `pip install -e .` |
   | Le modèle | `models/model.joblib`, copié à la main | artefact du run MLflow, avec ses versions de bibliothèques |
   | Le contrat d'entrée | `models/model_info.json` | `input_example` et la signature enregistrés dans le run |

   Il faut y ajouter une quatrième chose, qui est l'apport du TP5 : **les données d'entraînement**,
   versionnées par DVC et reliées au run par `data_md5`. Sans elles, on ne peut pas refaire le
   modèle, seulement le réutiliser.

## 7. Le rendu Git

- Lien de la pull request : …
- Le tag `tp5` existe sur GitHub : …
- `git status` avant le commit : `mlflow.db`, `mlruns/`, `data/sensors.csv` ou `.dvc/cache` apparaissaient-ils ? **non**

Aucun des quatre n'est jamais apparu dans `git status`, parce que `.gitignore` les couvre déjà :
`mlflow.db` et `mlruns/` y étaient dès le départ, `data/*.csv` aussi, et `.dvc/cache` est ignoré par
le `.gitignore` que `dvc init` écrit lui-même dans `.dvc/`. Nos quatre commits sont donc propres :

```
a14b446 Donnees v2
bc0f0a4 Donnees v1
c75146f DVC : init
d67da6d TP5 : projet MaintAI avec log_run (MLflow)
```

## 8. Ce qui reste flou

Quelques points que nous n'avons pas complètement assimilés :

- **La différence entre `dvc pull`, `dvc fetch` et `dvc checkout`.** Nous avons compris que
  `dvc checkout` travaille depuis le cache local et que `dvc pull` va chercher plus loin, dans le
  stockage. Nous l'avons d'ailleurs vérifié sans le vouloir : après avoir supprimé `.dvc/cache`, un
  `dvc checkout` vers la v1 a échoué avec `missing files`, et il a fallu un `dvc pull`. Mais la
  place exacte de `dvc fetch` dans tout ça nous échappe encore.

- **Comment choisir le seuil autrement qu'à la main.** Nous avons retenu 0.2 en comparant des
  chiffres, mais la vraie décision devrait venir du coût réel d'une fausse alerte et d'une panne
  manquée. Nous ne savons pas comment on passe de ces deux coûts à une valeur de seuil.

- **Le travail à plusieurs.** Si deux membres du groupe modifient les données chacun de leur côté et
  font `dvc add` puis `dvc push`, nous ne savons pas bien ce qui se passe au moment de fusionner les
  deux fichiers `.dvc` dans Git.

- **La suite de MLflow.** Nous avons vu les runs et les artefacts, mais pas le « Model Registry »
  aperçu dans l'interface. Nous ne savons pas encore comment on passe d'un run intéressant à un
  modèle réellement déployé en production.

## 9. Recherche par grille (grid search) : 25 entraînements

Jusqu'ici nous avions comparé cinq runs choisis un par un. Pour aller plus loin, nous avons balayé
une grille complète : toutes les combinaisons de deux hyperparamètres, soit 5 × 5 = **25
entraînements**.

Les 25 runs tournent sur la **version v1 des données** (`data_md5 = 73e0b7cb…`, 4000 relevés
d'entraînement, 1000 de test), la même que les cinq runs de la partie 2 et que la décision de
l'ADR 004. Ils sont donc tous comparables entre eux. Commande utilisée (PowerShell) :

```powershell
foreach ($C in 0.01, 0.1, 1.0, 10.0, 100.0) {
  foreach ($T in 0.15, 0.2, 0.25, 0.3, 0.4) {
    python -m maintai.train --C $C --threshold $T
  }
}
```

Chaque itération crée un run MLflow complet : les deux hyperparamètres, le `data_md5`, les trois
métriques et le modèle. Les 25 runs se comparent ensuite côte à côte dans `mlflow ui`.

### Les deux hyperparamètres ajustés

**`C` — la force de la régularisation de la régression logistique.**

C'est l'inverse de la régularisation : **plus `C` est petit, plus le modèle est bridé**. Un `C`
faible force les coefficients du modèle à rester proches de zéro, donc le modèle colle moins aux
détails des données d'entraînement — il est plus prudent, et il généralise souvent mieux quand les
données sont peu nombreuses ou bruitées. Un `C` grand lève le frein : le modèle est libre de suivre
les données de près, au risque de surapprendre.

Nous l'avons fait varier sur quatre ordres de grandeur, de 0.01 (très bridé) à 100 (quasiment
libre), en multipliant par 10 à chaque fois. C'est la façon habituelle de balayer ce paramètre : ce
qui compte est l'ordre de grandeur, pas la valeur exacte.

C'est un vrai hyperparamètre d'apprentissage : il agit **pendant** l'entraînement, et le changer
produit un modèle différent.

**`threshold` — le seuil d'alerte.**

Le modèle ne répond pas « panne » ou « pas de panne », il renvoie une probabilité entre 0 et 1.
Le seuil est la barre au-dessus de laquelle on déclenche une alerte. À 0.4 on n'alerte que si le
modèle est assez sûr ; à 0.15 on alerte au moindre doute.

Nous avons testé 0.15, 0.2, 0.25, 0.3 et 0.4, autour de la valeur par défaut du projet (0.3, lue
depuis `MAINTAI_THRESHOLD` dans `maintai/config.py`).

Attention, ce n'est **pas** un hyperparamètre d'apprentissage. Il s'applique *après* l'entraînement,
sur les probabilités déjà calculées : à `C` fixé, les cinq lignes de la grille utilisent exactement
le même modèle entraîné, seule la barre de décision change. C'est ce qui le rend si pratique en
production — on peut le régler sans réentraîner quoi que ce soit.

### Résultats des 25 runs

Recall (la part des pannes réelles que le modèle détecte) :

| `C` \ seuil | 0.15 | 0.20 | 0.25 | 0.30 | 0.40 |
|---|---|---|---|---|---|
| **0.01** | **0.919** | 0.838 | 0.787 | 0.691 | 0.559 |
| **0.1** | 0.897 | 0.846 | 0.809 | 0.750 | 0.654 |
| **1.0** | 0.875 | 0.838 | 0.794 | 0.750 | 0.684 |
| **10** | 0.875 | 0.838 | 0.794 | 0.750 | 0.684 |
| **100** | 0.875 | 0.838 | 0.794 | 0.750 | 0.684 |

Precision (la part des alertes qui correspondent à une vraie panne) :

| `C` \ seuil | 0.15 | 0.20 | 0.25 | 0.30 | 0.40 |
|---|---|---|---|---|---|
| **0.01** | 0.455 | 0.528 | 0.626 | 0.653 | **0.776** |
| **0.1** | 0.496 | 0.542 | 0.591 | 0.626 | 0.679 |
| **1.0** | 0.500 | 0.543 | 0.581 | 0.622 | 0.664 |
| **10** | 0.500 | 0.543 | 0.581 | 0.618 | 0.664 |
| **100** | 0.500 | 0.543 | 0.581 | 0.618 | 0.664 |

Accuracy :

| `C` \ seuil | 0.15 | 0.20 | 0.25 | 0.30 | 0.40 |
|---|---|---|---|---|---|
| **0.01** | 0.839 | 0.876 | 0.907 | 0.908 | **0.918** |
| **0.1** | 0.862 | 0.882 | 0.898 | 0.905 | 0.911 |
| **1.0** | 0.864 | 0.882 | 0.894 | 0.904 | 0.910 |
| **10** | 0.864 | 0.882 | 0.894 | 0.903 | 0.910 |
| **100** | 0.864 | 0.882 | 0.894 | 0.903 | 0.910 |

### Ce que la grille nous apprend

**1. Le seuil fait presque tout, `C` presque rien.** En parcourant une ligne, le recall passe de
0.92 à 0.56 — un écart énorme. En parcourant une colonne, il bouge de quelques centièmes. Le levier
utile sur ce problème est donc le seuil d'alerte, pas la régularisation. C'est rassurant pour
l'exploitation : le paramètre qui compte est justement celui qu'on peut changer sans réentraîner.

**2. `C` sature à partir de 1.0.** Les lignes `C = 1`, `C = 10` et `C = 100` sont identiques au
millième près. Au-delà de 1.0, la régularisation ne freine plus rien : le modèle a déjà trouvé ses
coefficients, l'augmenter encore ne change plus sa réponse. Inutile de tester `C = 1000`.

**3. Un `C` faible accentue l'effet du seuil.** La ligne `C = 0.01` est la plus étalée : meilleur
recall de toute la grille à seuil bas (0.919), mais aussi la plus mauvaise precision (0.455), et à
l'inverse la meilleure precision (0.776) et la meilleure accuracy (0.918) à seuil haut. Un modèle
bridé produit des probabilités plus resserrées autour de 0.5, donc déplacer le seuil fait basculer
beaucoup plus de cas d'un coup.

**4. Aucune combinaison n'est « la meilleure » dans l'absolu.** Les trois records appartiennent à
trois cases différentes :

| Critère | Meilleur run | Réglages | Le prix à payer |
|---|---|---|---|
| Recall | `82deb5dd` — 0.919 | `C=0.01`, seuil 0.15 | precision 0.455 : plus d'une alerte sur deux est fausse |
| Precision | `6bcc2e42` — 0.776 | `C=0.01`, seuil 0.40 | recall 0.559 : presque une panne sur deux passe inaperçue |
| Accuracy | `6bcc2e42` — 0.918 | `C=0.01`, seuil 0.40 | le même, et l'accuracy n'est pas le bon critère ici |

C'est au métier de trancher, pas à la grille. Elle montre les compromis possibles, elle ne choisit
pas à notre place.

**5. La grille confirme l'ADR 004, avec une nuance.** Notre décision était `C = 1.0`, seuil 0.2
(recall 0.838, precision 0.543). La grille montre que `C = 0.1` au même seuil fait très légèrement
mieux : recall 0.846 pour une precision identique (0.542). L'écart est de 0.008 sur le recall, soit
environ une panne de plus détectée sur 1000 relevés de test. C'est de l'ordre du bruit
d'échantillonnage, et cela ne justifie pas de modifier la décision — mais c'est une piste à vérifier
sur davantage de données.

**6. Une vérification au passage.** Quatre cases de la grille reprennent des réglages déjà testés
dans la partie 2 (`C=1.0` aux seuils 0.15, 0.2, 0.3, et `C=0.01` au seuil 0.3). Les chiffres sont
identiques au millième près, parce que `SEED = 42` est fixé. Nos entraînements sont donc bien
reproductibles — deux exécutions des mêmes réglages sur les mêmes données donnent le même modèle.

### Limites de cette grille

- **Un seul jeu de test.** Les 25 runs sont évalués sur les mêmes 1000 relevés. Les écarts de
  quelques millièmes entre deux cases voisines ne sont pas significatifs. Une validation croisée
  donnerait une idée de l'incertitude, ce que la grille seule ne fait pas.
- **Une seule famille de modèles.** Nous n'avons gardé que la régression logistique, parce que `C`
  n'existe pas pour une forêt aléatoire : inclure `--model forest` aurait cassé le produit cartésien.
  Une grille sur la forêt porterait sur d'autres hyperparamètres (`n_estimators`, `max_depth`).
- **Le seuil n'est pas optimisé proprement.** Le régler en regardant le jeu de test revient à s'en
  servir un peu comme d'un jeu d'entraînement. La méthode correcte serait de choisir le seuil sur un
  jeu de validation séparé, puis de mesurer une seule fois sur le test.

### Alors, quel est le modèle le plus performant ?

La question n'a de réponse qu'une fois le critère fixé. Le nôtre, posé dans l'ADR 004, est le
suivant : **obtenir le meilleur recall possible sans descendre sous une precision de 0.5**,
c'est-à-dire sans que la majorité des alertes soient fausses.

Sur ce critère, le meilleur run de la grille est la régression logistique avec **`C = 0.1` et un
seuil de 0.2** (run `394f90b6`) : recall 0.846, precision 0.542, accuracy 0.882. Les deux runs qui
font mieux en recall (0.919 et 0.897) tombent à 0.455 et 0.496 de precision : ils franchissent la
limite et noieraient l'équipe de maintenance sous les fausses alertes.

**Nous conservons pourtant le réglage de l'ADR 004** (`C = 1.0`, seuil 0.2, run `c661c909`), pour
une raison chiffrable. Le jeu de test contient 1000 relevés, dont 136 pannes réelles — on le lit
directement sur la baseline, dont l'accuracy de 0.864 donne la proportion de « pas de panne ». Un
recall de 0.846 contre 0.838, cela représente 115 pannes détectées contre 114 : **une seule panne
d'écart**, pour une precision identique au millième (0.542 contre 0.543).

Changer une décision documentée pour une panne d'écart sur un unique jeu de test serait précisément
l'erreur signalée dans les limites ci-dessus : prendre pour un progrès ce qui n'est que du bruit
d'échantillonnage. Les deux réglages sont équivalents en pratique, et `C = 1.0` est la valeur par
défaut de scikit-learn, donc la plus simple à justifier et à reprendre.

En résumé : **le modèle le plus performant est la régression logistique au seuil 0.2**, avec `C`
entre 0.1 et 1.0 — l'écart entre ces deux valeurs n'est pas mesurable sur nos données. Ce qui
distingue vraiment un bon réglage d'un mauvais, ici, c'est le seuil, pas la régularisation.
