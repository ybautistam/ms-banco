import os
import logging
import uuid
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.bancos import banco
from routes.reportes import reportes
from routes.conciliaziones import conc
from routes.cheques import cheques

app = FastAPI(title="bancos Api")
app.router.redirect_slashes = False

DEBUG = os.getenv("DEBUG", "0") == "1"
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if not origins:
    origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
  
    expose_headers=["X-New-Access-Token", "X-New-Access-Expires-In","X-New-Refresh-Token"],
)

logger = logging.getLogger("bancos")
logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def add_reqid_and_log(request: Request, call_next):
    reqid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
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
    if DEBUG:
        return JSONResponse({"detail": str(exc)}, status_code=500)
    return JSONResponse({"detail": "internal_error"}, status_code=500)
#-----------------routers --------------------------
app.include_router(banco)
app.include_router(reportes)
app.include_router(conc)
app.include_router(cheques)