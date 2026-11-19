# ADR 004 : choix du modèle et du seuil d'alerte

Date : 19/11/2026 · Auteurs : SAHIA ABDELALI (G1)

## Contexte
MaintAI doit signaler les machines qui vont tomber en panne. Une panne manquée coûte plus cher qu'une fausse alerte : le critère principal est donc le **recall**, la précision vient ensuite.

Cinq entraînements ont été suivis dans MLflow (expérience `maintai`), tous sur la même version des données : `data_md5` = `73e0b7cb3c6f795c70c3ddf970b99c15` (5 000 relevés, 13,6 % de pannes ; 4 000 pour l'entraînement, 1 000 pour le test, dont 136 pannes). Les runs sont donc directement comparables.

## Options étudiées

| Option | Run MLflow | recall | precision | accuracy | Pannes manquées (sur 136) | Fausses alertes |
|---|---|---|---|---|---|---|
| A. Régression logistique, C = 1.0, seuil 0.3 (défaut) | `4a77376c` | 0.750 | 0.622 | 0.904 | 34 | 62 |
| B. Régression logistique, C = 0.01, seuil 0.3 | `72222c34` | 0.691 | 0.653 | 0.908 | 42 | 50 |
| C. Régression logistique, C = 1.0, seuil 0.2 | `e8edbce3` | **0.838** | 0.543 | 0.882 | **22** | 96 |
| D. Forêt aléatoire (200 arbres), seuil 0.3 | `c971aa35` | 0.728 | 0.562 | 0.886 | 37 | 77 |
| E. Forêt aléatoire (200 arbres), seuil 0.2 | `b4df8d53` | 0.831 | 0.479 | 0.854 | 23 | 123 |
| Baseline (toujours « pas de panne ») | | 0.000 | | 0.864 | 136 | 0 |

1. **A, réglage par défaut** : bon compromis, peu de fausses alertes ; mais une panne sur quatre passe inaperçue.
2. **B, régularisation forte** : meilleures précision et accuracy ; mais le plus faible recall, avec 42 pannes manquées. Il optimise le mauvais critère.
3. **C, seuil abaissé à 0.2** : meilleur recall, avec 22 pannes manquées ; mais 96 fausses alertes, soit à peu près une alerte sur deux (précision 0.543).
4. **D, forêt aléatoire** : modèle plus lourd et moins interprétable, et moins bon que A sur les trois métriques au même seuil.
5. **E, forêt au seuil 0.2** : recall proche de C (23 pannes manquées) ; mais 123 fausses alertes, et moins bon que C sur les trois métriques.

L'accuracy ne départage pas les options : la baseline, qui ne détecte aucune panne, atteint déjà 0.864.

## Décision
**Option C : régression logistique, C = 1.0, seuil d'alerte 0.2.**

- Run MLflow : `e8edbce38b04411898929d27fb75cc93`
- Version des données : `data_md5` = `73e0b7cb3c6f795c70c3ddf970b99c15`

C'est le run qui manque le moins de pannes. Par rapport au réglage par défaut, il détecte 12 pannes de plus (22 manquées au lieu de 34) au prix de 34 fausses alertes de plus. Comme une panne manquée coûte plus cher qu'une fausse alerte, cet échange est favorable. Le seuil compte ici plus que le modèle : le passer de 0.3 à 0.2 améliore davantage le recall que changer de régularisation ou de modèle.

## Conséquences
- **Ce qui est facilité** : moins de pannes non détectées ; un modèle simple, rapide et interprétable (coefficients de la régression) ; une décision traçable, puisque le run, l'empreinte des données et les versions des bibliothèques sont enregistrés dans MLflow.
- **Ce qui est plus difficile** : environ une alerte sur deux est fausse. Il faut que l'équipe de maintenance accepte ce volume d'interventions inutiles, sinon elle risque d'ignorer les alertes.
- **Mise en œuvre** : le même réglage a été réentraîné sur la v1 (run `09ae1122`, mêmes métriques que `e8edbce3`), puis sur la v2 des données (`data_md5` = `93fdeef2cac1893c4f720c16457eea75`, run `1928a9e0a8f04c57b3668b41e5034660` : recall 0.824, précision 0.567). C'est ce dernier modèle qui est dans `models/`. Le seuil 0.2 est écrit dans `model_info.json`, que l'API lit.
- **À surveiller** :
  - Le seuil a été choisi sur le jeu de test : il faudrait le confirmer sur des données qui n'ont pas servi au choix.
  - Avec 136 pannes en test, une panne pèse 0,7 point de recall, donc de petits écarts entre runs restent fragiles.
  - Ces résultats ne valent que pour cette version des données, qui sont synthétiques. À chaque nouvelle version DVC, il faut refaire les runs et ne comparer que des runs ayant le même `data_md5`.
