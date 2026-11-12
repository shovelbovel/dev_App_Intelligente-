# Compte rendu · TP3 : une interface Streamlit pour MaintAI

**Groupe :** G1  ·  **Membres :** SAHIA ABDELALI  ·  **Date :** 12/11/26 10:00

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP3.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Mise en place (dans `TP/TP3`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
=================== 5 failed, 18 passed, 1 warning in 6.67s ===================
```

Quels fichiers de tests échouent, et quelle erreur donnent-ils ?

Deux fichiers échouent, pour deux raisons différentes :

```
FAILED tests/test_client.py::test_client_returns_prediction - NotImplementedE...
FAILED tests/test_client.py::test_client_wrong_key_raises_401 - NotImplemente...
FAILED tests/test_client.py::test_client_bad_reading_raises_422 - NotImplemen...
FAILED tests/test_ui.py::test_ui_shows_the_data - IndexError: list index out ...
FAILED tests/test_ui.py::test_ui_shows_the_prediction - IndexError: list inde...
```

- `tests/test_client.py` (3 tests) : `NotImplementedError: TP3 sprint 2 : MaintaiClient.predict`. La méthode
  `predict` du client se termine par un `raise NotImplementedError`, donc les trois tests échouent dès le premier
  appel, avant même d'atteindre leurs assertions.
- `tests/test_ui.py` (2 tests) : `IndexError: list index out of range`. Ici l'erreur est indirecte. Les tests
  cherchent `at.metric[0]` et `at.metric[-1]`, mais l'application ne contient encore aucun `st.metric` : les deux
  blocs `TODO` de `ui/app.py` n'affichent qu'un `st.info`. La liste des métriques est donc vide et l'indexation
  échoue. Le script lui-même ne plante pas (`assert not at.exception` passe) : c'est bien le contenu qui manque,
  pas le code qui est cassé.

## 2. Lancer Streamlit

Lancez d'abord `streamlit run ui/app.py`. Que s'affiche-t-il dans le navigateur ?

```
ModuleNotFoundError: No module named 'maintai'
Traceback:
File "C:\Users\alisa\Desktop\TP3\maintai-starter-tp3\ui\app.py", line 9, in <module>
    from maintai.client import APIError, MaintaiClient
```

Lancez ensuite `python -m streamlit run ui/app.py`. Pourquoi cette commande fonctionne-t-elle et pas la première ?

Tout se joue sur le contenu de `sys.path`, c'est-à-dire la liste des dossiers où Python cherche les modules.

Streamlit n'exécute pas le script comme Python le ferait : il le lit et l'exécute lui-même, et il ajoute à
`sys.path` le dossier **du script**, donc `ui/`. Or le paquet `maintai` n'est pas dans `ui/`, il est à la racine
du projet, un niveau au-dessus. Avec `streamlit run`, la racine n'est jamais ajoutée et l'import échoue.

`python -m streamlit` change cela : l'option `-m` fait que Python place **le dossier courant** en tête de
`sys.path` avant de lancer le module `streamlit`. Lancée depuis la racine du projet, la commande met donc cette
racine dans le chemin de recherche, et `from maintai.client import ...` est résolu.

J'ai vérifié que c'est bien la seule différence, en reproduisant les deux situations à l'identique :

```
--- A) avec le dossier courant dans sys.path (python -m) ---
import maintai OK
--- B) sans le dossier courant (streamlit.exe direct) ---
ModuleNotFoundError: No module named 'maintai'
```

Conséquence pratique : la commande doit être lancée **depuis la racine du projet**. Depuis un autre dossier,
`python -m streamlit run ...` échoue aussi, puisque c'est alors le mauvais dossier qui est ajouté au chemin.

## 3. Sprint 1 : l'onglet « Données »

Votre code de l'onglet « Données » (de `c1, c2, c3 = ...` jusqu'au nuage de points) :

```python
    # Les trois indicateurs : volume, taux de panne, température moyenne
    col_releves, col_taux, col_temp = st.columns(3)
    col_releves.metric("Relevés", f"{len(df)}")
    col_taux.metric("Taux de panne", f"{df[TARGET].mean():.1%}")
    col_temp.metric("Température moyenne", f"{df['temperature_c'].mean():.1f} °C")

    variable = st.selectbox("Variable à examiner", FEATURES)

    # pd.cut découpe la variable en tranches ; la moyenne de la cible y donne le taux de panne
    taux = df.groupby(pd.cut(df[variable], bins=8), observed=True)[TARGET].mean()
    taux.index = taux.index.astype(str)  # Arrow ne sait pas sérialiser des intervalles
    st.caption(f"Taux de panne par tranche de « {variable} »")
    st.bar_chart(taux)

    st.caption("Température et vibration, selon l'état de la machine")
    st.scatter_chart(
        df.assign(etat=df[TARGET].map({0: "normal", 1: "panne"})),
        x="temperature_c",
        y="vibration_mm_s",
        color="etat",
    )
