import pytest

HEADERS = {
    "X-API-Key": "test-key"
}  # la clé des tests (conftest.py) ; inutile en TP1, nécessaire enTP2
VALID = {
    "temperature_c": 60.0,
    "vibration_mm_s": 2.0,
    "load_pct": 50.0,
    "runtime_hours": 5000,
}
CAS_REFUSES = [
    # (description, url, corps, code attendu)
    ("valeur absurde", "/v1/predict", {**VALID, "load_pct": 250}, 422),
    (
        "champ manquant",
        "/v1/predict",
        {"temperature_c": 60.0, "vibration_mm_s": 2.0, "runtime_hours": 5000},
        422,
    ),
    ("champ inconnu", "/v1/predict", {**VALID, "pression_bar": 3.0}, 422),
    ("mauvais type", "/v1/predict", {**VALID, "temperature_c": "chaud"}, 422),
    ("mauvaise adresse", "/v1/predicte", VALID, 404),
]


@pytest.mark.parametrize("description, url, corps, attendu", CAS_REFUSES)
def test_requete_refusee(client, description, url, corps, attendu):
    assert client.post(url, json=corps, headers=HEADERS).status_code == attendu
