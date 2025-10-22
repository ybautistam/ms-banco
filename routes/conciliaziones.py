from fastapi import APIRouter, Depends,HTTPException,status
from sqlmodel import Session
from typing import Optional
from connection.data.db import get_session
from services.seguridad_cliente import require_scopes
from connection.models.modelos import ConciliacionCreate
from function.fconsiliaciones import crear_conciliacion,listar_conciliaciones,listar_partidas_pendientes,_seguimiento_bandera
from function.fbancos import verificar_cuenta_activa
from datetime import date

conc = APIRouter(
        prefix="/admin/conciliaciones",
        responses={
            404: {"description": "Not found"},
            500: {"description": "Internal Server Error"},
        },
        tags=["conciliaciones"] 
    )

@conc.post("/",status_code=status.HTTP_201_CREATED,dependencies=[],)
def crear_conc(dto: ConciliacionCreate,session: Session = Depends(get_session),):
    """
    Crea una conciliación:
      - Si bandera=True: solo calcula y NO marca movimientos ni inserta registros.
      - Si bandera=False: usa `crear_conciliacion()` para marcar no-conciliados y guardar la conciliación.
    """
    verificar_cuenta_activa(session, dto.id_cuenta_bancaria)
    fecha = dto.fecha_conciliacion or date.today()

    if dto.bandera:
              
        res = _seguimiento_bandera(session, dto.id_cuenta_bancaria, fecha, dto.saldo_banco)
        return {"bandera": True, **res}

    # Conciliación real (marca movimientos + inserta registro)
    try:
        conciliacion_id = crear_conciliacion(
            session=session,
            id_cuenta=dto.id_cuenta_bancaria,
            fecha_conciliacion=fecha,
            saldo_banco=dto.saldo_banco,
            observaciones=dto.observaciones,
        )
        return {"bandera": False, "id_conciliacion": conciliacion_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error al conciliar: {e}")


@conc.get("",dependencies=[],)
def listar_conc(id_cuenta_bancaria: int,desde: Optional[date] = None,hasta: Optional[date] = None,limit: int = 100,session: Session = Depends(get_session),):
    
    """
    Lista conciliaciones de una cuenta en un rango de fechas.
    """
    verificar_cuenta_activa(session, id_cuenta_bancaria)
    items = listar_conciliaciones(session, id_cuenta_bancaria, desde, hasta, limit)
    return {"items": items}


@conc.get("/partidas-pendientes",dependencies=[],)
def listar_partidas(id_cuenta_bancaria: int,hasta: date,session: Session = Depends(get_session),
):
    """
    Lista movimientos no conciliados y cheques emitidos no cobrados
    hasta la fecha dada (inclusive).
    """
    verificar_cuenta_activa(session, id_cuenta_bancaria)
    data = listar_partidas_pendientes(session, id_cuenta_bancaria, hasta)
    return data
