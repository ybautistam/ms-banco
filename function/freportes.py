from typing import Optional,List
from datetime import date
from sqlalchemy import text
from sqlmodel import Session
from datetime import timedelta


def historial_pagos(session:Session, proveedor_id:Optional[int] = None, fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None,limite:int = 100 ) -> List[dict]:
    
    lista ,params = [],{"limite": limite}
    
    if proveedor_id is not None:
        lista.append("p.proveedor_id = :prov")
        params["prov"] = proveedor_id
        
    if fecha_inicio is not None:
        lista.append("p.fecha_pago >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio
        
    if fecha_fin is not None:
        lista.append("p.fecha_pago < :fecha_fin")
        params["fecha_fin"] = fecha_fin + timedelta(days=1)  
            
    where_clause = (" WHERE " + " AND ".join(lista)) if lista else ""
        
    query = text(f"""
                 SELECT 
                    p.pago_id, 
                    p.proveedor_id, 
                    pr.nombre AS proveedor,
                    p.factura_id,
                    p.id_cuenta_bancaria, 
                    p.monto_pagado, 
                    p.fecha_pago, 
                    p.forma,        
                    p.referencia_banco, 
                    p.observacion
                FROM bancos.pagos_proveedor p
                JOIN bancos.proveedores pr ON pr.proveedor_id = p.proveedor_id 
                {where_clause}
                ORDER BY p.fecha_pago DESC
                LIMIT :limite
                    
                """) 
        
        
    result = session.exec(query, params).all()
    return [dict(r._mapping) for r in result]
   

def facturas_pagadas_por_fecha(session:Session, proveedor_id:Optional[int] = None, fecha_inicio: Optional[date] = None, fecha_fin: Optional[date] = None, limite:int = 100) -> List[dict]:

    lista,params = ["f.estado = 'PAGADA'" ],{"limite": limite}
        
    if proveedor_id is not None:
        lista.append("f.proveedor_id = :prov")
        params["prov"] = proveedor_id
        
    list_fecha_ultima = []
    
    if fecha_inicio is not None:
        list_fecha_ultima.append("MAX(pp.fecha_pago) >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio
    if fecha_fin is not None:
        
        list_fecha_ultima.append("MAX(pp.fecha_pago) < :fecha_fin_plus") 
        params["fecha_fin_plus"] = fecha_fin + timedelta(days=1)
            
    where_clause = " WHERE " + " AND ".join(lista) 
    having_clause = " HAVING " + " AND ".join(list_fecha_ultima) if list_fecha_ultima else ""
        
    #fecha ultima de pago  
    req = text(f"""
        SELECT 
            fc.factura_id, 
            fc.numero_factura, 
            fc.proveedor_id, 
            pr.nombre AS proveedor, 
            SUM(pp.monto_pagado) AS total_pagado, 
            fc.saldo_pendiente,
            MAX(pp.fecha_pago) AS fecha_ultimo_pago
        FROM bancos.facturas_compra fc
        JOIN bancos.pagos_proveedor pp ON pp.factura_id = fc.factura_id
        JOIN bancos.proveedores pr ON pr.proveedor_id = fc.proveedor_id
        {where_clause}
        GROUP BY fc.factura_id, fc.numero_factura, fc.proveedor_id, pr.nombre,fc.saldo_pendiente
        {having_clause} 
        ORDER BY total_pagado DESC
        LIMIT :limite
    """)
    
    filas = session.exec(req, params).all()
    return [dict(r._mapping) for r in filas]
    