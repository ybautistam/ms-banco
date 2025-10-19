import os
from sqlmodel import Session, create_engine
from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException,status,Depends
from typing import Annotated,List



class Settings(BaseModel):
    POSTGRES_URL: str = Field(default_factory=lambda: os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL"))
    ALLOWED_ORIGINS: List[str] = Field(default_factory=list)
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "5.0"))
    RETRIES: int = int(os.getenv("RETRIES", "2"))

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if not v:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

settings = Settings()

if not settings.POSTGRES_URL:
    raise RuntimeError("POSTGRES_URL no está definida en el entorno")

def _normalize_url(u: str) -> str:
    # railway da 'postgres://...'  => SQLAlchemy quiere 'postgresql://'
    if u.startswith("postgres://"):
        u = u.replace("postgres://", "postgresql://", 1)
    # fuerza psycopg3 (no psycopg2)
    if u.startswith("postgresql://") and "+psycopg" not in u and "+psycopg2" not in u:
        u = u.replace("postgresql://", "postgresql+psycopg://", 1)
    return u

DB_URL = _normalize_url(settings.POSTGRES_URL) 
engine = create_engine(DB_URL, pool_pre_ping=True, echo=False,connect_args={"options": "-c search_path=bancos,public"},)

def get_session():
    try: 
    
        with Session(engine) as session:
            yield session
    except Exception as e: 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error de conexión a la base de datos: {e}",
        )
        
SessionDep = Annotated[Session,Depends(get_session)]

