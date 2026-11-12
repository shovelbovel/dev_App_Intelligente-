# Compte rendu · TP3 : une interface Streamlit pour MaintAI

**Groupe :** …  ·  **Membres :** …  ·  **Date :** 12/11/2026

## 1. Mise en place (dans `TP/TP3`)

Avec l'environnement virtuel du projet, `python -m pytest` donne :

```
============================= test session starts =============================
collected 23 items
tests\test_api.py .......                                                [ 30%]
tests\test_client.py ...                                                 [ 43%]
tests\test_data.py ...                                                   [ 56%]
tests\test_security.py .....                                              [ 78%]
tests\test_train.py ...                                                   [ 91%]
tests\test_ui.py ..                                                       [100%]
======================== 23 passed, 1 warning in 2.88s ========================
```

Dans l'état actuel du projet, aucun fichier de test n'échoue. L'unique avertissement
concerne la dépréciation de `httpx` avec `starlette.testclient`.

## 2. Lancer Streamlit

La commande `streamlit run ui/app.py`, exécutée sans avoir activé l'environnement
virtuel, échoue avec :

```
streamlit : The term 'streamlit' is not recognized as the name of a cmdlet,
function, script file, or operable program.
```

La commande `python -m streamlit run ui/app.py` fonctionne lorsque `python` est
celui de l'environnement virtuel. Elle demande à Python d'exécuter le module
`streamlit` installé dans cet environnement, même si le lanceur `streamlit` n'est
pas présent dans le `PATH`.

## 3. Sprint 1 : l'onglet « Données »

La partie de `ui/app.py` allant de `c1, c2, c3 = ...` au nuage de points est :

```python
c1, c2, c3 = st.columns(3)
c1.metric("Relevés", len(df))
c2.metric("Taux de panne", f"{df.failure.mean():.1%}")
c3.metric("Température moyenne", f"{df.temperature_c.mean():.1f} °C")

variable = st.selectbox("Variable", FEATURES)

tranches = pd.cut(df[variable], bins=10)
taux = df.groupby(tranches, observed=True).failure.mean()
taux.index = [round(t.mid, 1) for t in taux.index]
st.subheader(f"Taux de panne selon {variable}")
st.bar_chart(taux)

st.subheader("Température et vibration")
df_points = df.assign(etat=df.failure.map({0: "Normal", 1: "Panne"}))
st.scatter_chart(df_points, x="temperature_c", y="vibration_mm_s", color="etat")
```

Les valeurs affichées avec `data/sensors.csv` sont :

| Indicateur | Valeur affichée |
|---|---|
| Relevés | 5000 |
| Taux de panne | 13.6% |
| Température moyenne | 59.8 °C |

Avec `vibration_mm_s`, le taux de panne augmente nettement avec la vibration :
environ 2,0 % dans la première tranche, 9,8 %, 32,3 %, 66,4 %, 83,6 %, puis
100 % dans les tranches les plus élevées.

Après avoir ajouté `print("relance")` en haut de `ui/app.py`, le message apparaît
dans le terminal à chaque déplacement d'un curseur. Streamlit réexécute donc le
script de haut en bas à chaque interaction avec un widget.

`@st.cache_data` mémorise le résultat de `charger` pour éviter de relire le CSV
à chaque relance du script. Il est notamment invalidé si les arguments ou le
code de la fonction changent ; le chemin du fichier est l'argument mis en cache.

## 4. Sprint 2 : l'onglet « Prédiction »

La méthode `predict` de `maintai/client.py` est :

```python
def predict(self, reading: dict) -> dict:
    headers = {"X-API-Key": self.api_key} if self.api_key else {}
    r = self.http.post("/v1/predict", json=reading, headers=headers)
    if r.status_code != 200:
        raise APIError(r.status_code, r.json().get("detail"))
    return r.json()
```

Dernière ligne de `python -m pytest` à la fin du sprint 2 :

```
======================== 23 passed, 1 warning in 2.88s ========================
```

Avec le modèle chargé et l'API lancée :

| Essai | Ce qu'affiche Streamlit |
|---|---|
| valeurs par défaut, bonne clé | `Probabilité de panne : 95 %`, puis `ALERTE : risque de panne (seuil 30%).` |
| valeurs par défaut, fausse clé | avertissement `L'API a refusé la requête (code 401) : Clé API absente ou invalide` |
| API arrêtée (Ctrl+C dans le terminal d'uvicorn) | erreur `API injoignable : vérifiez l'URL et que uvicorn est lancé.` |

Le port 8501 n'est pas dans `MAINTAI_CORS_ORIGINS`, mais la prédiction
fonctionne car le navigateur n'effectue pas cette requête : c'est le client
Python de Streamlit qui appelle l'API. CORS est une protection appliquée par les
navigateurs pour les requêtes JavaScript entre origines différentes, pas par
`httpx`.

## 5. Questions de compréhension

1. Dans la page web du TP2, le JavaScript exécute `fetch` et envoie directement la
   requête à l'API depuis le navigateur. Dans Streamlit, `MaintaiClient` envoie
   la requête depuis le processus Python de Streamlit.
2. Les tests de `test_client.py` utilisent le `TestClient` de FastAPI injecté dans
   `MaintaiClient`. Ils appellent donc l'application en mémoire, sans démarrer
   un processus `uvicorn`.
3. Pour une démonstration à un client, je choisirais Streamlit : l'interface est
   rapide à présenter et les graphiques sont intégrés. Pour l'application d'un
   technicien, je choisirais aussi Streamlit dans ce TP, car les curseurs,
   l'exploration des données et la prédiction sont réunis sur une même page.
   Une page HTML/JavaScript serait préférable si l'on devait fournir une
   interface très légère, fortement personnalisée ou déployée sans Python côté
   interface.

## 6. Le rendu Git

- Lien de la pull request : non disponible dans l'environnement analysé.
- Le tag `tp3` existe sur GitHub : non vérifiable depuis ce dossier.
- `git status` avant le commit : impossible à exécuter ici, car le dossier fourni
  n'est pas un dépôt Git local (`fatal: not a git repository`).
  Le `.gitignore` prévoit toutefois d'ignorer `.env`, `data/*.csv` et `models/`.

## 7. Ce qui reste flou

- Le résultat historique demandé « juste après la mise en place » ne peut pas
  être reconstitué à partir du dépôt courant : les 23 tests passent déjà.
- Le lien de pull request et l'existence du tag doivent être complétés depuis
  GitHub par le groupe.
- Il reste à décider si l'avertissement de dépréciation concernant
  `starlette.testclient` doit être traité dans une future mise à jour des
  dépendances.
