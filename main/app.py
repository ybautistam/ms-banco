import os
import logging
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.bancos import banco
from routes.reportes import reportes
from routes.conciliaziones import conc
from routes.cheques import cheques





#docker compose logs -f api   
#python -c "import sqlmodel, sys; print(sqlmodel.__version__, sys.executable)"

#docker compose ps      # verifica que ventas_api esté "Up"
#docker compose up -d   # si no está arriba, levántalo

""" 
# para esta sesión, desactiva buildkit
$env:DOCKER_BUILDKIT=0

# limpia builder cache (opcional pero ayuda)
docker buildx prune -af

# si no te importa borrar imágenes/volúmenes huérfanos (recomendado en dev)
docker system prune -af --volumes

docker compose build --no-cache
docker compose up -d

docker compose up -d --build

docker compose logs -f api
"""

app = FastAPI(title="bancos Api")



app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()] or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Authorization",
        "X-Refresh-Token",
        "Content-Type",
        "Accept",
    ],
    expose_headers=[
        "X-New-Access-Token",
        "X-New-Refresh-Token",
        "X-New-Access-Expires-In",
    ],
)

logger = logging.getLogger("bancos")
logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def add_reqid_and_log(request: Request, call_next):
    reqid = request.headers.get("X-Request-ID") or "no-reqid"
    response = await call_next(request)
    response.headers["X-Request-ID"] = reqid
    logger.info("%s %s %s", request.method, request.url.path, response.status_code)
    return response

@app.get("/health")
def health():
    return {"ok": True, "service": "bancos"}


@app.exception_handler(Exception)
async def excepciones_genericas(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse({"detail": "internal_error"}, status_code=500)

#-----------------routers --------------------------
app.include_router(banco)
app.include_router(reportes)
app.include_router(conc)
app.include_router(cheques)