```

Deux détails ont demandé une correction, parce que la version directe ne s'affiche pas :

- `taux.index = taux.index.astype(str)` : `pd.cut` produit un index d'objets `Interval`. Streamlit envoie les
  données au navigateur via Arrow, qui n'a pas de type « intervalle » ; sans cette conversion en texte, le
  graphique en barres ne peut pas être sérialisé.
- le nuage de points est coloré par une colonne `etat` (`"normal"` / `"panne"`) et non par `failure`. La colonne
  `failure` contient les entiers 0 et 1, que Streamlit interprète comme une échelle continue et rend en dégradé ;
  deux catégories de texte donnent deux couleurs distinctes et une légende lisible.

| Indicateur | Valeur affichée |
|---|---|
| Relevés | 5000 |
| Taux de panne | 13.6% |
| Température moyenne | 59.8 °C |

Choisissez `vibration_mm_s` dans la liste. Comment évolue le taux de panne quand la vibration augmente ?

Il augmente très fortement, et bien plus vite que pour les autres variables. Par tranche (`bins=8`) :

| Tranche de vibration (mm/s) | Taux de panne |
|---|---|
| (-0.002, 2.80] | 2.8 % |
| (2.80, 5.57] | 15.7 % |
| (5.57, 8.35] | 54.1 % |
| (8.35, 11.13] | 77.5 % |
| (11.13, 13.90] | 100.0 % |
| (13.90, 16.68] | 100.0 % |
| (19.45, 22.23] | 100.0 % |

On passe de 2.8 % à plus de 50 % en franchissant 5,6 mm/s, puis le taux sature à 100 % au-delà d'environ
11 mm/s : dans ce jeu de données, une vibration élevée suffit à elle seule à prédire la panne. À titre de
comparaison, la température ne va que de 0 % à 37.9 % entre sa première et sa dernière tranche. C'est cohérent
avec la façon dont les données sont générées dans `maintai/dataset.py`, où la vibration a le poids le plus lourd
dans le calcul du risque (`0.6 * (vibration_mm_s - 3)`).

Une tranche manque dans le tableau, (16.68, 19.45] : aucun relevé ne tombe dans cet intervalle, et
`observed=True` ne garde que les tranches réellement peuplées.

Ajoutez un `print("relance")` en haut de `ui/app.py`, puis déplacez un curseur. Que voyez-vous dans le terminal,
et qu'est-ce que cela montre sur le fonctionnement de Streamlit ?

`relance` s'affiche une première fois au chargement de la page, puis **une fois de plus à chaque interaction qui
déclenche une relance**. Le terminal accumule les lignes :

```
>>> 1. chargement initial de la page
relance
>>> 2. on change le selectbox (hors formulaire)
relance
>>> 3. on deplace un slider du formulaire SANS cliquer Predire
relance
    valeur du slider vue par le script : 72.0
>>> 4. on clique sur Predire
relance
```

Cela montre que Streamlit ne met pas à jour un composant isolé : il **réexécute tout le script de haut en bas**,
et reconstruit la page entière à partir du résultat. Il n'y a pas de « callback » attaché à un widget ; chaque
widget renvoie simplement sa valeur courante pendant cette nouvelle exécution.

Un détail important dans cette application : les curseurs sont à l'intérieur d'un `st.form`. Les widgets d'un
formulaire ne renvoient leur valeur qu'au moment de la validation, et non à chaque mouvement. On le voit à
l'étape 3 ci-dessus : le curseur a été placé à 100.0, mais le script voit encore 72.0 ; il faudra cliquer sur
« Prédire » pour que la nouvelle valeur soit prise en compte. Dans le navigateur, déplacer un de ces curseurs ne
provoque donc aucune relance — c'est précisément le rôle du formulaire : regrouper quatre saisies en un seul
envoi, au lieu d'appeler l'API à chaque petit déplacement. En revanche la liste déroulante de l'onglet
« Données », qui n'est pas dans un formulaire, relance le script dès qu'on en change.

À quoi sert `@st.cache_data` sur la fonction `charger` ?

Il découle directement du point précédent. Puisque le script entier est réexécuté à chaque relance, l'appel
`pd.read_csv(path)` le serait aussi : on relirait les 5000 lignes du CSV depuis le disque à chaque clic, pour un
résultat toujours identique. `@st.cache_data` mémorise la valeur de retour et la réutilise tant que les
arguments ne changent pas — ici le chemin du fichier. Le CSV n'est donc lu qu'une seule fois.

Le cache est indexé sur les arguments : si `path` changeait, la fonction serait réellement rappelée. `cache_data`
renvoie en plus une copie des données à chaque appel, de sorte qu'une modification du `DataFrame` dans la page ne
corrompe pas le contenu mis en cache.

## 4. Sprint 2 : l'onglet « Prédiction »

Votre méthode `predict` (`maintai/client.py`) :

```python
    def predict(self, reading: dict) -> dict:
        """Envoie un relevé ; lève APIError si l'API refuse, httpx.HTTPError si elle est injoignable."""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        r = self.http.post("/v1/predict", json=reading, headers=headers)
        if r.status_code != 200:
            raise APIError(r.status_code, r.json().get("detail"))
        return r.json()
