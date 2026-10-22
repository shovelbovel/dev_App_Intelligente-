# TP0 : MaintAI
**Nom : BAETOUTY ** Prénom Hibatallah · **Groupe :G1 ** 5IAD MOULAY YOUSSEF 
**REALISER EN BINOME : AVEC Abdelali SAHIA**

## Le problème
Savoir à l'avance si une machine va tomber en panne, grâce à 4 capteurs : température, vibration, charge et heures de fonctionnement. Une panne qu'on ne voit pas venir arrête toute la ligne.

## Résultats sur le jeu de test
| Modèle | Accuracy | Rappel | Précision |
|-|-|-|-|
| baseline | 0.824 | 0.000 | 0.000 |
| régression logistique | 0.839 | 0.847 | 0.527 |
| arbre de décision | 0.825 | 0.722 | 0.502 |
| forêt aléatoire | 0.882 | 0.540 | 0.720 |
| k plus proches voisins | 0.878 | 0.540 | 0.699 |

## Mon choix, et pourquoi
Je garde la régression logistique.

Le piège, c'est l'accuracy. La baseline dit « pas de panne » à chaque fois, et elle a quand même 82 % de bonnes réponses, parce que la plupart des machines vont bien. Pourtant, elle ne sert à rien : elle ne trouve aucune panne.

Je regarde donc surtout le rappel, qui dit combien de vraies pannes le modèle trouve. La forêt aléatoire a la meilleure accuracy, mais elle laisse passer une panne sur deux. La régression logistique en trouve plus de 8 sur 10.

## Le critère (rappel >= 0,75) est-il atteint ?
Oui, avec un rappel de 0,847. Aucun autre modèle n'y arrive. L'arbre de décision est le plus proche, avec 0,722.

Le défaut, c'est qu'elle donne beaucoup de fausses alertes : une fois sur deux, la machine n'avait rien. Je l'accepte quand même : vérifier une machine qui va bien prend un peu de temps, alors qu'une ligne arrêtée coûte beaucoup plus cher.

## Ce qui reste flou
- J'ai testé sur un seul découpage. Avec un autre, le rappel serait peut-être un peu différent.
- Je n'ai pas touché au seuil de 0,5. On pourrait le régler pour trouver encore plus de pannes.
- Je ne sais pas combien coûte exactement une fausse alerte. Sans ce chiffre, c'est difficile de dire quel compromis est le meilleur.

---

# TP0 : Cantine
**Nom :** Prénom Nom · **Groupe :** G3

## Le problème
Deviner combien de repas la cantine va servir dans la journée, en utilisant seulement 2 capteurs : la température et la pluie.

## Résultats sur le jeu de test
| Modèle | MAE (repas) | RMSE | R² |
|-|-|-|-|
| baseline (moyenne) | 70.271 | 88.416 | -0.151 |
| régression linéaire | 69.622 | 86.813 | -0.110 |
| arbre de décision | 83.626 | 107.376 | -0.698 |
| forêt aléatoire | 78.566 | 101.139 | -0.506 |
| k plus proches voisins | 72.638 | 91.000 | -0.219 |

## Mon choix, et pourquoi
Si je dois en garder un, c'est la régression linéaire, qui a la plus petite erreur. Mais honnêtement, elle ne fait pas mieux que la baseline. Prédire la moyenne tous les jours donne presque le même résultat : 70 repas d'erreur dans les deux cas.

Les autres modèles sont encore moins bons que la baseline. Tous les R² sont négatifs, donc aucun modèle n'explique vraiment le nombre de repas.

## Le critère (battre clairement la baseline) est-il atteint ?
Non. Le temps qu'il fait ne permet pas de prévoir combien d'élèves vont manger à la cantine.

J'ai fait le test avec toutes les colonnes du fichier : l'erreur tombe à 22 repas. Ce qui compte vraiment, ce sont le nombre d'inscrits, le menu, les examens ou les sorties scolaires, pas la météo.

## Ce qui reste flou
- Les 68 jours de test sont tous à la fin de l'année. L'hiver n'est pas testé.
- On ne sait pas quelle erreur est acceptable pour la cantine : 10 repas ? 30 ? Il faudrait poser la question.
- La pluie ou la chaleur jouent peut-être seulement les jours extrêmes. Je n'ai pas regardé ce cas.