# Compte rendu · TP4 : MaintAI devient un package Python

**Groupe :** …  ·  **Membres :** …  ·  **Date :** 12/11/2026 12:15

## 1. Mise en place (dans `TP/TP4`, avec son propre `.venv`)

Dernière ligne de `python -m pytest` juste après `pip install -r requirements.txt` :

```text
=================== 2 failed, 25 passed, 1 warning in 2.97s ===================
```

Les deux tests qui échouent sont :

- `tests/test_ui.py::test_ui_shows_the_data` : la métrique attendue n'est pas
  trouvée dans l'application Streamlit (`at.metric` est vide ou ne contient pas
  la valeur attendue).
- `tests/test_ui.py::test_ui_shows_the_prediction` : après le clic sur le
  bouton, la métrique de prédiction attendue n'est pas disponible, ce qui
  provoque un `IndexError`.

Ces échecs concernent le rendu/exécution de l'interface Streamlit. Les tests
API, CLI, client, données, entraînement et packaging passent.

## 2. Sprint 1 : `pyproject.toml` et `pip install -e .`

Sections `dependencies` et `[project.scripts]` :

```toml
dependencies = [
    "numpy>=2.0",
    "pandas>=2.2",
    "scikit-learn>=1.5",
    "joblib>=1.4",
]

[project.scripts]
maintai-predict = "maintai.cli:main"
```

`pytest` et `fastapi` ne sont pas dans les dépendances obligatoires car ils ne
sont pas nécessaires pour utiliser le coeur du package et sa commande CLI.
Ils sont déclarés dans des dépendances optionnelles : `dev` pour les tests et
`api` pour l'API FastAPI.

Sortie de `pip show maintai` (les quatre premières lignes) :

```text
Name: maintai
Version: 0.2.0
Summary: Prédiction de panne à partir de relevés de capteurs
Home-page:
```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```text
=================== 2 failed, 25 passed, 1 warning in 2.97s ===================
```

Depuis `%TEMP%`, la commande de prédiction affiche :

```text
Probabilité de panne : 95 % (ALERTE)
```

La commande `python -c "import maintai; print(maintai.__file__)"` affiche :

```text
C:\Users\the-r\devep deploi\TP4\maintai-starter-tp4\maintai\__init__.py
```

Python trouve donc le code dans le dossier source `maintai\` du projet, grâce à
l'installation éditable (`pip install -e .`).

Après modification de `maintai/cli.py`, le changement est visible sans
réinstaller. En mode editable, l'installation pointe vers le répertoire source
au lieu d'en copier une version figée dans `site-packages`.

## 3. Sprint 2 : construire et installer le wheel

Sortie de `dir dist` après `python -m build` :

```text
maintai-0.2.0-py3-none-any.whl
maintai-0.2.0.tar.gz
```

Le wheel contient notamment :

```text
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

Le modèle, les tests et `ui/` ne sont pas dans le wheel. La configuration
`[tool.setuptools.packages.find]` inclut uniquement les packages correspondant
à `maintai*`. Le modèle est donc un artefact externe, et les tests/UI ne font
pas partie du package distribué.

Dans un environnement neuf (`%TEMP%\essai`) :

| Étape | Ce qui s'affiche |
|---|---|
| sans `MAINTAI_MODELS_DIR` | `Modèle introuvable : ...\site-packages\models\model.joblib`, puis un message indiquant d'entraîner le modèle ou de renseigner `MAINTAI_MODELS_DIR` ; code retour 1 |
| avec `MAINTAI_MODELS_DIR` vers `models` | `Probabilité de panne : 95 % (ALERTE)` |
| après `pip install scikit-learn==1.8.0` | `Probabilité de panne : 95 % (ALERTE)` ; la version d'exécution correspond à celle du modèle |

L'avertissement `InconsistentVersionWarning` apparaît lorsque le modèle
scikit-learn sérialisé a été entraîné avec une version différente de celle
utilisée au chargement. La ligne concernée dans `models/model_info.json` est :

```json
"sklearn_version": "1.8.0"
```

## 4. Questions de compréhension

1. `requirements.txt` décrit l'environnement complet de développement et
   d'exécution du projet, avec des versions épinglées : API, UI, tests,
   packaging et dépendances ML. La liste `dependencies` de `pyproject.toml`
   décrit uniquement les dépendances nécessaires au package installé et utilise
   des contraintes de version minimales. Les extras (`api`, `ui`, `dev`)
   ajoutent les fonctionnalités facultatives.

2. `pip install -e .` installe le package en mode éditable : les imports
   utilisent directement les fichiers source et les modifications sont
   immédiatement visibles. `pip install dist\maintai-0.2.0-py3-none-any.whl`
   installe une archive construite, donc une copie figée du code du package.

3. Un point d'entrée associe une commande shell à une fonction Python. Ici,
   `maintai-predict = "maintai.cli:main"` demande à pip de créer la commande
   `maintai-predict.exe` dans le dossier `Scripts` de l'environnement Python,
   par exemple `.venv\Scripts\maintai-predict.exe`.

## 5. Le rendu Git

- Lien de la pull request : non disponible dans l'environnement fourni.
- Le tag `tp4` existe sur GitHub : non vérifiable depuis ce dossier.
- `git status` avant le commit : non vérifiable, car le dossier fourni n'est
  pas un dépôt Git.

Après `python -m build`, les répertoires `build/`, `dist/` et
`maintai.egg-info/` sont générés localement. Ils doivent être ignorés par
`.gitignore` et ne pas être ajoutés au commit.

## 6. Ce qui reste flou

Le comportement exact de l'interface Streamlit dépend de la version de
Streamlit et du contexte d'exécution ; les deux tests UI échouent encore dans
l'environnement observé alors que les autres tests passent. La présence ou
l'absence de `InconsistentVersionWarning` dépend également de la version
scikit-learn réellement utilisée pour charger le modèle.
