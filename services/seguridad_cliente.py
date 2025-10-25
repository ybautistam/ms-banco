# services/seguridad_cliente.py
from fastapi import Depends, HTTPException, status, Header
from typing import Any
import jwt, os
from connection.data.db import settings
from connection.models.modelos import AuthUsuario
import logging
#log = logging.getLogger("bancos.auth")

JWT_SECRET = os.getenv("JWT_SECRET")  
JWT_ALG = os.getenv("JWT_ALG")


def get_current_user(authorization: str = Header(..., alias="Authorization")) -> AuthUsuario:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalidacion auth header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return AuthUsuario(
            sub=str(payload.get("sub")),
            nombre=payload.get("nombre"),
            rol=payload.get("rol"),
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail=" token invalido")

def require_scopes(*needed: str):
    def _dep(usuario: AuthUsuario = Depends(get_current_user)) -> AuthUsuario:
        if needed:
            
            if not any(s in (usuario.scopes or []) for s in needed):
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Permisos insuficientes")
        return usuario
    return _dep


