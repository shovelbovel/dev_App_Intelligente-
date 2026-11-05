# Compte rendu · TP2 : tester, sécuriser et appeler l'API MaintAI

**Groupe :*G1*  ·  **Membres :*HIBATALLAH BAETOUTY*   ·  **Date :** 05/11/2026 REALISER EN BINOME AVEC ABDELALI SAHIA

---

## 1. Activité 1 : casser son API (dans `TP/TP1`)

Voici nos cinq requêtes, avec le code que nous avions **prévu** et le code **obtenu** dans `/docs` :

| Requête | Ce qui ne va pas | Code prévu | Code obtenu |
|---|---|---|---|
| 1 : `POST /v1/predict` avec `{"temperature_c": 60, "vibration_mm_s": 2, "runtime_hours": 5000}` | champ manquant | 422 | 422 |
| 2 : `POST /v1/predict` avec `{"temperature_c": 500, "vibration_mm_s": 2, "load_pct": 50, "runtime_hours": 5000}` | valeur absurde | 422 | 422 |
| 3 : `POST /v1/predict` avec `{"temperature_c": 60, "vibration_mm_s": 2, "load_pct": "beaucoup", "runtime_hours": 5000}` | texte au lieu d'un nombre | 422 | 422 |
| 4 : `POST /v1/predict` avec `{"temperature_c": 60, "vibration_mm_s": 2, "load_pct": 50, "runtime_hours": 5000, "couleur": "rouge"}` | champ en trop | 422 | 422 |
| 5 : `POST /v1/predire` avec un corps valide | mauvaise route | 404 | 404 |

Une de vos prévisions était-elle fausse ? Laquelle, et pourquoi ?

Non, nos cinq prévisions étaient justes. Les quatre premières requêtes arrivent sur une route qui existe, mais le schéma Pydantic les refuse, d'où le code 422. La cinquième vise une route qui n'existe pas, donc l'API répond 404 sans même regarder le corps.

Dernière ligne de `python -m pytest` avec `tests/test_casser.py` (dans `TP/TP1`) :

```
======================== 19 passed, 1 warning in 2.52s ========================
```

À quoi sert `@pytest.mark.parametrize` ? Combien de tests pytest compte-t-il pour votre fonction, et pourquoi ?

`@pytest.mark.parametrize` lance la même fonction de test avec plusieurs jeux de données, sans recopier le code. pytest compte 5 tests pour `test_requete_refusee`, un par ligne de `CAS_REFUSES`. Chaque cas réussit ou échoue séparément, donc on voit tout de suite lequel pose problème.

## 2. ruff

Sortie de `ruff check .` dans `TP/TP1` :

```
UP017 [*] Use `datetime.UTC` alias
  --> maintai\train.py:58:36
   |
56 |         "target": TARGET,
57 |         "threshold": settings.threshold,
58 |         "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
   |                                    ^^^^^^^^^^^^
59 |         "sklearn_version": sklearn.__version__,
60 |     }
   |
help: Convert to `datetime.UTC` alias
   |
5  | import json
   - from datetime import datetime, timezone
6  + from datetime import datetime, timezone, UTC
7  |
--------------------------------------------------------------------------------
57 |         "threshold": settings.threshold,
   -         "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
58 +         "trained_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
59 |         "sklearn_version": sklearn.__version__,
   |

I001 [*] Import block is un-sorted or un-formatted
 --> tests\test_casser.py:1:1
  |
1 | import pytest
  | ^^^^^^^^^^^^^
2 | HEADERS = {"X-API-Key": "test-key"} # la clé des tests (conftest.py) ; inutile en TP1, nécessaire enTP2
3 | VALID = {"temperature_c": 60.0, "vibration_mm_s": 2.0, "load_pct": 50.0, "runtime_hours": 5000}
  |
help: Organize imports
  |
1 | import pytest
2 +
3 | HEADERS = {"X-API-Key": "test-key"} # la clé des tests (conftest.py) ; inutile en TP1, nécessaire enTP2
  |

Found 2 errors.
[*] 2 fixable with `--fix`.
```

Après `ruff check --fix`, nouvelle sortie de `ruff check .` :

```
All checks passed!
```

Quelle différence entre `ruff check .` et `python -m pytest` ? Que vérifie chacun ?

`ruff check .` lit le code sans l'exécuter. Il cherche les problèmes de style et les erreurs probables, comme des imports mal rangés ou une écriture dépassée. `python -m pytest` exécute le code et vérifie qu'il se comporte comme prévu. Un code peut donc passer tous les tests et être quand même signalé par ruff, comme ici, et l'inverse est vrai aussi.

