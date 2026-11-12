# Compte rendu · TP3 : une interface Streamlit pour MaintAI

**Groupe :** g1  ·  **Membres :** hibatallah baetouty  ·  **Date :** 12/11/2026 10:00

---

## 1. Mise en place (dans `TP/TP3`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
=================== 5 failed, 18 passed, 1 warning in 6.83s ===================
```

Quels fichiers de tests échouent, et quelle erreur donnent-ils ?

Deux fichiers échouent, 5 tests en tout :

- `tests/test_client.py` (3 tests) → `NotImplementedError: TP3 sprint 2 : MaintaiClient.predict`.
  C'est normal : la méthode `predict` du client n'était pas encore écrite, elle ne contenait qu'un `raise`.
- `tests/test_ui.py` (2 tests) → `IndexError: list index out of range`.
  Les tests cherchent `at.metric[0]`, mais l'onglet « Données » n'affichait encore aucun `st.metric` :
  la liste est vide, donc l'index 0 n'existe pas.

Les 18 autres tests (données, entraînement, API, sécurité) passaient déjà, parce que cette partie
avait été faite dans les TP1 et TP2.

## 2. Lancer Streamlit

Lancez d'abord `streamlit run ui/app.py`. Que s'affiche-t-il dans le navigateur ?

```
ModuleNotFoundError: No module named 'maintai'
Traceback:
File "C:\Users\HP\Desktop\TP3\maintai-starter-tp3\ui\app.py", line 9, in <module>
    from maintai.client import APIError, MaintaiClient
```

Lancez ensuite `python -m streamlit run ui/app.py`. Pourquoi cette commande fonctionne-t-elle et pas la première ?

À cause du `sys.path`, la liste des dossiers où Python va chercher les modules.

Quand on lance `streamlit run ui/app.py`, Streamlit ajoute au `sys.path` **seulement le dossier du
script**, donc `ui/`. Dans `ui/` il n'y a pas de dossier `maintai`, donc l'import échoue.

Avec `python -m streamlit`, c'est le `-m` qui change tout : Python met le **dossier courant** en
première position du `sys.path`. Comme on lance la commande depuis la racine du projet, la racine
est dans le chemin et `maintai/` devient visible. Ça marche donc un peu par chance : il suffit de
lancer la commande depuis un autre dossier pour que ça casse à nouveau.

Pour ne plus dépendre de la commande utilisée, j'ai ajouté 3 lignes en haut de `ui/app.py` qui
ajoutent la racine du projet au `sys.path`. La racine est calculée à partir de `__file__`, pas du
dossier courant :

```python
RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
```

Depuis, les deux commandes marchent, et depuis n'importe quel dossier.
(Les tests, eux, n'avaient pas le problème : `pytest.ini` contient déjà `pythonpath = .`.)

## 3. Sprint 1 : l'onglet « Données »

Votre code de l'onglet « Données » (de `c1, c2, c3 = ...` jusqu'au nuage de points) :
*(commentaires raccourcis ici pour la lisibilité ; la version complète est dans `ui/app.py`)*

```python
with onglet_donnees:
    df = charger(get_settings().data_path)

    # 1. Trois indicateurs côte à côte
    col_releves, col_taux, col_temp = st.columns(3)
    col_releves.metric("Relevés", f"{len(df)}")
    col_taux.metric("Taux de panne", f"{df.failure.mean():.1%}")
    col_temp.metric("Température moyenne", f"{df.temperature_c.mean():.1f} °C")

    # 2. Choix de la variable à étudier (FEATURES vient de config.py)
    variable = st.selectbox("Variable à étudier", FEATURES)

    # 3. Taux de panne par tranche de cette variable
    tranches = pd.cut(df[variable], bins=8)
    taux_par_tranche = df.groupby(tranches, observed=True)["failure"].mean()
    # pd.cut donne des Interval, qu'Arrow ne sait pas sérialiser : on passe l'index en texte
    taux_par_tranche.index = [f"{t.left:.0f} – {t.right:.0f}" for t in taux_par_tranche.index]
    st.caption(f"Taux de panne par tranche de {variable}")
    st.bar_chart(taux_par_tranche)

    # 4. Nuage de points, coloré par panne (0/1 en texte, sinon Streamlit fait un dégradé)
    nuage = df.assign(etat=df.failure.map({0: "normal", 1: "panne"}))
    st.caption("Température et vibration, selon l'état de la machine")
    st.scatter_chart(nuage, x="temperature_c", y="vibration_mm_s", color="etat")
