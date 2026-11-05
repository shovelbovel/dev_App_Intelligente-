# ADR 003 · Sécurité de l'API : clé API et origines CORS

**Statut :** accepté · **Date :** 2026-11-05

## Contexte

L'API MaintAI ne doit répondre qu'aux programmes autorisés. Une page web servie sur
`http://localhost:5500` doit pouvoir l'appeler, une page servie ailleurs non. La clé ne doit
jamais apparaître dans le code ni dans Git.

## Décision 1 · Où transmettre la clé : dans l'en-tête `X-API-Key`

Chaque route `/v1` exige l'en-tête `X-API-Key`, comparé à `MAINTAI_API_KEY` avec
`secrets.compare_digest` (401 si absente ou fausse, 500 si le serveur n'en a pas).
`/health` reste public. La clé du serveur est lue dans `.env` (ignoré par Git) ;
`.env.example`, commité, ne contient qu'une fausse valeur.

| Option | Ce qu'elle ferait perdre |
|---|---|
| **en-tête** (retenu) | rien d'essentiel : il faut juste l'ajouter côté client |
| dans l'URL (`?key=...`) | la confidentialité : l'URL est enregistrée dans les journaux du serveur, des proxys et l'historique du navigateur, et peut être partagée par copier-coller |
| dans le corps JSON | la séparation des rôles : la clé se mélangerait au contrat de données (`extra="forbid"` la refuserait), ne marcherait pas pour les requêtes `GET` sans corps, et l'API devrait lire les données avant de vérifier qui appelle |

## Décision 2 · Quelles origines autoriser : une liste explicite, dans `.env`

`allow_origins` vient de `MAINTAI_CORS_ORIGINS` (par défaut
`http://localhost:5500,http://127.0.0.1:5500`), lue au démarrage. Seules les méthodes
`GET, POST` et les en-têtes `Content-Type, X-API-Key` sont permis.

| Option | Ce qu'elle ferait perdre |
|---|---|
| **liste dans `.env`** (retenu) | un peu de souplesse : ajouter une origine demande de redémarrer uvicorn |
| `*` (toutes les origines) | le contrôle : n'importe quelle page ouverte dans un navigateur pourrait appeler l'API depuis le poste d'un utilisateur |
| liste écrite dans le code | la configuration par environnement : changer d'origine (dev, production en séance 8) demanderait un commit |

## Conséquences

- CORS protège l'utilisateur d'un navigateur, pas l'API : `curl.exe`, Java ou Python ne
  passent pas par cette règle. La clé reste donc indispensable.
- Une clé commitée par erreur doit être changée (elle reste dans l'historique Git).
- La clé est partagée par tous les clients : pas d'autorisation fine (403) ni de révocation
  par client. À revoir si plusieurs clients doivent être distingués.
