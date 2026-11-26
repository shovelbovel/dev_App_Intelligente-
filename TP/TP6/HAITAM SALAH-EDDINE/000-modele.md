# ADR 000 : choisir le modèle de prédiction de panne

Date : 26/11/2026 · Auteurs : HAITAM SALAH EDDINE  Heure: 11:25am

## Contexte

MaintAI doit signaler les machines qui risquent de tomber en panne à partir de quatre mesures de capteurs (température, vibration, charge, heures de fonctionnement). Les pannes sont rares (13,6 % des relevés) : une panne manquée coûte plus cher qu'une fausse alerte, donc le rappel compte davantage que l'exactitude.

## Options étudiées

Mesures sur le même jeu de test (1 000 relevés), au seuil d'alerte 0,3 :


| Modèle                                | Exactitude | Rappel    | Précision | Taille du fichier |
| -------------------------------------- | ---------- | --------- | ---------- | ----------------- |
| Baseline (toujours « pas de panne ») | 0,864      | 0,000     | —         | —                |
| Régression logistique (C = 1,0)       | **0,904**  | **0,750** | **0,622**  | 1,7 Ko            |
| Forêt aléatoire (200 arbres)         | 0,886      | 0,728     | 0,562      | 8,5 Mo            |

1. **Régression logistique**, avec un `StandardScaler` dans le même pipeline.
   - Avantages : les meilleurs scores sur les trois métriques, un modèle minuscule (1,7 Ko) qui se charge instantanément, et des coefficients faciles à expliquer (une hausse de vibration fait monter le risque, par exemple).
   - Inconvénients : la frontière de décision est linéaire, donc le modèle peut manquer des interactions entre variables si les données réelles en contiennent.
2. **Forêt aléatoire**.
   - Avantages : elle capte les effets non linéaires et les interactions sans qu'on ait à les construire à la main.
   - Inconvénients : elle fait moins bien sur nos données (rappel 0,728, précision 0,562) et pèse 5 000 fois plus lourd. Elle est aussi plus lente à charger et plus difficile à expliquer.

## Décision

On garde la **régression logistique (C = 1,0) avec un seuil d'alerte de 0,3**. Elle a le meilleur rappel, ce qui est la contrainte principale du projet : ne pas manquer de panne. Elle bat la baseline de 75 points de rappel, et elle reste simple à servir et à expliquer. Le seuil de 0,3, plus bas que le 0,5 par défaut, privilégie lui aussi le rappel au détriment de quelques fausses alertes.

## Conséquences

- Le modèle est léger, ce qui facilite sa livraison : le volume Docker du TP6, le wheel du TP4 et un dossier `MAINTAI_MODELS_DIR` sur une autre machine.
- Le contrat d'entrée est fixé : quatre colonnes, dans l'ordre de `FEATURES`, enregistrées dans `model_info.json`.
- Le modèle doit être chargé avec la même version de scikit-learn que celle qui l'a écrit (1.8.0). Ce point est à surveiller à chaque mise à jour des dépendances.
- Les données actuelles sont synthétiques. Quand de vraies données arriveront, il faudra refaire la comparaison (les runs MLflow permettent de rejouer les deux options), car la forêt pourrait alors prendre l'avantage.
- Si le rappel ne suffit pas sur le terrain, on peut d'abord baisser le seuil (`--threshold`) avant de changer de modèle.