```

Deux remarques sur ce code :

- l'en-tête n'est ajouté que si une clé est fournie. En l'absence de clé, mieux vaut ne pas envoyer l'en-tête du
  tout plutôt que d'envoyer une valeur vide ou `None` : `require_api_key` teste `x_api_key is None` et renvoie
  alors un 401 propre.
- `r.json().get("detail")` convient aux deux formes d'erreur que produit l'API : une chaîne de caractères pour le
  401 levé par `maintai/api/security.py`, et la liste des erreurs de validation de FastAPI pour le 422. La classe
  `APIError` met l'une comme l'autre dans son message.

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
23 passed, 1 warning in 7.20s
```

(L'avertissement est un `StarletteDeprecationWarning` interne au client de test de FastAPI, sans rapport avec le
code du TP.)

Avec l'API lancée (`uvicorn maintai.api.main:app --reload --env-file .env`) :

| Essai | Ce qu'affiche Streamlit |
|---|---|
| valeurs par défaut, bonne clé | Métrique « Probabilité de panne : 95 % », puis un bandeau rouge « ALERTE : probabilité au-dessus du seuil de 30%, maintenance à planifier. » (réponse de l'API : `failure_probability` 0.9475, `alert` true, `threshold` 0.3) |
| valeurs par défaut, fausse clé | Bandeau orange « L'API a refusé la demande (code 401) : Clé API absente ou invalide ». Même affichage si le champ de la clé est laissé vide. |
| API arrêtée (Ctrl+C dans le terminal d'uvicorn) | Bandeau rouge « API injoignable : vérifiez qu'elle est lancée et que l'URL « http://localhost:8000 » est correcte. » (`httpx.ConnectError`, attrapé par `except httpx.HTTPError`) |

Les trois cas correspondent bien aux trois chemins du `try / except / else` : une réponse exploitable, une
réponse de refus, ou pas de réponse du tout.

Le port 8501 n'est pas dans `MAINTAI_CORS_ORIGINS`, et pourtant la prédiction fonctionne. Pourquoi ?

Parce que, avec Streamlit, ce n'est plus le navigateur qui appelle l'API. La requête part du **serveur**
Streamlit : c'est le code Python de `MaintaiClient`, exécuté côté serveur avec `httpx`, qui contacte
`http://localhost:8000`. Le navigateur, lui, ne parle qu'au serveur Streamlit sur le port 8501.

Or le CORS est un mécanisme de sécurité **du navigateur** : il n'encadre que les requêtes émises par le
JavaScript d'une page vers une autre origine. Une requête HTTP faite par un programme Python n'envoie pas
d'en-tête `Origin`, ne déclenche pas de requête préalable (preflight), et aucune règle CORS ne lui est appliquée.
La liste `MAINTAI_CORS_ORIGINS` n'a donc aucun effet ici, et le port 8501 n'a pas besoin d'y figurer.

C'était l'inverse au TP2 : la page HTML appelait l'API avec `fetch`, depuis le navigateur, et il fallait pour
cela autoriser explicitement son origine (`http://localhost:5500`).

## 5. Questions de compréhension

1. **Dans la page web du TP2, qui envoie la requête à l'API ? Et dans Streamlit ?**

   Au TP2, c'est le navigateur de l'utilisateur : le `fetch` du JavaScript de la page part de sa machine, et la
   clé API y circule. Avec Streamlit, c'est le serveur Streamlit, en Python, via `httpx` dans `MaintaiClient` ;
   le navigateur ne reçoit que la page déjà construite, par la liaison websocket qu'il entretient avec ce
   serveur. Deux conséquences : le CORS ne s'applique plus (question précédente), et la clé API reste du côté
   serveur au lieu d'être exposée dans le navigateur.

2. **Pourquoi les tests de `test_client.py` n'ont-ils pas besoin d'uvicorn ?**

   Parce que `MaintaiClient` accepte son client HTTP en paramètre :

   ```python
   def __init__(self, url=..., api_key=None, http: httpx.Client | None = None):
       self.http = http or httpx.Client(base_url=url, timeout=5.0)
   ```

   Les tests y passent le `TestClient` de FastAPI (fixture `client` de `tests/conftest.py`), qui transmet les
   requêtes directement à l'application ASGI, dans le même processus : aucun serveur lancé, aucun port ouvert,
   aucune socket réseau. Le code testé est pourtant exactement celui qui tourne en production, puisque seul
   l'objet de transport change. C'est aussi ce qui rend les tests rapides et fiables : ni port déjà occupé, ni
   attente du démarrage du serveur.

3. **Page HTML + JavaScript (TP2) ou Streamlit (TP3) : laquelle choisiriez-vous pour une démonstration à un
   client ? Et pour l'application d'un technicien de maintenance ? Pourquoi ?**

   Pour une démonstration à un client : **Streamlit**. En quelques dizaines de lignes on obtient des indicateurs,
   deux graphiques et un formulaire corrects, sans écrire de HTML ni de CSS. C'est l'outil adapté quand ce qu'on
   veut montrer est le modèle, pas l'interface, et quand la démonstration se fait sur un poste maîtrisé.

   Pour l'application d'un technicien de maintenance : plutôt une **page HTML/JS**, ou une vraie application
   front-end. Un technicien travaille sur le terrain, souvent sur téléphone ou tablette, avec une connexion
   irrégulière. Streamlit impose un serveur Python qui garde une session par utilisateur et réexécute le script à
   chaque interaction : cela se prête mal à un réseau instable, à un affichage sur mobile et à une montée en
   charge, et l'apparence comme les parcours sont difficiles à adapter aux besoins réels (mode hors ligne, lecture
   d'un code-barres, intégration dans un outil existant).

   Le point important est que ce choix reste ouvert : les deux interfaces consomment la même API. C'est l'intérêt
   d'avoir séparé le modèle, l'API et l'interface — on peut changer d'interface sans toucher au reste.

## 6. Le rendu Git

- Lien de la pull request : *(à compléter après la création de la PR)*
- Le tag `tp3` existe sur GitHub : *(à vérifier après `git push --tags`)*
- `git status` avant le commit : `.env`, `data/` ou `models/` apparaissaient-ils ? **non**

  Les trois sont déjà couverts par le `.gitignore` du projet :

  ```
  .venv/
  __pycache__/
  *.pyc
  .pytest_cache/
  data/*.csv
  models/
  .env
  ```

  C'est voulu, et pour deux raisons différentes. `.env` contient la clé API : un secret n'a pas sa place dans un
  dépôt, d'autant qu'il resterait dans l'historique même après suppression — c'est pourquoi le dépôt ne fournit
  que `.env.example`, sans valeur réelle. `data/*.csv` et `models/` sont, eux, des fichiers **reproductibles** :
  `python -m maintai.dataset` et `python -m maintai.train` les régénèrent. Les versionner alourdirait le dépôt de
  binaires que Git ne sait pas comparer, pour une information que deux commandes suffisent à reconstruire.

  Seul `data/.gitkeep` est suivi, afin que le dossier `data/` existe après un clone.

## 7. Ce qui reste flou

- `st.cache_data` et `st.cache_resource` : j'ai compris que le premier sert aux données et renvoie une copie,
  mais je ne sais pas précisément quand le second devient nécessaire. Pour un modèle chargé avec `joblib`, dans
  l'interface, lequel faudrait-il utiliser ?
- `st.session_state` : il n'est pas utilisé dans ce TP. C'est bien ce qu'il faudrait pour garder l'historique des
  prédictions d'une relance à l'autre, puisque les variables ordinaires sont perdues à chaque réexécution ?
- Le déploiement : l'interface et l'API sont deux processus distincts, chacun sur son port. Comment les met-on en
  ligne ensemble, et comment l'interface connaît-elle l'adresse de l'API ailleurs que sur `localhost` ?
- Côté environnement, j'ai rencontré un problème propre à ma machine qui m'a pris du temps et que je ne
  m'explique pas complètement : la politique « Application Control » de Windows bloque l'exécutable `pip.exe`
  (contournée avec `python -m pip`) et la bibliothèque native de `pyarrow` en version 26.0.1, ce qui faisait
  échouer l'import de `scikit-learn` et de Streamlit. Installer `pyarrow==24.0.0` dans l'environnement virtuel a
  résolu le blocage, mais je ne sais pas pourquoi cette version-là passe et pas l'autre.
