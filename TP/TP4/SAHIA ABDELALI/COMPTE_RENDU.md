# Compte rendu · TP4 : MaintAI devient un package Python

**Groupe :** …  ·  **Membres :** …  ·  **Date :** 12/11/2026

---

## 1. Mise en place (dans `TP/TP4`, avec son propre `.venv`)

Dernière ligne de `python -m pytest` juste après `pip install -r requirements.txt` :

```
2 failed, 25 passed, 1 warning in 2.49s
```

Quels sont les deux tests qui échouent, et pourquoi ?

Les deux sont dans `tests/test_package.py` :

```
FAILED tests/test_package.py::test_installed_version_matches_the_code
FAILED tests/test_package.py::test_command_is_declared
```

Ces deux tests ne regardent pas le code, ils regardent les métadonnées d'installation
(`importlib.metadata`). Tant qu'on n'a pas fait `pip install -e .`, pip n'a rien enregistré :

```
importlib.metadata.PackageNotFoundError: No package metadata was found for maintai
```

et la commande `maintai-predict` n'est déclarée nulle part, donc le second test ne la trouve pas
dans la liste des `console_scripts`.

Les 25 autres passent quand même parce que `pytest.ini` contient `pythonpath = .`. La racine du
projet est donc sur `sys.path` et `import maintai` fonctionne sans installer le package. Avoir le
code sous la main et avoir un package installé sont deux choses différentes : c'est exactement ce
que ces deux tests vérifient.

> Remarque : si on a déjà lancé `python -m build`, le dossier `maintai.egg-info/` reste à la racine.
> Comme la racine est sur `sys.path`, `importlib.metadata` y lit la version et le point d'entrée, et
> les deux tests passent alors que le package n'est pas installé. Il faut supprimer
> `maintai.egg-info/` pour retrouver le vrai état de départ.

## 2. Sprint 1 : `pyproject.toml` et `pip install -e .`

Vos sections `dependencies` et `[project.scripts]` :

```toml
dependencies = [
    "pandas>=2.2",         # maintai/data.py, dataset.py, predict.py
    "numpy>=1.26",         # maintai/dataset.py
    "scikit-learn>=1.5",   # maintai/data.py, train.py
    "joblib>=1.4",         # maintai/predict.py, train.py (chargement du modèle)
    "httpx>=0.27",         # maintai/client.py
]

[project.scripts]
maintai-predict = "maintai.cli:main"
```

La liste n'est pas recopiée de `requirements.txt` : on a relevé ce que les modules de `maintai/`
importent vraiment, et rien d'autre.

Pourquoi `pytest` et `fastapi` ne sont-ils pas dans `dependencies` ?

Parce que `dependencies` répond à une seule question : de quoi le code a-t-il besoin pour tourner
chez celui qui l'installe ?

- `pytest` ne sert qu'à nous, pendant le développement. Quelqu'un qui veut juste une prédiction n'a
  aucune raison de le télécharger. Il est dans le groupe `dev`.
- `fastapi` ne sert que si on lance l'API. La commande en ligne fonctionne sans. Il est dans le
  groupe `api`, qu'on installe au besoin avec `pip install maintai[api]`.

Tout mettre dans `dependencies` obligerait à installer streamlit, fastapi et uvicorn pour une seule
prédiction dans un terminal. Les groupes optionnels permettent de choisir.

Sortie de `pip show maintai` (les quatre premières lignes) :

```
Name: maintai
Version: 0.2.0
Summary: Prédiction de panne machine à partir de relevés de capteurs : modèle, API et commande en ligne.
Home-page:
```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
27 passed, 1 warning in 2.39s
```

Placez-vous dans un autre dossier (`cd %TEMP%`) et lancez `maintai-predict 72 6 85 15000`, puis `python -c "import maintai; print(maintai.__file__)"`. Qu'affichent ces deux commandes ? Où Python trouve-t-il le code de `maintai` ?

```
C:\Users\alisa\AppData\Local\Temp> maintai-predict 72 6 85 15000
Probabilité de panne : 95 % (ALERTE)

