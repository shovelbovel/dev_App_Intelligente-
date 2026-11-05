# Compte rendu · TP2 : tester, sécuriser et appeler l'API MaintAI

**Groupe :** …  ·  **Membres :** …  ·  **Date :** 05/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP2.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Activité 1 : casser son API (dans `TP/TP1`)

Vos cinq requêtes, le code que vous aviez **prévu**, puis le code **obtenu** dans `/docs` :

| Requête | Ce qui ne va pas | Code prévu | Code obtenu |
|---|---|---|---|
| 1 · `POST /v1/predict` sans `load_pct` | champ manquant | 422 | 422 |
| 2 · `POST /v1/predict` avec `"load_pct": 250` | valeur absurde | 422 | 422 |
| 3 · `POST /v1/predict` avec `"temperature_c": "chaud"` | texte au lieu d'un nombre | 422 | 422 |
| 4 · `POST /v1/predict` avec `"pression_bar": 3.0` en plus | champ en trop | 422 | 422 |
| 5 · `POST /v1/predire` (relevé valide) | mauvaise route | 404 | 404 |

Une de vos prévisions était-elle fausse ? Laquelle, et pourquoi ?

Non, les cinq codes obtenus correspondent aux prévisions. Le cas le plus incertain était le
**champ en trop** : par défaut, Pydantic *ignore* les champs inconnus (la requête aurait reçu 200).
Ici il est refusé (422) parce que `SensorReading` déclare `extra="forbid"`. La **mauvaise route**
donne 404 et non 422 : la route est le premier contrôle, avant même de lire le corps.

Dernière ligne de `python -m pytest` avec `tests/test_casser.py` (dans `TP/TP1`) :

```
18 passed
```

À quoi sert `@pytest.mark.parametrize` ? Combien de tests pytest compte-t-il pour votre fonction, et pourquoi ?

`parametrize` exécute la même fonction de test une fois par ligne de la liste `CAS_REFUSES`, en
injectant les valeurs (`description, url, corps, attendu`) comme arguments. On écrit la logique une
seule fois et on ajoute un cas en ajoutant une ligne. pytest compte **5 tests** pour cette seule
fonction (un par cas), chacun nommé dans le rapport (`-v`) :

```
tests/test_casser.py::test_requete_refusee[champ manquant-/v1/predict-corps0-422] PASSED
tests/test_casser.py::test_requete_refusee[valeur absurde-/v1/predict-corps1-422] PASSED
tests/test_casser.py::test_requete_refusee[texte au lieu d'un nombre-/v1/predict-corps2-422] PASSED
tests/test_casser.py::test_requete_refusee[champ en trop-/v1/predict-corps3-422] PASSED
tests/test_casser.py::test_requete_refusee[mauvaise route-/v1/predire-corps4-404] PASSED
```

## 2. ruff

Sortie de `ruff check .` dans `TP/TP1` :

```
All checks passed!
```

Quelle différence entre `ruff check .` et `python -m pytest` ? Que vérifie chacun ?

`ruff` fait une **analyse statique** : il *lit* le code sans l'exécuter et signale ce qui est mal
écrit (imports inutiles F401, imports mal rangés I001, variables jamais utilisées, syntaxe
dépassée). `pytest` *exécute* le code et vérifie son **comportement** : que l'API répond le bon
code, que le modèle bat la baseline, etc. Un code peut passer ruff et être faux, ou être juste et
mal écrit : les deux sont complémentaires.

