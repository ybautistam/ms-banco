# services/seguridad_cliente.py
from fastapi import Depends, HTTPException, status, Request
from typing import Any
import jwt, os
from connection.data.db import settings
from connection.models.modelos import AuthUsuario
import logging
log = logging.getLogger("bancos.auth")

def _get_secret_and_alg():
    # Prioriza JWT_SECRET (que es lo que tienes en Railway). Si no, intenta JWT_KEY.
    secret = (
        getattr(settings, "JWT_SECRET", None) or os.getenv("JWT_SECRET") or
        getattr(settings, "JWT_KEY", None)    or os.getenv("JWT_KEY")
    )
    alg = getattr(settings, "JWT_ALG", None) or os.getenv("JWT_ALG") or "HS256"
    if not secret:
        # Deja claro en logs / respuesta que falta configuración
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET/JWT_KEY no configurado en ms-banco"
        )
    return secret, alg

def _decode_jwt(token: str) -> dict[str, Any]:
    secret, alg = _get_secret_and_alg()
    try:
        options = {"verify_aud": bool(getattr(settings, "JWT_AUD", ""))}
        return jwt.decode(
            token,
            secret,
            algorithms=[alg],
            audience=(getattr(settings, "JWT_AUD", None) or None),
            issuer=(getattr(settings, "JWT_ISS", None) or None),
            options=options,
        )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        # Token expirado o inválido -> 401
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        # Cualquier otra cosa (mala config, issuer/aud, etc.) -> 401 para no reventar
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=f"Token inválido: {e}")

def get_current_user(request: Request) -> AuthUsuario:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        log.warning("Auth: Falta token")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Falta token")

    token = auth.split(" ", 1)[1]
    try:
        payload = _decode_jwt(token)
    except jwt.ExpiredSignatureError as e:
        log.warning("Auth: Token expirado: %s", e)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError as e:
        log.warning("Auth: Token inválido: %s", e)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    scopes = payload.get("roles") or payload.get("scopes") or []
    if not isinstance(scopes, list):
        scopes = []

    user = AuthUsuario(sub=payload.get("sub"), email=payload.get("email"), scopes=scopes)
    log.info("Auth OK sub=%s roles=%s", user.sub, scopes)
    return user

def require_scopes(*needed: str):
    def _dep(user: AuthUsuario = Depends(get_current_user)) -> AuthUsuario:
        if needed and not any(s in user.scopes for s in needed):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
        return user
    return _dep


