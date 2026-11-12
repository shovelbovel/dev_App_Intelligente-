# Compte rendu · TP4 : MaintAI devient un package Python

**Groupe : g1  ·  **Membres : Hibatallah Baetouty  ·  **Date :** 12/11/2026 12:15

---

## 1. Mise en place (dans `TP/TP4`, avec son propre `.venv`)

Dernière ligne de `python -m pytest` juste après `pip install -r requirements.txt` :

```
(non capturé : pytest n'a été lancé qu'après l'installation du package — voir §2)
```

Quels sont les deux tests qui échouent, et pourquoi ?

Les deux tests de `tests/test_package.py` : `test_installed_version_matches_the_code` et
`test_command_is_declared`. Ils ne regardent pas le code mais les **métadonnées du package
installé** : le premier lit `version("maintai")`, le second cherche `maintai-predict` dans les
points d'entrée. Tant que `pip install -e .` n'a pas été lancé, ces métadonnées n'existent pas.

## 2. Sprint 1 : `pyproject.toml` et `pip install -e .`

Nos sections `dependencies` et `[project.scripts]` :

```toml
dependencies = [
    "pandas>=2.2",        # maintai/data.py, dataset.py, predict.py
    "numpy>=1.26",        # maintai/dataset.py
    "scikit-learn>=1.5",  # maintai/data.py, train.py
    "joblib>=1.4",        # maintai/predict.py, train.py
    "httpx>=0.27",        # maintai/client.py
]

[project.scripts]
maintai-predict = "maintai.cli:main"
```

Pourquoi `pytest` et `fastapi` ne sont-ils pas dans `dependencies` ?

Parce que le code de `maintai/` n'en a pas besoin pour faire son travail de base. `pytest` ne sert
qu'à nous, pour développer ; `fastapi` ne sert qu'à qui veut lancer l'API. Les mettre en
dépendances obligatoires forcerait tous les utilisateurs à les télécharger pour rien. Ils sont donc
dans les groupes optionnels (`[project.optional-dependencies]`), qu'on installe à la demande avec
`pip install -e ".[api,dev]"`.

Sortie de `pip show maintai` (les quatre premières lignes) :

```
Name: maintai
Version: 0.2.0
Summary: TODO : une phrase qui dit ce que fait le package
Home-page:
```

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
27 passed, 1 warning in 9.54s
```

Placez-vous dans un autre dossier (`cd %TEMP%`) et lancez `maintai-predict 72 6 85 15000`, puis
`python -c "import maintai; print(maintai.__file__)"`. Qu'affichent ces deux commandes ? Où Python
trouve-t-il le code de `maintai` ?

```
C:\Users\HP\AppData\Local\Temp> maintai-predict 72 6 85 15000
Probabilité de panne : 95 % (ALERTE)