## 3. Mise en place du TP2 (dans `TP/TP2`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
2 failed, 16 passed, 1 warning in 2.75s
```

Quels sont les deux tests qui échouent, et que reçoivent-ils au lieu de 401 ?

`test_missing_key_is_rejected` (sans clé) et `test_wrong_key_is_rejected` (avec une fausse clé).
Ils reçoivent **200** au lieu de 401 : l'API ne vérifie encore aucune clé et répond à tout le monde.

## 4. La clé API (sprint 1)

Votre fonction `require_api_key()` (`maintai/api/security.py`) :

```python
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Refuse la requête si la clé est absente ou fausse."""
    expected = get_settings().api_key
    if not expected:
        # Erreur de configuration du serveur, pas du client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La clé API du serveur n'est pas configurée (MAINTAI_API_KEY)",
        )
    # compare_digest : durée constante, ne trahit pas le nombre de caractères justes
    if x_api_key is None or not secrets.compare_digest(
        x_api_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API absente ou invalide",
        )
```

Votre ligne `router = ...` dans `maintai/api/main.py` :

```python
router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])
```

Après avoir écrit `security.py` seul (sans toucher au router), combien de tests échouent ? Pourquoi ?

Toujours **2** : la fonction existe, mais aucune route ne l'appelle. Tant qu'elle n'est pas
déclarée comme dépendance du router, FastAPI ne l'exécute jamais et `/v1/predict` reste ouvert.

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
18 passed
```

Lancez `uvicorn maintai.api.main:app --reload --env-file .env`, puis envoyez ces requêtes (avec `/docs` ou `curl.exe`) :

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health`, sans clé | 200 | `{"status":"ok","model_loaded":true}` |
| `POST /v1/predict`, relevé normal, sans clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, relevé normal, fausse clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, relevé normal, bonne clé | 200 | `{"failure_probability":0.0027,"alert":false,"threshold":0.3,"model_version":"2026-11-05T11:28:24Z"}` |
| `POST /v1/predict`, 500 °C, sans clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, 500 °C, bonne clé | 422 | `{"detail":[{"type":"less_than_equal","loc":["body","temperature_c"],"msg":"Input should be less than or equal to 150","input":500,"ctx":{"le":150.0}}]}` |

500 °C sans clé et 500 °C avec la clé ne donnent pas le même code. Pourquoi ?

Les contrôles se font dans l'ordre : route (404) → **clé (401)** → données (422) → modèle (503).
La dépendance `require_api_key` s'exécute avant la validation du corps. Sans clé, la requête est
arrêtée au contrôle 2 : l'API ne regarde même pas les données (401). Avec la bonne clé, elle passe
ce contrôle et c'est la validation Pydantic (`temperature_c ≤ 150`) qui la refuse (422).

Relancez uvicorn **sans** `--env-file .env` et envoyez un relevé avec votre clé. Quel code obtenez-vous, et pourquoi ce n'est pas 401 ?

**500**, `{"detail":"La clé API du serveur n'est pas configurée (MAINTAI_API_KEY)"}`. Sans
`--env-file`, `MAINTAI_API_KEY` n'est pas défini, donc `get_settings().api_key` vaut `None`. Ce
n'est pas la faute du client (sa clé n'est pas forcément fausse) : c'est le **serveur** qui est mal
configuré, d'où une erreur 5xx et non 4xx. Refuser en 500 évite aussi un serveur ouvert à tous par
oubli de configuration.

## 5. La page web (sprint 2)

Votre code `fetch` (le contenu du `addEventListener` dans `web/index.html`) :

```javascript
document.getElementById("go").addEventListener("click", async () => {
  const reading = Object.fromEntries(FEATURES.map(f => [f, Number(document.getElementById(f).value)]));
  const url = document.getElementById("url").value.trim().replace(/\/+$/, "");
  const cle = document.getElementById("key").value.trim();
  show("", "Envoi…");
  try {
    const resp = await fetch(`${url}/v1/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": cle },
      body: JSON.stringify(reading),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      // 401 (clé), 422 (données), 503 (modèle), 500 (serveur mal configuré)
      const detail = typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail ?? data);
      show("err", `Erreur ${resp.status} : ${detail}`);
      return;
    }
    const pct = (data.failure_probability * 100).toFixed(1);
    if (data.alert) {
      show("alert", `ALERTE : probabilité de panne ${pct} % (seuil ${data.threshold}, modèle ${data.model_version})`);
    } else {
      show("ok", `Pas d'alerte : probabilité de panne ${pct} % (seuil ${data.threshold}, modèle ${data.model_version})`);
    }
  } catch (e) {
    // fetch échoue sans réponse : API arrêtée, ou CORS qui bloque (voir la console F12)
    show("err", `API injoignable (arrêtée, ou origine refusée par CORS) : ${e.message}`);
  }
});
```

Ce qu'affiche la page (servie sur le port 5500) :

| Essai | Ce qu'affiche la page |
|---|---|
| relevé normal, bonne clé | (fond vert) `Pas d'alerte : probabilité de panne … % (seuil 0.3, modèle …)` |
| 500 °C, bonne clé | (fond orange) `Erreur 422 : [{"type":"less_than_equal","loc":["body","temperature_c"],"msg":"Input should be less than or equal to 150",…}]` |
| relevé normal, fausse clé | (fond orange) `Erreur 401 : Clé API absente ou invalide` |

**Expérience CORS.** Servez la page sur le port 5501. Que dit la page, et que dit la console (F12) ?

La page affiche `API injoignable (arrêtée, ou origine refusée par CORS) : Failed to fetch`.
La console indique :
`Access to fetch at 'http://localhost:8000/v1/predict' from origin 'http://localhost:5501' has been blocked by CORS policy: Response to preflight request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present on the requested resource.`
Côté API, la requête de pré-vérification `OPTIONS` reçoit **400 Bad Request** sans en-tête
`Access-Control-Allow-Origin`, car `http://localhost:5501` n'est pas dans `MAINTAI_CORS_ORIGINS`.
Le navigateur n'envoie donc jamais le `POST`.

Pourquoi `curl.exe` obtient-il une réponse alors que la page du port 5501 est bloquée ?

CORS est une règle **du navigateur**, pas de l'API : c'est le navigateur qui demande la permission
(`OPTIONS`) et qui bloque la réponse si l'origine n'est pas autorisée. Il protège l'utilisateur
contre une page qui utiliserait son navigateur pour appeler l'API. `curl.exe` (comme Java ou Python)
n'est pas un navigateur : il n'a pas d'origine, ne fait pas de pré-vérification et ignore les
en-têtes CORS. Pour lui, seule la **clé** compte : c'est pour cela qu'elle reste indispensable.

## 6. Les tests de l'activité 1 dans le TP2

Copiez `test_casser.py` dans `TP/TP2/tests`. Sans `headers=HEADERS`, combien de tests échouent, et avec quel code ? Lequel des cinq cas passe quand même, et pourquoi ?

**4 tests échouent** : champ manquant, valeur absurde, texte au lieu d'un nombre et champ en trop
reçoivent **401** au lieu de 422, car la clé est vérifiée avant les données.

```
FAILED tests/test_casser.py::test_requete_refusee[champ manquant-/v1/predict-corps0-422]
FAILED tests/test_casser.py::test_requete_refusee[valeur absurde-/v1/predict-corps1-422]
FAILED tests/test_casser.py::test_requete_refusee[texte au lieu d'un nombre-/v1/predict-corps2-422]
FAILED tests/test_casser.py::test_requete_refusee[champ en trop-/v1/predict-corps3-422]
4 failed, 1 passed
```

Le cas **mauvaise route** passe quand même (404) : la route `/v1/predire` n'existe pas, donc
aucune dépendance du router n'est exécutée. Le contrôle de la route vient avant celui de la clé.

Dernière ligne de `python -m pytest` avec `headers=HEADERS` :

```
23 passed, 1 warning in 2.21s
```

## 7. Questions de compréhension

1. Quelle différence entre 401 et 422 ? Et entre 401 et 403 ?
   **401 Unauthorized** : l'API ne sait pas *qui* appelle (clé absente ou invalide), c'est
   l'authentification. **422 Unprocessable Entity** : l'appelant est reconnu, mais les *données*
   ne respectent pas le schéma (champ manquant, hors bornes…). **403 Forbidden** : l'appelant est
   bien identifié, mais il n'a *pas le droit* de faire cette action (autorisation). 401 = « qui
   es-tu ? », 403 = « je sais qui tu es, mais c'est non ».
2. Pourquoi la clé n'est-elle ni dans le code ni dans Git ? Que contiennent `.env` et `.env.example`, et lequel est commité ?
   Le code et Git sont partagés (GitHub, coéquipiers, forks) et l'historique Git est permanent :
   une clé commitée une seule fois y reste même après suppression du fichier, et il faut alors la
   changer. `.env` contient la **vraie** clé et les origines, propres à chaque poste ; il est exclu
   par le `.gitignore` et n'est jamais commité. `.env.example` est **commité** : il contient les
   mêmes variables avec de fausses valeurs (`changez-moi`) pour dire *quoi* configurer.
3. Pourquoi la clé voyage-t-elle dans un en-tête et pas dans l'URL ?
   Une URL est enregistrée partout : journaux du serveur et des proxys, historique et favoris du
   navigateur, en-tête `Referer`, copier-coller. La clé y fuirait. Un en-tête n'est pas journalisé
   par défaut, et il fonctionne pour toutes les méthodes, sans toucher au contrat de données.
4. Que fait `secrets.compare_digest` de plus qu'un simple `==` ?
   Il compare en **temps constant** : il parcourt toute la chaîne quelle que soit la position de la
   première différence. `==` s'arrête au premier caractère faux, donc la durée de réponse révèle
   combien de caractères étaient justes : un attaquant pourrait deviner la clé caractère par
   caractère (attaque temporelle).
5. Qu'est-ce qu'une « origine » ? `http://localhost:5500` et `http://localhost:8000` sont-elles la même origine ?
   Une origine est le triplet **schéma + domaine + port**. `http://localhost:5500` et
   `http://localhost:8000` ont le même schéma et le même domaine mais un port différent : ce sont
   **deux origines différentes**. La page doit donc être autorisée par CORS pour appeler l'API.

## 8. Le rendu Git

- Lien de la pull request : …
- Le tag `tp2` existe sur GitHub : oui / non
- `git status` avant le commit : le fichier `.env` apparaissait-il ? non (il est exclu par le `.gitignore`)
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  …

## 9. Ce qui reste flou

…
