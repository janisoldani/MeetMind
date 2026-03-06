"""
Auth-Dependencies für FastAPI Endpoints.
Clerk JWT-Validierung wird in Milestone 1, Schritt 5 implementiert.
"""
import uuid

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db_with_rls

security = HTTPBearer(auto_error=True)

# JWKS Client wird lazy initialisiert (erst wenn Clerk konfiguriert ist)
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not settings.clerk_jwks_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth nicht konfiguriert (CLERK_JWKS_URL fehlt)",
            )
        _jwks_client = PyJWKClient(settings.clerk_jwks_url)
    return _jwks_client


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Validiert den Clerk JWT und gibt die User-ID zurück."""
    token = credentials.credentials
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True},
        )
        return payload["sub"]  # Clerk User ID
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token abgelaufen")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Ungültiger Token")


async def get_current_workspace_id(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(lambda: get_db_with_rls(uuid.uuid4())),
) -> uuid.UUID:
    """Lädt die workspace_id des aktuellen Users aus der DB.
    Wird in Milestone 1 Schritt 5 vollständig implementiert.
    """
    # TODO: User aus DB laden und workspace_id zurückgeben
    # Placeholder für jetzt
    raise HTTPException(status_code=501, detail="Noch nicht implementiert")
