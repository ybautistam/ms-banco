# app/security.py
from fastapi import Depends, HTTPException, status, Request
from typing import List, Any
import jwt  
from connection.data.db import settings  
from connection.models.modelos import AuthUsuario  

def _decode_jwt(token: str) -> dict[str, Any]:
    # Si JWT_AUD está vacío, no verifiques audience
    options = {"verify_aud": bool(settings.JWT_AUD)}
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALG],
        audience=settings.JWT_AUD or None,
        issuer=settings.JWT_ISS or None,
        options=options,
    )

def get_current_user(request: Request) -> AuthUsuario:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Falta token")

    token = auth.split(" ", 1)[1]
    try:
        payload = _decode_jwt(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    scopes = payload.get("roles") or payload.get("scopes") or []
    if not isinstance(scopes, list):
        scopes = []

    return AuthUsuario(
        sub=payload.get("sub"),
        email=payload.get("email"),
        scopes=scopes,
    )

def require_scopes(*needed: str):
    def _dep(user: AuthUsuario = Depends(get_current_user)) -> AuthUsuario:
        # Necesita al menos uno de los scopes requeridos
        if needed and not any(s in user.scopes for s in needed):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
        return user
    return _dep

