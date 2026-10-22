# TP0 : MaintAI

**Nom :** ZAKI Rim · **Groupe :** G1

## Le problème

MaintAI doit prédire une panne à partir de quatre capteurs : la température, les vibrations, la charge et le temps de fonctionnement. Une panne manquée peut arrêter une ligne de production ; il est donc plus important de détecter correctement les pannes que de maximiser uniquement l'accuracy.

## Résultats sur le jeu de test

| Modèle | Accuracy | Rappel | Précision |
|---|---:|---:|---:|
| Baseline | 0.824 | 0.000 | 0.000 |
| Régression logistique | 0.889 | 0.574 | 0.737 |

## Mon choix, et pourquoi

Je retiens la régression logistique comme meilleur modèle parmi ceux évalués. Elle améliore nettement l'accuracy par rapport à la baseline et, surtout, elle détecte une partie des pannes : son rappel est de 0.574, alors que la baseline ne détecte aucune panne. Sa précision de 0.737 signifie cependant qu'une partie des alertes est erronée.

Ce choix reste provisoire pour une mise en production, car le modèle ne respecte pas encore le critère de rappel défini ci-dessous. Il faudrait notamment ajuster le seuil de décision et évaluer ce réglage sur un jeu de validation distinct.

## Le critère (rappel >= 0,75) est-il atteint ?

Non. Le rappel de la régression logistique est de 0.574, soit 0.176 point en dessous de l'objectif de 0.75. La baseline est encore plus insuffisante avec un rappel nul. Aucun des modèles présentés ne satisfait donc le critère d'acceptation.

## Ce qui reste flou

- La taille exacte du jeu de test et la répartition entre pannes et non-pannes ne sont pas indiquées ; l'accuracy peut être trompeuse si les classes sont déséquilibrées.
- On ne sait pas si le découpage des données empêche une fuite entre l'entraînement et le test.
- Le seuil de décision n'est pas précisé. Un seuil plus bas pourrait augmenter le rappel, au prix d'une baisse possible de la précision.
- Le coût réel d'une fausse alerte n'est pas comparé au coût d'une panne manquée.
- Il faut tester le modèle sur davantage de pannes et sur des conditions de fonctionnement variées avant toute utilisation opérationnelle.

---

# Analyse actualisée : MaintAI

**Nom :** ZAKI Rim · **Groupe :** G1

## Le problème

MaintAI doit prédire si une panne survient à partir de quatre capteurs : la température, les vibrations, la charge et le temps de fonctionnement. Comme une panne manquée peut arrêter une ligne, la métrique principale choisie est le rappel.

## Résultats sur le jeu de test

| Modèle | Accuracy | Rappel | Précision |
|---|---:|---:|---:|
| Régression logistique | 0.839 | 0.847 | 0.527 |
| Random forest | 0.862 | 0.693 | 0.592 |
| Gradient boosting | 0.888 | 0.608 | 0.713 |
| K plus proches voisins | 0.878 | 0.540 | 0.699 |
| Baseline | 0.824 | 0.000 | 0.000 |

## Mon choix, et pourquoi

Je choisis la régression logistique, car elle obtient le meilleur rappel avec un score de 0.847. Elle détecte donc une plus grande proportion des pannes que les autres modèles évalués et que la baseline. Son accuracy est inférieure à celle du gradient boosting, mais le rappel est prioritaire dans ce contexte : une panne manquée est plus grave qu'une fausse alerte.

Sa précision de 0.527 reste cependant limitée. Le modèle générera donc un nombre non négligeable de fausses alertes, qui devront être acceptées ou réduites selon le coût réel d'une intervention de maintenance.

## Le critère (rappel >= 0,75) est-il atteint ?

Oui. La régression logistique obtient un rappel de 0.847, soit 0.097 point au-dessus de l'objectif de 0.75. Le critère est donc atteint sur ce jeu de test. Cette conclusion doit toutefois être confirmée sur un jeu de validation ou sur de nouvelles données avant un déploiement en production.

## Ce qui reste flou

- La taille exacte du jeu de test et le nombre de pannes qu'il contient ne sont pas indiqués.
- La précision de 0.527 montre que la régression logistique produit probablement de nombreuses fausses alertes ; leur coût opérationnel reste à mesurer.
- Le seuil de décision utilisé n'est pas précisé. Un autre seuil pourrait modifier l'équilibre entre rappel et précision.
- Il faut vérifier que le découpage aléatoire ne crée pas de fuite entre les données d'entraînement et celles du test.
- Les performances doivent être vérifiées sur des pannes réelles et sur des conditions de fonctionnement différentes avant toute décision de déploiement.
