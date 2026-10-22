# TP0 : MaintAI
**Nom :** Prénom Nom · **Groupe :** G3

## Le problème
Prédire une panne à partir de 4 capteurs. Si on rate une panne, la ligne s'arrête.

## Résultats sur le jeu de test
| Modèle | Accuracy | Rappel | Précision |
|-|-|-|-|
| baseline | 0.824 | 0.000 | 0.000 |
| régression logistique | 0.839 | 0.847 | 0.527 |
| arbre de décision | 0.825 | 0.722 | 0.502 |
| forêt aléatoire | 0.882 | 0.540 | 0.720 |
| k plus proches voisins | 0.878 | 0.540 | 0.699 |

## Mon choix, et pourquoi
Je choisis la régression logistique, parce qu'elle trouve le plus de pannes (85 %).

L'accuracy ne suffit pas : la baseline a 82 % mais ne trouve aucune panne. Le plus important ici, c'est le rappel.

## Le critère (rappel >= 0,75) est-il atteint ?
Oui : la régression logistique a un rappel de 0,847.

Elle fait des fausses alertes (une sur deux), mais c'est moins grave que de rater une panne.

## Ce qui reste flou
- J'ai testé avec un seul découpage des données.
- Je n'ai pas essayé de changer le seuil de 0,5.
- Je ne connais pas le coût d'une fausse alerte.

---

# TP0 : Cantine
**Nom :** Prénom Nom · **Groupe :** G3

## Le problème
Prédire le nombre de repas servis chaque jour avec 2 capteurs : la température et la pluie.

## Résultats sur le jeu de test
| Modèle | MAE (repas) | RMSE | R² |
|-|-|-|-|
| baseline (moyenne) | 70.271 | 88.416 | -0.151 |
| régression linéaire | 69.622 | 86.813 | -0.110 |
| arbre de décision | 83.626 | 107.376 | -0.698 |
| forêt aléatoire | 78.566 | 101.139 | -0.506 |
| k plus proches voisins | 72.638 | 91.000 | -0.219 |

## Mon choix, et pourquoi
La régression linéaire a la plus petite erreur (70 repas), mais elle fait presque pareil que la baseline. Les autres modèles font pire.

## Le critère (battre clairement la baseline) est-il atteint ?
Non. La météo ne suffit pas pour prévoir le nombre de repas.

Avec toutes les colonnes du fichier, l'erreur descend à 22 repas.

## Ce qui reste flou
- Le test porte sur seulement 68 jours, à la fin de l'année.
- On n'a pas de critère chiffré pour l'erreur acceptable.
