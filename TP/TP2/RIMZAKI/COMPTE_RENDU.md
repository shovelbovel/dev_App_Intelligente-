# Compte rendu · TP2 : tester, sécuriser et appeler l'API MaintAI

 **Membres :** ZAKI Rim  ·  **Date :** 05/11/2026

> Remplissez chaque partie dans ce fichier, puis rendez-le avec la pull request du TP2.
> Collez les sorties du terminal entre les lignes ``` (trois accents graves).

---

## 1. Activité 1 : casser son API (dans `TP/TP1`)

Vos cinq requêtes, le code que vous aviez **prévu**, puis le code **obtenu** dans `/docs` :

| Requête | Ce qui ne va pas | Code prévu | Code obtenu |
|---|---|---|---|
| 1 | champ manquant : `load_pct` absent | 422 | 422 |
| 2 | valeur absurde : `load_pct` = 250 | 422 | 422 |
| 3 | texte au lieu d'un nombre : `temperature_c` = `"chaud"` | 422 | 422 |
| 4 | champ en trop : `"couleur": "rouge"` | 422 | 422 |
| 5 | mauvaise route : `POST /v1/predicte` | 404 | 404 |

Une de vos prévisions était-elle fausse ? Laquelle, et pourquoi ?

Aucune de mes prévisions n'était fausse, mais deux pièges existent. Pour le cas 3, une chaîne qui ressemble à un nombre (`"72.5"`) est convertie automatiquement par Pydantic et donne **200** au lieu de 422 ; il faut un vrai texte comme `"chaud"`. Pour le cas 5, un `GET` sur `/v1/predict` (au lieu d'un `POST` sur une adresse inexistante) donne **405** (méthode non autorisée) et non 404.

Dernière ligne de `python -m pytest` avec `tests/test_casser.py` (dans `TP/TP1`) :

```
======================== 19 passed, 1 warning in 1.71s =========================
```

À quoi sert `@pytest.mark.parametrize` ? Combien de tests pytest compte-t-il pour votre fonction, et pourquoi ?

`@pytest.mark.parametrize` permet d'écrire la fonction de test une seule fois et de la faire tourner sur chaque ligne d'une liste de cas. Pytest compte **5 tests** pour `test_requete_refusee`, un par cas de `CAS_REFUSES`. Chaque cas est indépendant : si l'un échoue, les autres s'exécutent quand même et le rapport indique lequel a échoué.

## 2. ruff

Sortie de `ruff check .` dans `TP/TP1` :

```
demofastapi.py:1:1: I001 [*] Import block is un-sorted or un-formatted
maintai/api/schemas.py:21:5: PIE790 [*] Unnecessary `pass` statement
maintai/train.py:58:36: UP017 [*] Use `datetime.UTC` alias
Found 3 errors.
[*] 3 fixable with `--fix`.
```

Quelle différence entre `ruff check .` et `python -m pytest` ? Que vérifie chacun ?

`ruff check .` est un **linter** : il lit le code **sans l'exécuter** et repère les problèmes de style et de qualité (imports mal triés, `pass` inutile, syntaxe dépréciée). `python -m pytest` **exécute** le code via les tests et vérifie son **comportement** (bons codes de réponse, bonnes valeurs). Un code peut passer tous les tests et avoir des défauts de style, et inversement. Ces trois erreurs se corrigent avec `ruff check . --fix`.

## 3. Mise en place du TP2 (dans `TP/TP2`)

Dernière ligne de `python -m pytest` juste après la mise en place :

```
======================== 2 failed, 16 passed, 1 warning in 1.41s ========================
```

Quels sont les deux tests qui échouent, et que reçoivent-ils au lieu de 401 ?

Ce sont `test_missing_key_is_rejected` (requête sans clé) et `test_wrong_key_is_rejected` (requête avec la clé `"wrong"`), dans `tests/test_security.py`. Ils reçoivent **200** au lieu de 401, car l'API n'est pas encore protégée : elle répond à tout le monde.

## 4. La clé API (sprint 1)

Votre fonction `require_api_key()` (`maintai/api/security.py`) :

```python
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Refuse la requête si la clé est absente ou fausse."""
    settings = get_settings()
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clé API non configurée",
        )

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API requise",
        )

    if not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API incorrecte",
        )
```

Votre ligne `router = ...` dans `maintai/api/main.py` :

```python
router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])
```

Après avoir écrit `security.py` seul (sans toucher au router), combien de tests échouent ? Pourquoi ?

**2 tests** échouent encore (les deux tests de `test_security.py` qui attendent un 401 et reçoivent toujours 200). La fonction existe, mais personne ne l'appelle : tant que le router ne déclare pas `dependencies=[Depends(require_api_key)]`, FastAPI ne l'exécute pas.

Dernière ligne de `python -m pytest` à la fin du sprint 1 :

```
======================== 18 passed, 1 warning in 1.36s ========================
```

Lancez `uvicorn maintai.api.main:app --reload --env-file .env`, puis envoyez ces requêtes (avec `/docs` ou `curl.exe`) :

| Requête | Code obtenu | Réponse (le corps JSON) |
|---|---|---|
| `GET /health`, sans clé | 200 | `{"status":"ok","model_loaded":true}` |
| `POST /v1/predict`, relevé normal, sans clé | 401 | `{"detail":"Clé API requise"}` |
| `POST /v1/predict`, relevé normal, fausse clé | 401 | `{"detail":"Clé API incorrecte"}` |
| `POST /v1/predict`, relevé normal, bonne clé | 200 | `{"failure_probability":0.9553,"alert":true,"threshold":0.3,"model_version":"2026-11-05T11:34:10Z"}` |
| `POST /v1/predict`, 500 °C, sans clé | 401 | `{"detail":"Clé API requise"}` |
| `POST /v1/predict`, 500 °C, bonne clé | 422 | `{"detail":[{"type":"less_than_equal","loc":["body","temperature_c"],"msg":"Input should be less than or equal to 150","input":500,"ctx":{"le":150.0}}]}` |

500 °C sans clé et 500 °C avec la clé ne donnent pas le même code. Pourquoi ?

Le contrôle de la clé passe **avant** la validation du corps de la requête. Sans clé, FastAPI s'arrête au 401 et ne regarde jamais la température. Avec la bonne clé, l'authentification réussit, puis Pydantic examine le corps et refuse 500 °C (limite 150) : 422. Le 401 répond à « qui es-tu ? », le 422 à « ta requête est-elle valable ? ».

Relancez uvicorn **sans** `--env-file .env` et envoyez un relevé avec votre clé. Quel code obtenez-vous, et pourquoi ce n'est pas 401 ?

J'obtiens **500** avec `{"detail":"Clé API non configurée"}`. Sans `--env-file`, la variable `MAINTAI_API_KEY` n'existe pas dans l'environnement du serveur, donc `get_settings().api_key` vaut `None`. Le client n'a rien fait de mal : c'est le serveur qui est mal configuré, donc une erreur 5xx et non 401 (qui désigne une faute du client). Le serveur refuse d'ailleurs tout le monde, même avec la bonne clé, au lieu de laisser l'API ouverte.

## 5. La page web (sprint 2)

Votre code `fetch` (le contenu du `addEventListener` dans `web/index.html`) :

```javascript
const reading = Object.fromEntries(FEATURES.map(f => [f, Number(document.getElementById(f).value)]));
const base = document.getElementById("url").value.replace(/\/$/, "");
const key = document.getElementById("key").value;
try {
  const r = await fetch(base + "/v1/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": key },
    body: JSON.stringify(reading),
  });
  if (r.ok) {
    const data = await r.json();
    const pct = (data.failure_probability * 100).toFixed(1);
    show(data.alert ? "alert" : "ok",
      (data.alert ? "ALERTE : " : "OK : ") + "probabilité de panne " + pct + " %");
  } else if (r.status === 401) {
    show("err", "Clé API refusée (401)");
  } else if (r.status === 422) {
    show("err", "Valeurs refusées (422) : vérifiez les bornes");
  } else {
    show("err", "Erreur du serveur (" + r.status + ")");
  }
} catch (e) {
  show("err", "Impossible de joindre l'API : serveur éteint ou requête bloquée (CORS)");
}
```

Ce qu'affiche la page (servie sur le port 5500) :

| Essai | Ce qu'affiche la page |
|---|---|
| relevé normal, bonne clé | `ALERTE : probabilité de panne 94.8 %` (valeurs par défaut de la page : 72 °C, 6 mm/s, 85 %, 15000 h) |
| 500 °C, bonne clé | `Valeurs refusées (422) : vérifiez les bornes` |
| relevé normal, fausse clé | `Clé API refusée (401)` |

**Expérience CORS.** Servez la page sur le port 5501. Que dit la page, et que dit la console (F12) ?

La page affiche `Impossible de joindre l'API : serveur éteint ou requête bloquée (CORS)`. La console affiche une erreur du type : `Access to fetch at 'http://localhost:8000/v1/predict' from origin 'http://localhost:5501' has been blocked by CORS policy: ... No 'Access-Control-Allow-Origin' header is present on the requested resource` (le texte exact varie selon le navigateur). Le serveur n'autorise que les origines de `MAINTAI_CORS_ORIGINS` (ports 5500) : pour la pré-vérification (`OPTIONS`) venant de 5501, il répond `400 Disallowed CORS origin`, sans l'en-tête `Access-Control-Allow-Origin`.

Pourquoi `curl.exe` obtient-il une réponse alors que la page du port 5501 est bloquée ?

La règle CORS est appliquée par le **navigateur**, pas par le serveur. Le serveur répond bien (200 à un `POST` valide, même avec `Origin: http://localhost:5501`), mais le navigateur refuse de transmettre la réponse à la page si l'en-tête `Access-Control-Allow-Origin` ne l'autorise pas. `curl.exe` n'est pas un navigateur : il n'applique aucune règle CORS.

## 6. Les tests de l'activité 1 dans le TP2

Copiez `test_casser.py` dans `TP/TP2/tests`. Sans `headers=HEADERS`, combien de tests échouent, et avec quel code ? Lequel des cinq cas passe quand même, et pourquoi ?

**4 tests échouent** sur 5 : ils reçoivent **401** au lieu de 422, car la clé manque et le contrôle de la clé passe avant la validation. Le cas qui passe quand même est **« mauvaise route »** : `/v1/predicte` n'existe pas, donc FastAPI répond 404 sans jamais atteindre le router protégé ni sa dépendance.

Dernière ligne de `python -m pytest` avec `headers=HEADERS` :

```
======================== 23 passed, 1 warning in 1.41s ========================
```

## 7. Questions de compréhension

1. Quelle différence entre 401 et 422 ? Et entre 401 et 403 ?
   **401** signifie « non authentifié » : la clé est absente ou invalide, le serveur ne sait pas qui appelle. **422** signifie que la requête est mal formée ou contient des valeurs invalides (champ manquant, 500 °C) : c'est la validation du contenu. **403** signifie que l'identité est connue mais n'a pas le droit d'accéder à la ressource ; **401** signifie que l'identité n'est pas prouvée.
2. Pourquoi la clé n'est-elle ni dans le code ni dans Git ? Que contiennent `.env` et `.env.example`, et lequel est commité ?
   Git conserve tout l'historique et le dépôt est partagé : une clé commitée est visible de tous ceux qui ont accès au dépôt, même après suppression. `.env` contient la vraie clé (`MAINTAI_API_KEY`) et les origines CORS, et n'est **pas** commité (il est dans `.gitignore`). `.env.example` est un modèle avec les mêmes variables et des valeurs d'exemple, et c'est lui qui est commité pour montrer ce qu'il faut configurer.
3. Pourquoi la clé voyage-t-elle dans un en-tête et pas dans l'URL ?
   Les URL sont enregistrées dans l'historique du navigateur, les journaux des serveurs et des proxys, et peuvent apparaître dans l'en-tête `Referer`. Un en-tête n'est pas conservé de cette façon, donc la clé y est moins exposée.
4. Que fait `secrets.compare_digest` de plus qu'un simple `==` ?
   Il compare en **temps constant**, quel que soit l'endroit où les deux chaînes diffèrent. Un `==` s'arrête au premier caractère différent, ce qui permet à un attaquant de deviner la clé caractère par caractère en mesurant les temps de réponse (attaque par chronométrage).
5. Qu'est-ce qu'une « origine » ? `http://localhost:5500` et `http://localhost:8000` sont-elles la même origine ?
   Une origine est le triplet **schéma + hôte + port**. Non, ces deux adresses n'ont pas la même origine, car les ports (5500 et 8000) diffèrent : le navigateur applique donc la règle CORS entre la page et l'API.
