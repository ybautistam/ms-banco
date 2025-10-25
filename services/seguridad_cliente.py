# services/seguridad_cliente.py
from fastapi import Depends, HTTPException, status, Header
from typing import Any
import jwt, os
from connection.data.db import settings
from connection.models.modelos import AuthUsuario
import logging
#log = logging.getLogger("bancos.auth")

JWT_SECRET = os.getenv("JWT_SECRET","racsh5cYrXtPacAK1nnHNgHsduL9ALQdp0wAOXKItcd7Iev16dFHdr2A5TA_vQIC0eKQQi7uDoaH0WOi5xZW-w")  
JWT_ALG = os.getenv("JWT_ALG","HS256")


def get_current_user(authorization: str = Header(..., alias="Authorization")) -> AuthUsuario:
    
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return AuthUsuario(
            sub=str(payload.get("sub")),
            nombre=payload.get("nombre"),
            rol=payload.get("rol"),
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail=" token invalido bancos")

def require_roles(*roles: str):
    def _dep(usuario: AuthUsuario = Depends(get_current_user)) -> AuthUsuario:
        if roles and (usuario.rol not in roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Rol insuficiente")
        return usuario
    return _dep


