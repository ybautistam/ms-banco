from uuid import uuid4
from decimal import Decimal
from fastapi import HTTPException, status
from sqlmodel import Session, select
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from typing import List,Optional
from datetime import date, timedelta

from connection.models.modelos import(MovimientoBancario, MovimientoCreate,TransferenciaCreate, PagoProveedorCreate,CuentaBancaria, FacturaCompra,PagoProveedor)

def verificar_cuenta_activa(session:Session,id_cuenta:int)-> None: 
  
    cuenta = session.get(CuentaBancaria, id_cuenta)
    if not cuenta :
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cuenta bancaria no existe")
    if cuenta.estado != "ACTIVA":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cuenta bancaria no está activa")
    
    
def buscar_factura(session:Session,factura_id:int, proveedor_id:int)->FacturaCompra:
   
    factura = session.get(FacturaCompra, factura_id)
    if not factura or factura.proveedor_id != proveedor_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Factura no encontrada para el proveedor")
    return factura
    


def facturas_abiertas_por_proveedor(session:Session, proveedor_id:int,limite: int = 20) -> List[dict]:
    
        
    req = text(""" 
                SELECT factura_id,numero_factura,saldo_pendiente,fecha_emision,fecha_vencimiento,estado
                FROM bancos.facturas_compra
                    WHERE proveedor_id = :prov 
                        AND estado IN ('PARCIAL','PENDIENTE')
                    ORDER BY fecha_vencimiento NULLS LAST
                    LIMIT :lim
            """)
    fila = session.exec(req, {"prov": proveedor_id, "lim":limite}).all()
    return [dict(r._mapping) for r in fila]
    
    
def obtener_saldo(session:Session,id_cuenta:int)->Decimal:
       
    verificar_cuenta_activa(session, id_cuenta)
        
    req = session.exec(
        text("SELECT saldo_calculado FROM  bancos.vw_saldo_cuenta WHERE id_cuenta_bancaria = :id"),
        {"id": id_cuenta}
    ).first()
    # retorna el saldo o 0.00 si la cuenta no tiene movimientos
    return req[0] if req else Decimal("0.00")
   

def crear_movimiento(session:Session, mov:MovimientoCreate,usuario:str)-> int:
    
    verificar_cuenta_activa(session, mov.id_cuenta_bancaria)
    
    if mov.referencia_externa:
        # Verificar si ya existe un movimiento con la misma referencia externa
        existente = session.exec(
            select(MovimientoBancario.id_movimiento).where(
                MovimientoBancario.referencia_externa == mov.referencia_externa
            )
        ).first()
        if existente:
            return  existente[0]
    movi = MovimientoBancario(**mov.dict(),usuario_registro=usuario)
    
    try: 
        session.add(movi)
        session.commit()
        session.refresh(movi)
        return movi.id_movimiento
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Movimiento duplicado o datos invalidos ") from e
    
def transferencia_interna(session:Session,trans:TransferenciaCreate,usuario:str)-> str:
    if trans.origen == trans.destino:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cuenta origen y destino no pueden ser iguales")
    #origen
    verificar_cuenta_activa(session, trans.origen)
    #destino
    verificar_cuenta_activa(session, trans.destino)
    
    #validar saldo haste de hacer la transaccion 
    saldo_origen = obtener_saldo(session, trans.origen)
    if saldo_origen < trans.monto:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=f"Saldo insuficiente ({saldo_origen}) en cuenta origen {trans.origen}.")
    
    id_trans = str(uuid4())
    
    try: 
        #transaccion atomica
        
        with session.begin(): 
            #se retira de la cuenta origen 
            salida = MovimientoBancario(
                id_cuenta_bancaria=trans.origen,
                tipo_mov="TRANSFERENCIA_OUT",
                monto=trans.monto,
                referencia=trans.referencia,
                descripcion=f"Transferencia a cuenta ID {trans.destino}",
                transferencia_id=id_trans,
                usuario_registro=usuario
            )
            session.add(salida)
            #se deposita a la cuenta destino 
            entrada= MovimientoBancario (
                id_cuenta_bancaria=trans.destino,
                tipo_mov="TRANSFERENCIA_IN",
                monto=trans.monto,
                referencia=trans.referencia,
                descripcion=f"Transferencia de cuenta ID {trans.origen}",
                transferencia_id=id_trans,
                usuario_registro=usuario
            )
            session.add(entrada)
            
            return id_trans
    except IntegrityError as e:
        
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Error al crear transferencia") from e
    
