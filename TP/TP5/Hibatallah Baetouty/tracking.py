"""Suivi des entraînements avec MLflow : chaque entraînement devient un « run » qu'on peut comparer.

Les runs sont enregistrés dans mlflow.db (dossier courant) ; on les regarde avec : mlflow ui
"""
import hashlib
import os
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")  # coupe un message d'information de MLflow

import mlflow
import mlflow.sklearn

EXPERIMENT = "maintai"
TRUSTED_TYPES = ["sklearn.tree._tree.Tree"]  # nécessaire pour --model forest


def file_md5(path: Path) -> str:
    """Empreinte du fichier de données : la même que celle que DVC écrit dans le fichier .dvc."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def log_run(params: dict, metrics: dict, model, X_example, data_path: Path) -> str:
    """Enregistre un entraînement : paramètres, version des données, métriques et modèle. Renvoie l'id du run."""
    # 1. L'expérience regroupe tous les runs du projet : elle est créée au premier appel.
    mlflow.set_experiment(EXPERIMENT)

    # 2. Le with ouvre un run et le ferme proprement, même si l'entraînement lève une erreur.
    with mlflow.start_run() as run:
        # 3a. Les réglages de l'entraînement (modèle, C, seuil, taille du train).
        mlflow.log_params(params)

        # 3b. L'empreinte des données : deux runs comparables doivent avoir le même data_md5.
        #     C'est la même empreinte que celle écrite par DVC dans data/sensors.csv.dvc.
        mlflow.log_param("data_md5", file_md5(data_path))

        # 3c. Les résultats mesurés sur le jeu de test, baseline comprise.
        mlflow.log_metrics(metrics)

        # 3d. Le modèle lui-même (scaler + classifieur). input_example fige le contrat d'entrée ;
        #     skops_trusted_types autorise la sérialisation des arbres pour --model forest.
        mlflow.sklearn.log_model(
            model,
            name="model",
            input_example=X_example,
            skops_trusted_types=TRUSTED_TYPES,
        )

        # 4. L'identifiant sert à retrouver le run (mlflow ui) et à recharger le modèle.
        return run.info.run_id
