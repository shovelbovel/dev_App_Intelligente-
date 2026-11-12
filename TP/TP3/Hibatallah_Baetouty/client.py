"""Client Python de l'API MaintAI : ce que fetch faisait dans la page web (TP2), en Python.

Usage :
    from maintai.client import MaintaiClient
    api = MaintaiClient("http://localhost:8000", api_key="demo123")
    api.predict({"temperature_c": 72, "vibration_mm_s": 6, "load_pct": 85, "runtime_hours": 15000})
"""
import httpx


class APIError(Exception):
    """L'API a répondu, mais pas 200 : on garde le code et le message."""

    def __init__(self, status_code: int, detail):
        super().__init__(f"Erreur {status_code} : {detail}")
        self.status_code = status_code
        self.detail = detail


class MaintaiClient:
    def __init__(self, url: str = "http://localhost:8000", api_key: str | None = None,
                 http: httpx.Client | None = None):
        # Les tests passent leur TestClient dans http : même code, sans serveur
        self.http = http or httpx.Client(base_url=url, timeout=5.0)
        self.api_key = api_key

    def health(self) -> dict:
        r = self.http.get("/health")
        r.raise_for_status()
        return r.json()

    def predict(self, reading: dict) -> dict:
        """Envoie un relevé ; lève APIError si l'API refuse, httpx.HTTPError si elle est injoignable."""
        # 1. En-tête d'authentification, ajouté seulement si une clé est fournie.
        #    Sans clé on envoie un dict vide plutôt qu'un en-tête vide : c'est l'API qui
        #    tranche et répond 401 (voir api/security.py), pas le client.
        headers = {"X-API-Key": self.api_key} if self.api_key else {}

        # 2. L'équivalent Python du fetch() de la page web du TP2.
        #    Si le serveur est injoignable, httpx lève ici une httpx.HTTPError que l'on
        #    laisse remonter volontairement : l'appelant (l'UI) sait la distinguer d'un refus.
        r = self.http.post("/v1/predict", json=reading, headers=headers)

        # 3. Tout code autre que 200 est une erreur métier : on la convertit en APIError,
        #    qui transporte le code et le message. Pas de raise_for_status() ici, car il
        #    perdrait le contenu de "detail" dont l'interface a besoin pour s'expliquer.
        if r.status_code != 200:
            # FastAPI met son message dans la clé "detail" : du texte pour 401 et 503,
            # une liste de champs invalides pour 422.
            try:
                detail = r.json().get("detail")
            except ValueError:
                # Corps non-JSON (page d'erreur d'un proxy, 502/504...) : .json() lèverait
                # une erreur de parsing au lieu de l'APIError attendue, donc on se rabat
                # sur le texte brut de la réponse.
                detail = r.text
            raise APIError(r.status_code, detail)

        # 4. Cas normal : on renvoie le dict {failure_probability, alert, threshold,
        #    model_version}, tel que décrit par PredictionOut dans api/schemas.py.
        return r.json()