def pago_a_proveedor(session:Session,pago:PagoProveedorCreate,usuario:str)-> int:
    
    verificar_cuenta_activa(session, pago.id_cuenta_bancaria)
    
    #validar saldo 
    saldo_cuenta = obtener_saldo(session, pago.id_cuenta_bancaria)
    if saldo_cuenta < pago.monto_pagado:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail=f"Saldo insuficiente ({saldo_cuenta}) para realizar el pago.")
    
    factura: Optional[FacturaCompra] = None
    
    if pago.factura_id:
        factura = buscar_factura(session, pago.factura_id, pago.proveedor_id)
        
        if factura.estado == "ANULADA":
            raise HTTPException(status.HTTP_400_BAD_REQUEST,detail="Factura anulada; no se puede pagar")
        if factura.saldo_pendiente <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La factura ya está pagada")
        
        if pago.monto_pagado > factura.saldo_pendiente:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Monto pagado excede saldo pendiente de la factura")
    
    
    try: 
        with session.begin(): 
            
            #registro del pago al proveedor
            
            registrar_pago = PagoProveedor(
                proveedor_id=pago.proveedor_id,
                factura_id=pago.factura_id if factura else None,
                id_cuenta_bancaria=pago.id_cuenta_bancaria,
                monto_pagado=pago.monto_pagado,
                forma=pago.forma,
                referencia_banco=pago.referencia_banco,
                observacion=pago.observacion
            )
            session.add(registrar_pago)
            
            
            # retiro de la cuenta bancaria
            mov = MovimientoBancario(
                id_cuenta_bancaria=pago.id_cuenta_bancaria,
                tipo_mov="RETIRO",
                monto=pago.monto_pagado,
                referencia=f"Pago a proveedor {pago.proveedor_id} - Fact: {pago.factura_id or 'S/F'}",
                descripcion=pago.observacion,
                usuario_registro=usuario
            )
            
            session.add(mov)
            session.flush() 
            session.refresh(registrar_pago) 
            session.refresh(mov)            

            
            mov.referencia_externa = str(registrar_pago.pago_id)
            session.add(mov) # Guardar el movimiento actualizado
            
           
            # actualizar saldo pendiente de la factura si aplica
            
            if factura:
                fact= session.exec(
                    select(FacturaCompra)
                    .where(FacturaCompra.factura_id == factura.factura_id)
                    .with_for_update()
                ).one()
                fact.saldo_pendiente = (fact.saldo_pendiente - pago.monto_pagado).quantize(Decimal("0.01"))
                fact.estado = ("PAGADA" if fact.saldo_pendiente == 0 else "PARCIAL")
                
        # pago_id = session.exec(
        #     select(PagoProveedor.pago_id).order_by(PagoProveedor.pago_id.desc()).limit(1)
        # ).first()[0]
        # return pago_id
        
        return registrar_pago.pago_id
    except IntegrityError as e:
        
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="datos invalidos o pago duplicado") from e


def historial_pagos(session: Session,
                    proveedor_id: Optional[int] = None,
                    desde: Optional[date] = None,
                    hasta: Optional[date] = None,
                    limit: int = 200) -> list[dict]:
    lista, params = [], {"limit": limit}
    if proveedor_id is not None:
        lista.append("p.proveedor_id = :prov"); params["prov"] = proveedor_id
    if desde is not None:
        lista.append("p.fecha_pago >= :desde"); params["desde"] = desde
    if hasta is not None:
        lista.append("p.fecha_pago < :hasta_plus"); params["hasta_plus"] = hasta + timedelta(days=1)

    where_clause = ("WHERE " + " AND ".join(lista)) if lista else ""
    sql = text(f"""
        SELECT p.pago_id, p.proveedor_id, pr.nombre AS proveedor,
               p.factura_id, p.id_cuenta_bancaria, p.fecha_pago,
               p.monto_pagado, p.forma, p.referencia_banco, p.observacion
        FROM bancos.pagos_proveedor p
        JOIN bancos.proveedores pr ON pr.proveedor_id = p.proveedor_id
        {where_clause}
        ORDER BY p.fecha_pago DESC
        LIMIT :limit
    """)
    rows = session.exec(sql, params).all()
    return [dict(r._mapping) for r in rows]
