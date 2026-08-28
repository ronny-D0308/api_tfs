# =============================================================
# security.py — Autenticação por API Key fixa
# =============================================================

import os
import secrets
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    """
    Valida a API Key enviada no header X-API-Key.
    Usa comparação segura (secrets.compare_digest) para evitar timing attacks.
    """
    expected = os.getenv("API_KEY")

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY não configurada no servidor."
        )

    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida ou ausente.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
