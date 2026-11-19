# ADR 004 : modèle et seuil d'alerte retenus pour MaintAI

Date : [18/11/2026] temps : [12:00] · Auteurs : [hibatallah baetouty]

## Contexte

MaintAI doit prévenir avant qu'une machine tombe en panne. Les deux erreurs possibles ne coûtent
pas la même chose : une fausse alerte envoie un technicien pour rien, une panne manquée arrête la
production. Il faut donc choisir un modèle, mais aussi le seuil à partir duquel on déclenche une
alerte — deux décisions séparées, que les chiffres bruts d'accuracy ne permettent pas de trancher.

Quatre entraînements ont été enregistrés dans MLflow, tous sur la même version des données
(`data_md5 = 73e0b7cb3c6f795c70c3ddf970b99c15`, 4000 relevés d'entraînement, 1000 de test), ce qui
les rend comparables entre eux.

| Run | Réglages | recall | precision | accuracy |
|---|---|---|---|---|
| `d6f8e2f1` | logreg, C=1.0, seuil 0.3 | 0.750 | 0.622 | 0.904 |
| `032b9df2` | logreg, C=0.01, seuil 0.3 | 0.691 | 0.653 | 0.908 |
| `c661c909` | logreg, C=1.0, seuil 0.2 | 0.838 | 0.543 | 0.882 |
| `8caab819` | forest, seuil 0.3 | 0.728 | 0.562 | 0.886 |

La baseline, qui prédit toujours « pas de panne », obtient 0.864 d'accuracy et 0.0 de recall : elle
ne détecte aucune panne. C'est la preuve que l'accuracy seule est trompeuse sur ce problème.

## Options étudiées

1. **Régression logistique C=1.0, seuil 0.3** (le réglage par défaut) : recall 0.750, precision
   0.622. Compromis équilibré, mais laisse passer une panne sur quatre.
2. **Régression logistique C=0.01, seuil 0.3** : la meilleure accuracy (0.908) et la meilleure
   precision (0.653), mais le plus mauvais recall des quatre (0.691). La régularisation forte
   rend le modèle plus prudent, donc il alerte moins — exactement l'inverse de ce qu'on veut.
3. **Régression logistique C=1.0, seuil 0.2** : le meilleur recall (0.838), au prix d'une precision
   de 0.543. C'est le même modèle que l'option 1, seul le seuil de décision diffère.
4. **Forêt aléatoire, seuil 0.3** : recall 0.728, precision 0.562. Modèle beaucoup plus lourd et
   plus lent à entraîner, et il ne fait pas mieux que la régression logistique. Il perd sur les
   deux tableaux.

## Décision

Nous retenons l'**option 3** : régression logistique avec `C = 1.0` et un seuil d'alerte à **0.2**.

- Run MLflow : `c661c909a61249ad9b14b366410e4556`
- Version des données : `data_md5 = 73e0b7cb3c6f795c70c3ddf970b99c15` (v1, commit `bc0f0a4`)
- Commande : `python -m maintai.train --threshold 0.2`

La raison est la contrainte métier : une panne manquée coûte plus cher qu'une fausse alerte. Ce run
détecte 84 % des pannes là où le réglage par défaut en détecte 75 % — soit environ 9 pannes
rattrapées sur 100. Sa precision descend à 0.543, donc un peu moins d'une alerte sur deux est une
fausse alerte, ce que nous acceptons tant qu'un déplacement de technicien reste bien moins coûteux
qu'un arrêt de production.

Nous écartons l'option 2 malgré sa meilleure accuracy : sur des données où seules 13 % des machines
tombent en panne, l'accuracy récompense surtout le fait de ne rien prédire. La baseline le montre
bien avec ses 0.864.

Nous écartons l'option 4 parce que la forêt aléatoire n'apporte rien ici : des performances égales
ou inférieures, pour un modèle plus lourd, plus lent et plus difficile à expliquer à un
responsable de maintenance.

## Conséquences

**Ce que cela facilite.** Le modèle reste une régression logistique : rapide à entraîner, léger à
charger dans l'API, et dont on peut lire les coefficients pour expliquer une alerte. Surtout, le
seuil est un simple paramètre, lu depuis `MAINTAI_THRESHOLD` dans `maintai/config.py`. S'il faut
ajuster le niveau d'alerte après quelques semaines d'exploitation, on change une variable
d'environnement — aucun réentraînement, aucun redéploiement du modèle.

**Ce que cela rend plus difficile.** Avec une precision de 0.543, l'équipe de maintenance recevra
beaucoup de fausses alertes. Si elle finit par ne plus les prendre au sérieux, le gain en recall
disparaît. Il faudra accompagner la mise en service et expliquer ce choix aux utilisateurs.

**Ce qu'il faudra surveiller.**

- Le ressenti de l'équipe sur le volume de fausses alertes. Si c'est intenable, remonter le seuil à
  0.25 et mesurer le recall qu'on perd.
- La dérive des données : ces chiffres valent pour la version `73e0b7cb…`. Un run entraîné sur la
  v2 (`93fdeef2…`) a donné un recall de 0.741, mais sur un autre jeu de test — ce n'est donc pas
  comparable directement, et cela ne remet pas en cause la décision.
- Le vrai coût des deux erreurs. Nous avons supposé qu'une panne manquée coûte beaucoup plus cher
  qu'une fausse alerte. Si la maintenance chiffre ces deux coûts, le seuil devra être recalculé à
  partir de ces chiffres plutôt que choisi à la main.

Toute révision de cette décision devra repartir de runs entraînés sur la **même** version des
données, vérifiable par leur `data_md5` dans MLflow.
