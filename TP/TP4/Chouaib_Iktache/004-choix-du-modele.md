# ADR 004 : choix du modèle et du seuil de MaintAI

Date : 19/11/2026 · Auteurs : Iktache Chouaib

## Contexte
MaintAI doit prévenir une panne avant qu'elle n'arrive. Une panne manquée (faux négatif) coûte beaucoup plus cher qu'une
fausse alerte (une intervention de contrôle inutile) : le critère principal est donc le **recall**, la precision vient ensuite.
Chaque entraînement est maintenant enregistré dans MLflow (expérience `maintai`), ce qui permet de comparer les réglages
sur les mêmes données.

Runs comparés, tous sur les données v1 (`data_md5` = `73e0b7cb3c6f795c70c3ddf970b99c15`, 4000 lignes d'entraînement, 1000 de test) :

| Run | modèle | C | seuil | recall | precision | accuracy |
|---|---|---|---|---|---|---|
| `1170b800…` | logreg | 1.0 | 0.3 | 0.750 | 0.622 | 0.904 |
| `3fd67dfa…` | logreg | 0.01 | 0.3 | 0.691 | 0.653 | 0.908 |
| `3747245d…` | logreg | 1.0 | **0.2** | **0.838** | 0.543 | 0.882 |
| `0343eb59…` | forest | – | 0.3 | 0.728 | 0.562 | 0.886 |
| `ff36e94b…` | forest | – | 0.2 | 0.831 | 0.479 | 0.854 |

La baseline (toujours prédire « pas de panne ») a un recall de 0.0.

## Options étudiées
1. **Régression logistique, C = 1.0, seuil 0.3** (réglage du TP4) : bon compromis (precision 0.622), simple et lisible ;
   mais elle laisse passer 25 % des pannes.
2. **Régression logistique, C = 1.0, seuil 0.2** : meilleur recall mesuré (0.838) ; en échange, la precision tombe à 0.543.
3. **Régression logistique, C = 0.01** : régularisation forte, la meilleure precision (0.653) mais le plus mauvais recall (0.691).
4. **Forêt aléatoire (seuil 0.3 ou 0.2)** : à seuil égal, pas meilleure que la régression logistique (recall 0.728 / 0.831,
   precision plus faible) ; modèle plus lourd, plus long à entraîner, moins explicable et qui demande des types de confiance skops.

## Décision
On retient la **régression logistique avec `C = 1.0` et le seuil `0.2`**, run MLflow `3747245dab5e46288151105f3e8894fd`,
entraîné sur les données `data_md5 = 73e0b7cb3c6f795c70c3ddf970b99c15` (v1, `data/sensors.csv.dvc`).
Raison principale : c'est le run au meilleur recall ; il détecte environ 84 % des pannes, contre 75 % au seuil 0.3,
et une panne manquée coûte plus cher qu'une fausse alerte.

## Conséquences
- On accepte plus de fausses alertes : environ une alerte sur deux est fausse (precision 0.543), soit plus de contrôles inutiles.
- Le modèle reste simple, rapide et explicable (coefficients de la régression logistique).
- Le seuil 0.2 doit être celui du modèle déployé : entraîner avec `python -m maintai.train --threshold 0.2`
  (il est écrit dans `models/model_info.json`).
- À surveiller : le recall en production et la dérive des données. Si les données changent (v2…), il faudra ré-entraîner
  et comparer dans MLflow, en vérifiant le `data_md5` de chaque run.