```

| Indicateur | Valeur affichée |
|---|---|
| Relevés | 5000 |
| Taux de panne | 13.6% |
| Température moyenne | 59.8 °C |

Choisissez `vibration_mm_s` dans la liste. Comment évolue le taux de panne quand la vibration augmente ?

Il augmente très vite :

| Tranche (mm/s) | Taux de panne |
|---|---|
| 0 – 3 | 2.8 % |
| 3 – 6 | 15.7 % |
| 6 – 8 | 54.1 % |
| 8 – 11 | 77.5 % |
| 11 et plus | 100 % |

En dessous de 3 mm/s presque aucune machine ne tombe en panne, et au-dessus de 11 mm/s elles
tombent toutes en panne. La vibration a donc l'air d'être la variable la plus utile pour prévoir une
panne. Avec la température, la montée est beaucoup plus douce (de 0 % à environ 38 %), donc elle
explique moins bien les pannes toute seule.

Ajoutez un `print("relance")` en haut de `ui/app.py`, puis déplacez un curseur. Que voyez-vous dans le terminal, et qu'est-ce que cela montre sur le fonctionnement de Streamlit ?

« relance » s'affiche une fois de plus dans le terminal à chaque fois qu'on touche un curseur, un
onglet ou la liste déroulante. Les lignes s'empilent.

Ça montre que Streamlit ne met pas juste à jour le petit morceau qui a changé : à chaque
interaction, il **réexécute tout le script de haut en bas**, des imports jusqu'à la dernière ligne.
C'est ce qui rend le code simple à écrire (pas de callbacks, pas d'état à synchroniser), mais il
faut y penser : tout ce qui est lent (lire un fichier, appeler l'API) serait refait à chaque clic.
D'où le cache sur `charger`, et d'où le `st.form` dans l'onglet « Prédiction », qui n'envoie la
requête qu'au clic sur le bouton et pas à chaque mouvement de curseur.

À quoi sert `@st.cache_data` sur la fonction `charger` ?

Comme le script est relancé en entier à chaque clic, `pd.read_csv` serait refait à chaque fois pour
rien, alors que le fichier ne change pas. `@st.cache_data` garde le résultat en mémoire : le CSV
n'est lu qu'une seule fois, et les fois suivantes Streamlit renvoie directement le DataFrame déjà
chargé. Le cache est lié aux arguments de la fonction (ici le chemin), donc si le chemin change, le
fichier est relu.

Petite conséquence : comme l'objet en cache est réutilisé à chaque relance, il ne faut pas le
modifier. C'est pour ça que j'utilise `.assign` pour le nuage de points, qui travaille sur une
copie, au lieu d'ajouter la colonne directement dans `df`.

## 4. Sprint 2 : l'onglet « Prédiction »

Votre méthode `predict` (`maintai/client.py`) :

```python
    def predict(self, reading: dict) -> dict:
        """Envoie un relevé ; lève APIError si l'API refuse, httpx.HTTPError si elle est injoignable."""
        # 1. En-tête d'authentification, seulement si une clé est donnée (sinon l'API répond 401)
        headers = {"X-API-Key": self.api_key} if self.api_key else {}

        # 2. L'équivalent Python du fetch() du TP2 ; si le serveur est éteint, httpx lève ici
        r = self.http.post("/v1/predict", json=reading, headers=headers)

        # 3. Autre chose que 200 = l'API refuse : on transforme ça en APIError
        if r.status_code != 200:
            try:
                detail = r.json().get("detail")
            except ValueError:
                detail = r.text  # corps non-JSON (page d'erreur d'un proxy par exemple)
            raise APIError(r.status_code, detail)

        # 4. Cas normal : {failure_probability, alert, threshold, model_version}
        return r.json()
```

Je n'utilise pas `raise_for_status()` ici, contrairement à `health()` : il lèverait bien une erreur,
mais on perdrait le contenu de `detail`, qui est justement le message que l'interface affiche à
l'utilisateur.

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
========================= 23 passed, 1 warning in 9.22s =========================
```

Avec l'API lancée (`uvicorn maintai.api.main:app --reload --env-file .env`) :