## 3. Mise en place du TP2 (dans `TP/TP2`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
2 failed, 16 passed, 1 warning in 1.07s
```

Quels sont les deux tests qui échouent, et que reçoivent-ils au lieu de 401 ?

Les deux tests qui échouent sont `test_missing_key_is_rejected` et `test_wrong_key_is_rejected`. Ils reçoivent 200 au lieu de 401. Au départ, la route `/v1/predict` n'est pas protégée, donc elle répond normalement, même sans clé ou avec une fausse clé.

## 4. La clé API (sprint 1)

Notre fonction `require_api_key()` (`maintai/api/security.py`) :

```python
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Refuse la requête si la clé est absente ou fausse."""
    expected = get_settings().api_key
    if expected is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clé API du serveur non configurée : lancez uvicorn avec --env-file .env",
        )
    # compare_digest prend le même temps quelle que soit la position de l'erreur.
    # En bytes, car il refuse les chaînes non ASCII, et un client peut en envoyer.
    if x_api_key is None or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API absente ou invalide",
        )
```

Notre ligne `router = ...` dans `maintai/api/main.py` :

```python
router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])
```

Après avoir écrit `security.py` seul (sans toucher au router), combien de tests échouent ? Pourquoi ?

Les deux mêmes tests échouent encore. La fonction existe, mais aucune route ne l'appelle, donc la vérification de la clé ne s'exécute jamais. Il faut l'ajouter au router pour qu'elle serve à quelque chose.

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
18 passed, 1 warning in 0.94s
```

Requêtes envoyées après `uvicorn maintai.api.main:app --reload --env-file .env` :

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health`, sans clé | 200 | `{"status":"ok","model_loaded":true}` |
| `POST /v1/predict`, relevé normal, sans clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, relevé normal, fausse clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, relevé normal, bonne clé | 200 | `{"failure_probability":0.0027,"alert":false,"threshold":0.3,"model_version":"2026-11-05T11:50:51Z"}` |
| `POST /v1/predict`, 500 °C, sans clé | 401 | `{"detail":"Clé API absente ou invalide"}` |
| `POST /v1/predict`, 500 °C, bonne clé | 422 | `{"detail":[{"type":"less_than_equal","loc":["body","temperature_c"],"msg":"Input should be less than or equal to 150","input":500,"ctx":{"le":150.0}}]}` |

500 °C sans clé et 500 °C avec la clé ne donnent pas le même code. Pourquoi ?

La clé est vérifiée avant les données. Sans clé, la requête s'arrête tout de suite avec un 401, et la température n'est jamais contrôlée. Avec la bonne clé, la requête passe cette étape, puis Pydantic voit que 500 dépasse 150 et répond 422.

Relancez uvicorn **sans** `--env-file .env` et envoyez un relevé avec votre clé. Quel code obtenez-vous, et pourquoi ce n'est pas 401 ?

Nous obtenons 500, avec le message « Clé API du serveur non configurée ». Ce n'est pas 401 parce que le client n'a rien fait de mal : c'est le serveur qui n'a pas de clé à comparer. L'erreur vient donc du serveur et non du client.

## 5. La page web (sprint 2)

Notre code `fetch` (le contenu du `addEventListener` dans `web/index.html`) :

```javascript
const reading = Object.fromEntries(FEATURES.map(f => [f, Number(document.getElementById(f).value)]));
const adresse = document.getElementById("url").value.replace(/\/+$/, "") + "/v1/predict";
const cle = document.getElementById("key").value;
try {
  const resp = await fetch(adresse, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": cle },
    body: JSON.stringify(reading),
  });
  const data = await resp.json();
  if (!resp.ok) {
    // 401, 503 : detail est un texte ; 422 : une liste d'erreurs
    const detail = Array.isArray(data.detail) ? data.detail.map(formatErreur).join("\n") : data.detail;
    show("err", `Erreur ${resp.status} : ${detail}`);
    return;
  }
  const proba = (data.failure_probability * 100).toFixed(1);
  if (data.alert) {
    show("alert", `ALERTE : probabilité de panne ${proba} %`);
  } else {
    show("ok", `Pas d'alerte : probabilité de panne ${proba} %`);
  }
} catch (e) {
  show("err", "API injoignable : uvicorn est arrêté, ou CORS bloque cette origine (voir F12)");
}
```

Nous avons ajouté la fonction `formatErreur` pour que les erreurs 422 s'affichent sous la forme d'un code et d'une explication, et non en JSON brut.

Ce qu'affiche la page (servie sur le port 5500), avec les valeurs par défaut du formulaire (72 °C, 6 mm/s, 85 %, 15 000 h) :

| Essai | Ce qu'affiche la page |
|---|---|
| relevé normal, bonne clé | `ALERTE : probabilité de panne 94.8 %` |
| 500 °C, bonne clé | `Erreur 422 : Température 500 dépasse le maximum autorisé (150)` |
| relevé normal, fausse clé | `Erreur 401 : Clé API absente ou invalide` |

**Expérience CORS.** Servez la page sur le port 5501. Que dit la page, et que dit la console (F12) ?

La page affiche : « API injoignable : uvicorn est arrêté, ou CORS bloque cette origine (voir F12) ». L'API refuse en effet le port 5501 : sa réponse à la demande préalable du navigateur est un 400, sans en-tête `access-control-allow-origin`.

La console indique :

```
(collez ici le message de la console F12)
```

Pourquoi `curl.exe` obtient-il une réponse alors que la page du port 5501 est bloquée ?

Le CORS est une protection du navigateur, pas du serveur. Le navigateur demande à l'API si l'origine est autorisée et bloque la réponse si ce n'est pas le cas. `curl.exe` ne fait pas cette vérification : même avec l'origine `http://localhost:5501`, il reçoit bien un 200. Le CORS ne remplace donc pas la clé API.

## 6. Les tests de l'activité 1 dans le TP2

Copiez `test_casser.py` dans `TP/TP2/tests`. Sans `headers=HEADERS`, combien de tests échouent, et avec quel code ? Lequel des cinq cas passe quand même, et pourquoi ?

Quatre tests échouent, car ils reçoivent 401 au lieu de 422 : sans clé, la requête est refusée avant le contrôle des données. Le cas qui passe quand même est « mauvaise adresse » (`/v1/predicte`). Cette route n'existe pas, donc l'API répond 404 avant toute vérification de clé, et c'est le code attendu.

Dernière ligne de `python -m pytest` avec `headers=HEADERS` :

```
23 passed, 1 warning in 1.57s
```

## 7. Questions de compréhension

1. Quelle différence entre 401 et 422 ? Et entre 401 et 403 ?

   Le code 401 veut dire que le client n'est pas identifié, parce que sa clé est absente ou fausse. Le code 422 veut dire que le client est bien passé, mais que ses données ne sont pas valides. Le code 403 veut dire que le client est identifié, mais qu'il n'a pas le droit de faire cette action.

2. Pourquoi la clé n'est-elle ni dans le code ni dans Git ? Que contiennent `.env` et `.env.example`, et lequel est commité ?

   Tout ce qui est dans Git reste dans l'historique et peut être lu par ceux qui ont accès au dépôt, donc une clé qui s'y trouve n'est plus secrète. Le fichier `.env` contient la vraie clé et il n'est pas commité, car il est dans `.gitignore`. Le fichier `.env.example` contient seulement des valeurs d'exemple pour montrer quoi remplir, et c'est lui qui est commité.

3. Pourquoi la clé voyage-t-elle dans un en-tête et pas dans l'URL ?

   Les URL sont souvent enregistrées, par exemple dans l'historique du navigateur et dans les journaux des serveurs. Une clé placée dans l'URL pourrait donc se retrouver visible à plusieurs endroits. Dans un en-tête, elle est beaucoup moins exposée.

4. Que fait `secrets.compare_digest` de plus qu'un simple `==` ?

   `==` s'arrête au premier caractère différent, donc la comparaison prend plus ou moins de temps selon la clé essayée. Un attaquant pourrait mesurer ce temps pour deviner la clé petit à petit. `secrets.compare_digest` prend le même temps quelle que soit la position de l'erreur, ce qui empêche cette attaque.

5. Qu'est-ce qu'une « origine » ? `http://localhost:5500` et `http://localhost:8000` sont-elles la même origine ?

   Une origine est la combinaison du protocole, du nom d'hôte et du port. `http://localhost:5500` et `http://localhost:8000` ne sont pas la même origine, car leurs ports sont différents. C'est pour cela que l'API doit autoriser explicitement le port 5500 avec le CORS.

## 8. Le rendu Git

- Lien de la pull request : …
- Le tag `tp2` existe sur GitHub : oui / non
- `git status` avant le commit : le fichier `.env` apparaissait-il ? oui / non
- Qui a relu la pull request, et quel commentaire a-t-il laissé ?
  …

## 9. Ce qui reste flou

…