C:\Users\alisa\AppData\Local\Temp> python -c "import maintai; print(maintai.__file__)"
C:\Users\alisa\Desktop\TP4\maintai-starter-tp4\maintai\__init__.py
```

Deux mécanismes différents, qu'il faut séparer :

- **La commande** est trouvée grâce au `PATH`. L'activation du venv ajoute `.venv\Scripts\`, où pip
  a créé `maintai-predict.exe`. Le dossier courant n'intervient pas.
- **Le code** n'est pas copié dans `site-packages`. `pip install -e .` y a déposé deux fichiers,
  `__editable__.maintai-0.2.0.pth` et `__editable___maintai_0_2_0_finder.py`. Le `.pth` est exécuté
  au démarrage de Python et installe un chercheur dont toute la logique tient dans une table :

```python
MAPPING = {'maintai': 'C:\\Users\\alisa\\Desktop\\TP4\\maintai-starter-tp4\\maintai'}
```

Donc Python lit le code **dans notre dossier de travail**, via un renvoi posé dans le venv. Le
chemin est absolu, ce qui explique que le dossier courant ne change rien.

Le modèle suit la même logique : `ROOT` est calculé dans `maintai/config.py` avec
`Path(__file__).resolve().parent.parent`, donc `models/` est cherché à côté du source et non dans le
dossier courant. C'est pour ça que la prédiction fonctionne depuis `%TEMP%` sans rien configurer.

Modifiez le message affiché par `maintai/cli.py`, puis relancez `maintai-predict` sans réinstaller. Le changement est-il visible ? Pourquoi ?

Oui, immédiatement, sans aucun `pip install` :

```
>>> MESSAGE MODIFIE - Risque de panne : 95 % (ALERTE)
```

C'est tout l'intérêt du `-e`. `site-packages` ne contient pas de copie du code, seulement le renvoi
vers notre dossier, donc Python relit nos fichiers `.py` à chaque exécution. Avec une installation
normale (`pip install .`), le code serait copié dans `site-packages` et il faudrait réinstaller pour
voir la modification.

Une nuance quand même : cela vaut pour le **code**, pas pour les **métadonnées**. Si on change
`[project.scripts]` ou `dependencies` dans `pyproject.toml`, il faut relancer `pip install -e .`,
parce que ces informations ont été enregistrées une fois pour toutes à l'installation.

## 3. Sprint 2 : construire et installer le wheel

Sortie de `dir dist` après `python -m build` :

```
 Directory of c:\Users\alisa\Desktop\TP4\maintai-starter-tp4\dist

11/12/2026  11:44 AM    <DIR>          .
11/12/2026  11:44 AM    <DIR>          ..
11/12/2026  11:44 AM            11,636 maintai-0.2.0-py3-none-any.whl
11/12/2026  11:44 AM            12,386 maintai-0.2.0.tar.gz
               2 File(s)         24,022 bytes
