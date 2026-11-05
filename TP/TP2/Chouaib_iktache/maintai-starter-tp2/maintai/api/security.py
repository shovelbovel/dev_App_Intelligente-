"""Authentification par clé API, transmise dans l'en-tête X-API-Key."""
import secrets

from fastapi import Header, HTTPException, status

from maintai.config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Refuse la requête si la clé est absente ou fausse."""
    expected = get_settings().api_key
    if not expected:
        # Erreur de configuration du serveur, pas du client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La clé API du serveur n'est pas configurée (MAINTAI_API_KEY)",
        )
    # compare_digest : durée constante, ne trahit pas le nombre de caractères justes
    if x_api_key is None or not secrets.compare_digest(
        x_api_key.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API absente ou invalide",
        )
