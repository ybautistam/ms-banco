import os
from sqlmodel import Session, create_engine
from pydantic import BaseModel, Field, field_validator
from fastapi import HTTPException,status,Depends
from typing import Annotated,List



class Settings(BaseModel):
    POSTGRES_URL: str = Field(default_factory=lambda: os.getenv("POSTGRES_URL", ""))
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

# POSTGRES_URL = os.getenv("POSTGRES_URL")  
# if not POSTGRES_URL: 
#     raise RuntimeError("POSTGRES_URL no está definida en el entorno")

engine = create_engine(settings.POSTGRES_URL, pool_pre_ping=True, echo=False,connect_args={"options": "-c search_path=bancos,public"},)

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