C:\Users\HP\AppData\Local\Temp> python -c "import maintai; print(maintai.__file__)"
C:\Users\HP\Desktop\TP4\maintai-starter-tp4\maintai\__init__.py
```

Python trouve le code **dans notre dossier de projet**, pas dans le venv. Rien n'a été copié : avec
`-e`, pip a seulement déposé dans `site-packages` un fichier
`__editable__.maintai-0.2.0.pth` et un « finder » qui contient le chemin vers
`maintai-starter-tp4\maintai\`. Et la commande marche partout parce que `.venv\Scripts\` est dans
le `PATH` — pas parce qu'on est dans le projet.

Modifiez le message affiché par `maintai/cli.py`, puis relancez `maintai-predict` sans réinstaller.
Le changement est-il visible ? Pourquoi ?

Oui, immédiatement.

```
avant : Probabilité de panne : 95 % (ALERTE)
après : [maintai 0.2.0] Probabilité de panne : 95 % -> ALERTE (seuil 30 %)
```

Puisque l'installation ne contient qu'un **pointeur** vers nos fichiers, Python relit le source à
chaque lancement. Le cycle éditer → tester ne passe plus par pip.

Attention quand même : ce rechargement ne concerne que le **contenu** des modules. Si on change le
nom de la commande, qu'on ajoute une dépendance ou qu'on monte la version, il faut réinstaller :
le `.exe` et les métadonnées sont figés à l'installation.

## 3. Sprint 2 : construire et installer le wheel

Sortie de `dir dist` après `python -m build` :

```
maintai-0.2.0-py3-none-any.whl    11 686 octets
maintai-0.2.0.tar.gz              12 425 octets
```

Contenu du wheel (`tar -tf dist\maintai-0.2.0-py3-none-any.whl`). Le modèle, les tests et `ui/`
y sont-ils ? Pourquoi ?

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

**Aucun des trois.** Le wheel ne contient que les 12 fichiers `.py` de `maintai/`. Le wheel pèse
11 Ko, ce qui le dit déjà : le modèle seul est bien plus gros.

- `tests/` et `ui/` sont écartés par `include = ["maintai*"]` dans `[tool.setuptools.packages.find]`.
- `models/` et `data/` le seraient de toute façon : setuptools n'embarque que des **paquets Python**
  (dossiers importables), et par défaut seulement les `.py`. Un `.joblib` ou un `.csv` demanderait
  une déclaration explicite, et le fichier devrait être *à l'intérieur* de `maintai/`.

À noter : la **sdist** (`.tar.gz`), elle, contient `tests/`, `pyproject.toml` et `README.md`. Les
deux formats n'ont pas le même rôle — la sdist sert à reconstruire et vérifier, le wheel à installer.

Dans un environnement neuf (`%TEMP%\essai`), installez le wheel et lancez `maintai-predict` :

| Étape | Ce qui s'affiche |
|---|---|
| sans `MAINTAI_MODELS_DIR` | `Modèle introuvable : ...\essai\.venv\Lib\site-packages\models\model.joblib` / `Entraînez-le (python -m maintai.train) ou indiquez son dossier dans MAINTAI_MODELS_DIR.` — **exit 1** |
| avec `MAINTAI_MODELS_DIR` vers nos `models` | `InconsistentVersionWarning: Trying to unpickle estimator StandardScaler from version 1.8.0 when using version 1.9.1.` (×3 : StandardScaler, LogisticRegression, Pipeline), puis `[maintai 0.2.0] Probabilité de panne : 95 % -> ALERTE (seuil 30 %)` — **exit 0** |
| après `pip install scikit-learn==1.8.0` | `[maintai 0.2.0] Probabilité de panne : 95 % -> ALERTE (seuil 30 %)` — **plus aucun avertissement, exit 0** |

Bon à savoir : `pip install` du wheel seul a suffi à tirer **automatiquement** pandas, numpy,
scikit-learn, joblib, httpx et leurs dépendances. C'est la section `dependencies` qui paie : on n'a
donné au « collègue » qu'un fichier de 11 Ko. Et `maintai-predict.exe` est bien apparu dans son
`Scripts\`, grâce à `[project.scripts]`.

D'où vient l'avertissement `InconsistentVersionWarning` ? Quelle ligne de `models/model_info.json`
permet de le comprendre ?

La ligne :

```json
"sklearn_version": "1.8.0"
```

Le modèle a été entraîné avec scikit-learn 1.8.0 (`train.py` écrit cette ligne au moment de
l'entraînement, et joblib grave la même valeur dans le fichier `.joblib`). Mais notre borne
`scikit-learn>=1.5` a laissé pip installer la plus récente, 1.9.1. L'avertissement est la
comparaison des deux. Un modèle sauvegardé avec joblib n'est pas un format d'échange : il est
couplé aux classes de la version qui l'a produit.

Ce n'est pas une erreur mais un *warning* : la commande aboutit et donne la bonne réponse — mais
« à vos risques », sans garantie.

## 4. Questions de compréhension

1. **Quelle différence entre `requirements.txt` et la liste `dependencies` de `pyproject.toml` ?**

   Pas le même métier. `dependencies` décrit la **compatibilité** de notre bibliothèque : des bornes
   larges (`>=`), pour cohabiter avec ce que l'utilisateur a déjà. `requirements.txt` décrit la
   **reproductibilité** d'un déploiement : des versions figées (`==`), pour refaire l'environnement
   à l'identique.

   Le TP le montre en direct : notre collègue a installé le wheel sans appliquer
   `requirements.txt`, il a eu sklearn 1.9.1 au lieu de 1.8.0, d'où l'avertissement.

2. **Quelle différence entre `pip install -e .` et `pip install dist\...whl` ?**

   | | editable (`-e .`) | wheel |
   |---|---|---|
   | Où est le code | dans notre projet | copié dans `site-packages` |
   | `maintai.__file__` | `...\maintai-starter-tp4\maintai\__init__.py` | `...\site-packages\maintai\__init__.py` |
   | Une modification du code | visible aussitôt | demande rebuild + réinstallation |
   | Pour quoi | développer | déployer |

   Conséquence qu'on n'avait pas vue venir : `config.py` calcule ses chemins à partir de
   l'emplacement du code (`ROOT = Path(__file__).parent.parent`). En editable, `ROOT` retombait sur
   le projet, donc le modèle était trouvé « par chance ». Avec le wheel, `ROOT` pointe dans
   `site-packages`, et le modèle n'y est pas — d'où `MAINTAI_MODELS_DIR`.

3. **Qu'est-ce qu'un point d'entrée (`[project.scripts]`) ? Où pip crée-t-il `maintai-predict.exe` ?**

   C'est une ligne `nom-de-commande = "module:fonction"` qui dit : « quand on tape
   `maintai-predict`, appelle `main()` de `maintai/cli.py` ». À l'installation, pip lit cette
   métadonnée et génère un petit exécutable lanceur dans **`.venv\Scripts\`**
   (`.venv/bin/` sous Linux/macOS). Comme ce dossier est dans le `PATH` du venv activé, la commande
   est disponible depuis n'importe quel dossier.

## 5. Le rendu Git

- Lien de la pull request : …
- Le tag `tp4` existe sur GitHub : …
- `git status` avant le commit : `dist/`, `build/` ou `maintai.egg-info/` apparaissaient-ils ? …

## 6. Ce qui reste flou

- Notre borne `scikit-learn>=1.5` est trop permissive pour un package qui recharge des modèles
  joblib. `scikit-learn>=1.8,<1.9` serait plus honnête : la contrainte serait dans les métadonnées,
  là où pip peut l'appliquer, au lieu de dépendre du bon vouloir de `requirements.txt`. Quelle est
  la bonne pratique quand on distribue du code qui désérialise des modèles ?
- Le `description` du `pyproject.toml` est resté sur `"TODO : ..."`, et on l'a découvert **gravé en
  `Summary:`** dans le wheel construit. Sur PyPI, ce serait la phrase affichée sous le nom du
  package.
- Si le modèle n'a pas sa place dans le wheel, où le met-on vraiment en production (registre de
  modèles ? stockage objet ? volume monté) et comment garantit-on que la version du modèle et celle
  du code vont ensemble ?
