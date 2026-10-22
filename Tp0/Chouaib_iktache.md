# Rapport : CantineAI et MaintAI
**Nom :** IKTACHE Chouaib · **Groupe :** G1

# 1. CantineAI

## Le problème
Prévoir le nombre de repas servis chaque jour à la cantine, pour préparer la bonne quantité et limiter le gaspillage.



## Résultats sur le jeu de test
| Modèle | MAE | RMSE | R² |
|---|---|---|---|
| ridge | **22.6** | 28.5 | 0.880 |
| gradient boosting | 29.9 | 37.7 | 0.790 |
| forêt aléatoire | 31.8 | 41.6 | 0.745 |
| knn | 38.4 | 48.2 | 0.657 |
| arbre de décision | 42.0 | 54.8 | 0.558 |
| baseline | 70.3 | 88.4 | -0.151 |

Meilleur modèle selon la MAE : **ridge**, environ 23 repas d'erreur par jour, soit 3 fois moins que la baseline (70).

## Mon choix, et pourquoi
Ridge : la plus petite MAE (22.6) et le meilleur R² (0.88), et c'est un modèle simple et rapide.

## Le critère est-il atteint ?
Oui si le critère est une MAE < 30 repas : ridge obtient 22.6, environ 3 fois mieux que la baseline.

## Ce qui reste flou
Le seuil d'acceptation reste à fixer avec la cantine. Le test ne couvre que 68 jours (fin d'année scolaire).

# 2. MaintAI (exemple pannes)

## Le problème
Prédire une panne à partir de 4 capteurs ; une panne manquée arrête une ligne.

## Exemple pannes : résultats du projet


| Modèle | Accuracy | Rappel | Précision | F1 |
|---|---|---|---|---|
| régression logistique | 0.839 | **0.847** | 0.527 | 0.649 |
| forêt aléatoire | 0.844 | 0.767 | 0.540 | 0.634 |
| arbre de décision | 0.825 | 0.722 | 0.502 | 0.592 |
| gradient boosting | 0.888 | 0.608 | 0.713 | 0.656 |
| knn | 0.890 | 0.517 | 0.784 | 0.623 |
| baseline | 0.824 | 0.000 | 0.000 | 0.000 |

Meilleur modèle selon le rappel : **régression logistique** (rappel = 0.847).

## Résultats sur le jeu de test
| Modèle | Accuracy | Rappel | Précision |
|---|---|---|---|
| baseline | 0.824 | 0.000 | 0.000 |
| régression logistique | 0.889 | 0.574 | 0.737 |

## Mon choix, et pourquoi
Régression logistique : le meilleur rappel (0.847). Une panne manquée coûte plus cher qu'une fausse alerte.

## Le critère (rappel >= 0,75) est-il atteint ?
Oui : rappel = 0.847 > 0.75.

## Ce qui reste flou
La précision est faible (0.527) : près d'une alerte sur deux est fausse. Le premier tableau (rappel 0.574) ne correspond pas aux résultats actuels.
