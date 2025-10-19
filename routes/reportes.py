from typing import Optional,List
from datetime import date
from sqlmodel import Session
from connection.data.db import get_session
from fastapi import APIRouter, Depends
from function.freportes import historial_pagos, facturas_pagadas_por_fecha
from services.seguridad_cliente import require_scopes

reportes = APIRouter(
        prefix="/admin/reportes",
        responses={
            404: {"description": "Not found"},
            500: {"description": "Internal Server Error"},
        },
        tags=["reportes"] 
    )


@reportes.get("/historial_pagos",dependencies=[Depends(require_scopes("admin"))])
def obtener_historial_pagos(proveedor_id: Optional[int] = None, fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None, limite: int = 100, session: Session = Depends(get_session)):
    """
    Obtener el historial de pagos realizados a proveedores
    """
    pagos = historial_pagos(session, proveedor_id, fecha_inicio, fecha_fin, limite)
    return {"historial_pagos": pagos}

@reportes.get("/facturas_pagadas",dependencies=[Depends(require_scopes("admin"))])
def obtener_facturas_pagadas(proveedor_id: Optional[int] = None, fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None, limite: int = 100, session: Session = Depends(get_session)):
    """
    Obtener una lista de facturas pagadas por proveedores en un rango de fechas.
    """
    facturas = facturas_pagadas_por_fecha(session, proveedor_id, fecha_inicio, fecha_fin, limite)
    return {"facturas_pagadas": facturas}