| Essai | Ce qu'affiche Streamlit |
|---|---|
| valeurs par défaut, bonne clé | « Probabilité de panne : **95 %** », puis un bandeau rouge « ⚠️ ALERTE : panne probable (seuil 30%) — planifier une maintenance. » (l'API renvoie `failure_probability: 0.9475`, `alert: true`) |
| valeurs par défaut, fausse clé | bandeau jaune : « L'API a refusé le relevé (code 401) : Clé API absente ou invalide » |
| API arrêtée (Ctrl+C dans le terminal d'uvicorn) | bandeau rouge : « API injoignable : vérifiez l'URL et que le serveur est démarré. » |

Les deux derniers cas ne sont pas la même erreur dans le code : la fausse clé lève une `APIError`
(l'API a répondu, mais elle refuse → l'utilisateur peut corriger, donc `st.warning` en jaune), et
l'API arrêtée lève une `httpx.HTTPError` (aucune réponse du tout → panne technique, donc `st.error`
en rouge).

Le port 8501 n'est pas dans `MAINTAI_CORS_ORIGINS`, et pourtant la prédiction fonctionne. Pourquoi ?

Parce que le CORS est une règle appliquée par le **navigateur**, et qu'ici ce n'est pas le navigateur
qui appelle l'API.

Dans le TP2, la page web tournait dans le navigateur et c'était le JavaScript, sur la machine de
l'utilisateur, qui faisait le `fetch`. Le navigateur ajoutait un en-tête
`Origin: http://localhost:5500` et vérifiait que l'API l'autorisait : il fallait donc que le port
5500 soit dans `MAINTAI_CORS_ORIGINS`.

Dans le TP3, la requête part du **serveur Streamlit**, en Python, avec httpx. Il n'y a pas de
navigateur dans cet appel, donc pas d'en-tête `Origin` et aucune vérification CORS. Le navigateur ne
parle qu'à Streamlit (port 8501), et Streamlit parle à l'API (port 8000). Le port 8501 n'a donc
aucune raison d'être dans la liste.

## 5. Questions de compréhension

1. Dans la page web du TP2, qui envoie la requête à l'API ? Et dans Streamlit ?

   Dans le TP2, c'est le navigateur de l'utilisateur, avec `fetch` en JavaScript. L'URL et la clé
   API sont dans le navigateur, et chaque utilisateur appelle l'API lui-même.
   Dans le TP3, c'est le serveur Streamlit, en Python, avec `httpx` (`MaintaiClient`). Le navigateur
   ne reçoit que le résultat déjà affiché. C'est pour ça que le CORS ne se déclenche pas, et aussi
   que la clé peut rester côté serveur.

2. Pourquoi les tests de `test_client.py` n'ont-ils pas besoin d'uvicorn ?

   Parce que `MaintaiClient` accepte un paramètre `http`, et que les tests y passent le `TestClient`
   de FastAPI (fixture `client` dans `conftest.py`). Les requêtes ne passent alors pas par le
   réseau : elles entrent directement dans l'application FastAPI, en mémoire, dans le même
   processus. Pas de port à ouvrir, pas de serveur à lancer, et les tests restent rapides. C'est
   exactement le même code client qui est testé, seul le transport change.

3. Page HTML + JavaScript (TP2) ou Streamlit (TP3) : laquelle choisiriez-vous pour une démonstration à un client ? Et pour l'application d'un technicien de maintenance ? Pourquoi ?

   Pour une **démo à un client**, je prendrais Streamlit. C'est beaucoup plus rapide à écrire (les
   indicateurs, les onglets et les graphiques tiennent en quelques lignes), le rendu est propre sans
   écrire de CSS, et on peut changer une variable ou un graphique pendant la réunion.
   Pour l'**application du technicien**, je prendrais plutôt la page HTML + JS. Elle est légère,
   elle marche bien sur un téléphone ou une tablette dans un atelier, elle peut s'intégrer dans un
   outil qui existe déjà, et on contrôle vraiment l'interface (gros boutons, mode hors-ligne, lecture
   de code-barres…). Streamlit relance tout le script à chaque clic et garde tout l'état sur le
   serveur : ça devient lourd avec beaucoup d'utilisateurs en même temps, et on ne peut pas
   personnaliser l'affichage autant qu'on veut.

## 6. Le rendu Git

- Lien de la pull request : … *(à compléter)*
- Le tag `tp3` existe sur GitHub : non *(à faire)*
- `git status` avant le commit : `.env`, `data/` ou `models/` apparaissaient-ils ? non

Pour l'instant le dossier n'est pas encore un dépôt Git (`git status` répond
`fatal: not a git repository`), donc il n'y a ni commit, ni pull request, ni tag. Il me reste à
faire : `git init`, le commit, la PR et le tag `tp3`.

Par contre le `.gitignore` est déjà correct : il contient `.env`, `data/*.csv` et `models/`, donc
ces fichiers n'apparaîtront pas dans `git status`. C'est surtout important pour `.env`, qui contient
la clé API et ne doit jamais être commité. Le fichier `.env.example`, lui, est fait pour être
commité : il ne doit contenir qu'une valeur d'exemple, pas la vraie clé.

## 7. Ce qui reste flou

- La différence exacte entre `st.cache_data` et `st.cache_resource`. J'ai compris que `cache_data`
  sert aux données (il en garde une copie), mais je ne sais pas trop dans quels cas il faut vraiment
  utiliser l'autre.
- Ce qui se passe quand plusieurs personnes ouvrent l'application en même temps : est-ce que chacune
  a ses propres curseurs et sa propre clé, ou est-ce que tout est partagé ? Et est-ce que le cache
  est commun à tout le monde ?
- Pour l'instant chaque utilisateur doit taper la clé API dans la barre latérale. Dans une vraie
  application, ce serait sûrement mieux que le serveur Streamlit lise la clé dans son propre `.env`,
  mais je ne sais pas comment on fait ça proprement.
- Je n'ai pas bien compris pourquoi les objets `Interval` de `pd.cut` posent problème à l'affichage.
  J'ai contourné en transformant l'index en texte et ça marche, mais je ne saurais pas expliquer
  précisément ce qui bloque dans Arrow.