```

Contenu du wheel (`tar -tf dist\maintai-0.2.0-py3-none-any.whl`). Le modèle, les tests et `ui/` y sont-ils ? Pourquoi ?

```
maintai/__init__.py
maintai/cli.py
maintai/client.py
maintai/config.py
maintai/data.py
maintai/dataset.py
maintai/predict.py
maintai/train.py
maintai/api/__init__.py
maintai/api/main.py
maintai/api/schemas.py
maintai/api/security.py
maintai-0.2.0.dist-info/METADATA
maintai-0.2.0.dist-info/WHEEL
maintai-0.2.0.dist-info/entry_points.txt
maintai-0.2.0.dist-info/top_level.txt
maintai-0.2.0.dist-info/RECORD
```

Non : ni le modèle, ni `models/`, ni `data/sensors.csv`, ni `tests/`, ni `ui/`, ni `web/`. Le wheel
contient 12 fichiers `.py` et ses métadonnées, pour 11 ko.

C'est `pyproject.toml` qui décide, avec `[tool.setuptools.packages.find] include = ["maintai*"]` :
seul le dossier `maintai/` entre dans le paquet. Tout le reste est à côté, pas dedans.

Et c'est voulu. Un paquet transporte du code, pas des données. Les tests ne servent à personne après
l'installation. `ui/` et `web/` sont des applications qui utilisent le package, pas des morceaux du
package. Quant au modèle, il a sa propre vie : il se réentraîne régulièrement, et on ne veut pas
publier une nouvelle version du paquet à chaque réentraînement. Ces deux choses se versionnent
séparément.

Dans un environnement neuf (`%TEMP%\essai`), installez le wheel et lancez `maintai-predict` :

| Étape | Ce qui s'affiche |
|---|---|
| sans `MAINTAI_MODELS_DIR` | `Modèle introuvable : C:\Users\alisa\AppData\Local\Temp\essai\.venv\Lib\site-packages\models\model.joblib` puis `Entraînez-le (python -m maintai.train) ou indiquez son dossier dans MAINTAI_MODELS_DIR.` (code de sortie 1) |
| avec `MAINTAI_MODELS_DIR` vers vos `models` | `InconsistentVersionWarning: Trying to unpickle estimator StandardScaler from version 1.8.0 when using version 1.9.1. This might lead to breaking code or invalid results. Use at your own risk.` (répété pour `StandardScaler`, `LogisticRegression` et `Pipeline`), **puis** `Probabilité de panne : 95 % (ALERTE)` (code de sortie 0) |
| après `pip install scikit-learn==1.8.0` | `Probabilité de panne : 95 % (ALERTE)`, sans aucun avertissement (code de sortie 0) |

Premier message : le wheel contient le code, pas le modèle. Le chemin cherché est
`site-packages\models\model.joblib`, parce que `ROOT` est calculé depuis l'emplacement du source, et
ce dossier n'existe pas. `MAINTAI_MODELS_DIR` ne répare rien dans le paquet, il redirige simplement
`models_dir` vers notre dossier de projet.

D'où vient l'avertissement `InconsistentVersionWarning` ? Quelle ligne de `models/model_info.json` permet de le comprendre ?

La ligne est :

```json
"sklearn_version": "1.8.0"
```

Le modèle a été entraîné avec scikit-learn 1.8.0, mais `pip install` a installé **1.9.1** dans
l'environnement neuf.

Un `.joblib` est un *pickle* : il ne contient pas le code des estimateurs, seulement des références
aux classes de scikit-learn, les valeurs apprises, et la version qui l'a écrit. Au chargement,
sklearn compare sa propre version à celle inscrite et avertit si elles diffèrent. Les trois objets
de la pipeline sont cités (`StandardScaler`, `LogisticRegression`, `Pipeline`) parce que chacun
porte sa propre marque de version.

Pourquoi 1.9.1 et pas 1.8.0 ? À cause du `>=` de notre `pyproject.toml` : `scikit-learn>=1.5`
autorise toute version plus récente, et pip prend toujours la plus récente disponible. Le collègue
qui n'installe que le wheel n'a pas notre `requirements.txt`, donc il n'a pas nos versions figées.

Le point important : **c'est un avertissement, pas une erreur**. La prédiction a quand même répondu
95 %. C'est justement ce qui rend le problème dangereux en production : si la structure interne d'un
estimateur avait changé entre les deux versions, on aurait obtenu un résultat faux sans rien
remarquer, au lieu d'un plantage. D'où le « Use at your own risk ».

## 4. Questions de compréhension

1. **Quelle différence entre `requirements.txt` et la liste `dependencies` de `pyproject.toml` ?**

   `requirements.txt` fige les versions exactes (`==`) de notre environnement de travail, outils
   inclus (`pytest`, `build`). Il sert à **reproduire** : retrouver précisément les versions avec
   lesquelles le modèle a été entraîné.

   `dependencies` dans `pyproject.toml` décrit ce avec quoi le package est **compatible**, avec des
   planchers souples (`>=`). C'est une bibliothèque : elle doit pouvoir s'installer à côté d'autres
   paquets sans imposer ses versions à tout le monde.

   On a vu la différence en vrai : le wheel installé seul a pris scikit-learn 1.9.1 et sorti
   l'avertissement, précisément parce que `>=` laisse pip monter en version.

2. **Quelle différence entre `pip install -e .` et `pip install dist\maintai-0.2.0-py3-none-any.whl` ?**

   Avec `-e .`, rien n'est copié : un renvoi dans `site-packages` pointe vers notre dossier. On
   modifie un `.py`, l'effet est immédiat. C'est le mode de développement.

   Avec le wheel, le code est **copié** dans `site-packages`. Le package devient indépendant de
   notre dossier (on pourrait le supprimer), mais modifier le source n'a plus aucun effet tant qu'on
   n'a pas reconstruit et réinstallé. C'est le mode de livraison.

   La vérification est directe, avec `maintai.__file__` :

   ```
   -e .    → C:\Users\alisa\Desktop\TP4\maintai-starter-tp4\maintai\__init__.py
   wheel   → C:\Users\alisa\AppData\Local\Temp\essai\.venv\Lib\site-packages\maintai\__init__.py
   ```

3. **Qu'est-ce qu'un « point d'entrée » (`[project.scripts]`) ? Où pip crée-t-il le fichier `maintai-predict.exe` ?**

   C'est une ligne `nom-de-commande = "module:fonction"`. À l'installation, pip la lit et fabrique
   un petit exécutable qui importe le module et appelle la fonction. Chez nous,
   `maintai-predict = "maintai.cli:main"` appelle `main()` de `maintai/cli.py`.

   pip le crée dans le dossier `Scripts` du venv :

   ```
   .venv\Scripts\maintai-predict.exe
   ```

   (sur Linux et macOS, ce serait `.venv/bin/maintai-predict`). Comme ce dossier est dans le `PATH`
   après activation, la commande marche depuis n'importe où, sans avoir à taper `python -m`. On
   retrouve la même déclaration dans le wheel, dans `maintai-0.2.0.dist-info/entry_points.txt` :

   ```
   [console_scripts]
   maintai-predict = maintai.cli:main
   ```

## 5. Le rendu Git

- Lien de la pull request : …
- Le tag `tp4` existe sur GitHub : oui / non
- `git status` avant le commit : `dist/`, `build/` ou `maintai.egg-info/` apparaissaient-ils ? **non**

Le `.gitignore` fourni les couvre déjà :

```
dist/
build/
*.egg-info/
models/
```

C'est logique : ce sont des fichiers *produits*. On peut les régénérer à tout moment avec
`python -m build`, et un wheel committé à chaque modification polluerait l'historique. On versionne
la recette, pas le gâteau.

## 6. Ce qui reste flou

**Un problème d'environnement rencontré en route** (pas lié au TP, mais il nous a coûté du temps) :
sur cette machine, la politique Application Control de Windows bloque les DLL de certains paquets
très récents.

- `pyarrow 26.0.1`, installé comme dépendance de streamlit, était bloqué. Conséquence inattendue :
  scikit-learn fait un `import pyarrow` optionnel protégé par `except ModuleNotFoundError`, qui ne
  rattrape pas l'`ImportError` d'une DLL bloquée. Résultat : plus aucun `import sklearn` possible, et
  l'erreur remontait dans `maintai-predict`, très loin de sa cause. Réglé avec `pyarrow==18.1.0`.
- `pandas 3.1.1`, dans l'environnement neuf `%TEMP%\essai`, était bloqué de la même façon. Réglé
  avec `pandas==3.0.2`.

Les versions un peu plus anciennes passent, les toutes récentes non. La leçon qu'on en retient : un
paquet « installé » n'est pas forcément utilisable, et un plantage peut venir d'une dépendance
*optionnelle* d'une dépendance.

**Les questions qu'on se pose encore :**

- Comment livre-t-on le modèle à côté du paquet, dans la vraie vie ? Un deuxième paquet de données ?
  Un téléchargement au premier lancement ? Un registre de modèles ?
- Vu que l'avertissement de version n'empêche pas une prédiction peut-être fausse, ne faudrait-il
  pas carrément refuser de charger un modèle dont `sklearn_version` ne correspond pas ? Le
  `model_info.json` contient déjà l'information, on pourrait la vérifier dans `Predictor.load`.
- Où placer la limite entre `>=` et `==` ? Notre paquet dépend d'un modèle entraîné avec une version
  précise, ce qui pousse à figer, mais figer dans une bibliothèque crée des conflits chez
  l'utilisateur.
