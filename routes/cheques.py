from fastapi import APIRouter, Depends,HTTPException, status
from sqlmodel import Session
from sqlalchemy import text
from connection.data.db import get_session
from services.seguridad_cliente import require_roles
from connection.models.modelos import EmitirCheque, AnularCheque
from function.fcheques import emitir_cheque, anular_cheque

cheques = APIRouter(
        prefix="/admin/cheques",
        responses={
            404: {"description": "Not found"},
            500: {"description": "Internal Server Error"},
        },
        tags=["cheques"] 
    )

@cheques.post("/emitir", status_code=201, dependencies=[])
def api_emitir(dto: EmitirCheque, session: Session = Depends(get_session)):
    try:
    
        cid = emitir_cheque(session, dto.id_cuenta_bancaria, dto.id_tipo_cheque, dto.numero_cheque,
                            dto.beneficiario, dto.monto, dto.referencia, dto.observacion)
        return {"id_cheque": cid}
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

@cheques.post("/{id_cheque}/anular", status_code=204, dependencies=[])
def api_anular(id_cheque: int, dto: AnularCheque, session: Session = Depends(get_session)):
    try: 
        
        anular_cheque(session, id_cheque, dto.motivo); return {"anulado exitosamente": True}
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    

@cheques.get("/listar", dependencies=[])
def listar_cheques(cuenta_id: int | None = None, estado: str | None = None, session: Session = Depends(get_session)):
     
    sql = "SELECT * FROM bancos.cheques WHERE 1=1"
    params = {}
    if cuenta_id is not None:
        sql += " AND id_cuenta_bancaria = :c"; params["c"] = cuenta_id
    if estado is not None:
        sql += " AND estado = :e"; params["e"] = estado
    sql += " ORDER BY id_cheque DESC LIMIT 200"
    rows = session.exec(text(sql), params).all()
    return {"items": [dict(r._mapping) for r in rows]}
   