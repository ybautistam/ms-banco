from sqlmodel import Session
from sqlalchemy import text
from datetime import date
from connection.models.modelos import ConciliacionBancaria
from fastapi import HTTPException, status
from decimal import Decimal,ROUND_HALF_UP
from typing import List, Dict, Union
from function.fbancos import verificar_cuenta_activa

def _calcular_saldo_movimientos(session: Session, id_cuenta: int, hasta: date, solo_no_conciliados: bool = False) -> Decimal:
    """Calcula el saldo de los movimientos (Débito/Crédito) hasta una fecha dada.
    Si solo_no_conciliados es True, solo suma los movimientos con conciliado=False."""

    condicion_conciliado = "AND conciliado = false" if solo_no_conciliados else ""
    
    sum_sql = text(f"""
        SELECT COALESCE(SUM(
          CASE 
            WHEN tipo_mov IN ('DEPOSITO','TRANSFERENCIA_IN','CHEQUE_COBRADO') THEN monto
            WHEN tipo_mov IN ('RETIRO','TRANSFERENCIA_OUT','CHEQUE_EMITIDO') THEN -monto
            ELSE 0
          END
        ), 0)::numeric(18,2) AS saldo
        FROM bancos.movimientos_bancarios
        WHERE id_cuenta_bancaria = :id
          AND fecha::date <= :hasta
          {condicion_conciliado}
    """)
    
    row = session.exec(sum_sql, {"id": id_cuenta, "hasta": hasta}).first()
    return row[0] if row else Decimal("0.00")
  

def _seguimiento_bandera(session: Session, id_cuenta: int, f: date, saldo_banco: Decimal) -> dict:
    """
    Calcula y devuelve el seguimiento de la conciliación sin marcar movimientos ni insertar registros.
    """
    
    verificar_cuenta_activa(session, id_cuenta)
   
    saldo_no_conc = _calcular_saldo_movimientos(session, id_cuenta, f, solo_no_conciliados=True)
    saldo_libros = _calcular_saldo_movimientos(session, id_cuenta, f, solo_no_conciliados=False)

    diferencia = (saldo_banco - saldo_libros).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "fecha_conciliacion": str(f),
        "saldo_banco": str(saldo_banco),
        "saldo_libros_total": str(saldo_libros),
        "saldo_no_conciliado_hasta_fecha": str(saldo_no_conc),
        "diferencia_proyectada": str(diferencia),
    }


#--------------------------------------------------------------------------------


def crear_conciliacion(session: Session, id_cuenta: int, fecha_conciliacion: date | None,
                       saldo_banco: Decimal, observaciones: str | None) -> int:
  
    verificar_cuenta_activa(session, id_cuenta)
    
    f = fecha_conciliacion or date.today()
    
    saldo_libros = _calcular_saldo_movimientos(session, id_cuenta, f, solo_no_conciliados=False)
    
    # La diferencia se calcula entre el saldo del banco y el saldo total de libros
    diferencia = (saldo_banco - saldo_libros).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    #Marcar como conciliados y registrar conciliación en una sola transacción
    with session.begin():
      #Actualizar movimientos no conciliados
        upd = text("""
            UPDATE bancos.movimientos_bancarios
            SET conciliado = true
            WHERE id_cuenta_bancaria = :id
              AND fecha::date <= :hasta
              AND conciliado = false
        """)
        session.exec(upd, {"id": id_cuenta, "hasta": f})

        c = ConciliacionBancaria(
            id_cuenta_bancaria=id_cuenta,
            fecha_conciliacion=f,
            saldo_libros=saldo_libros,
            saldo_banco=saldo_banco,
            diferencia=diferencia,
            observaciones=observaciones
        )
        session.add(c)
        session.flush()
        return c.id_conciliacion
    

def listar_conciliaciones(session: Session, id_cuenta: int, desde: date | None, hasta: date | None, limit: int):
    verificar_cuenta_activa(session, id_cuenta)
    sql = """
      SELECT id_conciliacion, id_cuenta_bancaria, fecha_conciliacion,
             saldo_libros, saldo_banco, diferencia, observaciones
      FROM bancos.conciliaciones_bancarias
      WHERE id_cuenta_bancaria = :id
    """
    params = {"id": id_cuenta, "limit": limit}
    if desde:
        sql += " AND fecha_conciliacion >= :desde"
        params["desde"] = desde
    if hasta:
        sql += " AND fecha_conciliacion <= :hasta"
        params["hasta"] = hasta
    sql += " ORDER BY fecha_conciliacion DESC LIMIT :limit"

    rows = session.exec(text(sql), params).all()
    return [dict(r._mapping) for r in rows]




def _calcular_saldo_movimientos(session: Session, id_cuenta: int, hasta: date, solo_no_conciliados: bool = False) -> Decimal:
    """Calcula el saldo de los movimientos (Débito/Crédito) hasta una fecha dada.
    Si solo_no_conciliados es True, solo suma los movimientos con conciliado=False."""

    condicion_conciliado = "AND conciliado = false" if solo_no_conciliados else ""
    
    sum_sql = text(f"""
        SELECT COALESCE(SUM(
          CASE 
            WHEN tipo_mov IN ('DEPOSITO','TRANSFERENCIA_IN','CHEQUE_COBRADO') THEN monto
            WHEN tipo_mov IN ('RETIRO','TRANSFERENCIA_OUT','CHEQUE_EMITIDO') THEN -monto
            ELSE 0
          END
        ), 0)::numeric(18,2) AS saldo
        FROM bancos.movimientos_bancarios
        WHERE id_cuenta_bancaria = :id
          AND fecha::date <= :hasta
          {condicion_conciliado}
    """)
    
    row = session.exec(sum_sql, {"id": id_cuenta, "hasta": hasta}).first()
    return row[0] if row else Decimal("0.00")
  

def _seguimiento_bandera(session: Session, id_cuenta: int, f: date, saldo_banco: Decimal) -> dict:
    """
    Calcula y devuelve el seguimiento de la conciliación sin marcar movimientos ni insertar registros.
    """
    
    verificar_cuenta_activa(session, id_cuenta)
   
    saldo_no_conc = _calcular_saldo_movimientos(session, id_cuenta, f, solo_no_conciliados=True)
    saldo_libros = _calcular_saldo_movimientos(session, id_cuenta, f, solo_no_conciliados=False)

    diferencia = (saldo_banco - saldo_libros).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "fecha_conciliacion": str(f),
        "saldo_banco": str(saldo_banco),
        "saldo_libros_total": str(saldo_libros),
        "saldo_no_conciliado_hasta_fecha": str(saldo_no_conc),
        "diferencia_proyectada": str(diferencia),
    }


#--------------------------------------------------------------------------------


def crear_conciliacion(session: Session, id_cuenta: int, fecha_conciliacion: date | None,
                       saldo_banco: Decimal, observaciones: str | None) -> int:
  
    verificar_cuenta_activa(session, id_cuenta)
    
    f = fecha_conciliacion or date.today()
    
    saldo_libros = _calcular_saldo_movimientos(session, id_cuenta, f, solo_no_conciliados=False)
    
    # La diferencia se calcula entre el saldo del banco y el saldo total de libros
    diferencia = (saldo_banco - saldo_libros).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    #Marcar como conciliados y registrar conciliación en una sola transacción
    with session.begin():
      #Actualizar movimientos no conciliados
        upd = text("""
            UPDATE bancos.movimientos_bancarios
            SET conciliado = true
            WHERE id_cuenta_bancaria = :id
              AND fecha::date <= :hasta
              AND conciliado = false
        """)
        session.exec(upd, {"id": id_cuenta, "hasta": f})

        c = ConciliacionBancaria(
            id_cuenta_bancaria=id_cuenta,
            fecha_conciliacion=f,
            saldo_libros=saldo_libros,
            saldo_banco=saldo_banco,
            diferencia=diferencia,
            observaciones=observaciones
        )
        session.add(c)
        session.flush()
        return c.id_conciliacion
    

def listar_conciliaciones(session: Session, id_cuenta: int, desde: date | None, hasta: date | None, limit: int):
    verificar_cuenta_activa(session, id_cuenta)
    sql = """
      SELECT id_conciliacion, id_cuenta_bancaria, fecha_conciliacion,
             saldo_libros, saldo_banco, diferencia, observaciones
      FROM bancos.conciliaciones_bancarias
      WHERE id_cuenta_bancaria = :id
    """
    params = {"id": id_cuenta, "limit": limit}
    if desde:
        sql += " AND fecha_conciliacion >= :desde"
        params["desde"] = desde
    if hasta:
        sql += " AND fecha_conciliacion <= :hasta"
        params["hasta"] = hasta
    sql += " ORDER BY fecha_conciliacion DESC LIMIT :limit"

    rows = session.exec(text(sql), params).all()
    return [dict(r._mapping) for r in rows]

def listar_partidas_pendientes(session: Session, id_cuenta: int, hasta: date) -> Dict[str, List[Dict[str, Union[int, str, Decimal]]]]:
    
    ''' 
    Administrador ingresa el Saldo del Banco: Llama a crear_conciliacion(id_cuenta, fecha, saldo_banco, ...)

    Resultado: El sistema registra la ConciliacionBancaria y la diferencia.

    Administrador Solicita Partidas: Llama a la nueva función listar_partidas_pendientes(id_cuenta, fecha)

    Resultado: Obtiene una lista de movimientos y cheques que, según los libros, deberían estar pendientes de reflejarse en el banco.

    Análisis y Ajuste (Manual/Semi-Automático):

    El administrador compara esta lista de partidas_pendientes con los movimientos que no aparecen en el estado de cuenta del banco.

    Si un movimiento está en la lista y no está en el estado de cuenta, es una verdadera partida pendiente que explica parte de la diferencia.

    Si el administrador ve un movimiento en el estado de cuenta del banco (ej. una comisión o un cheque cobrado) que no está en sus libros (o su cheque está en 'EMITIDO'), debe:

    a) Registrar la Comisión: Crear un nuevo MovimientoBancario de tipo RETIRO por la comisión.

    b) Marcar el Cheque como Cobrado: Llamar a cobrar_cheque(id_cheque).

    El objetivo es que la suma de todos los movimientos y cheques no conciliados (los que lista la función) sea igual al valor de la diferencia en la tabla ConciliacionBancaria.
    '''
    verificar_cuenta_activa(session, id_cuenta)

    # 1. Movimientos en Libros No Conciliados (Depósitos/Retiros Pendientes)
    # Excluye CHEQUE_EMITIDO, ya que se maneja por separado en la tabla Cheque.
    # Se busca cualquier movimiento en la cuenta, antes o en la fecha límite, que NO esté conciliado.
    
    #Movimientos en Libros No Conciliados (Excluye Cheques)
    sql_movimientos = text("""
        SELECT 
            id_movimiento AS id,
            fecha,
            tipo_mov,
            monto,
            descripcion
        FROM bancos.movimientos_bancarios
        WHERE 
            id_cuenta_bancaria = :id_cuenta
            AND fecha::date <= :hasta
            AND conciliado = FALSE
            AND tipo_mov NOT IN ('CHEQUE_EMITIDO', 'CHEQUE_COBRADO')
        ORDER BY fecha
    """)
    
    movimientos_pendientes = session.exec(
        sql_movimientos, 
        {"id_cuenta": id_cuenta, "hasta": hasta}
    ).all()

    # 2. Cheques Emitidos y No Cobrados (Pendientes de Presentación al Banco)
    # Estos son un caso especial de "retiro" que aún no impacta el banco.
    sql_cheques = text("""
        SELECT 
            id_cheque AS id,
            fecha_emision AS fecha,
            'CHEQUE_EMITIDO' AS tipo_mov,
            monto,
            beneficiario AS descripcion
        FROM bancos.cheques
        WHERE 
            id_cuenta_bancaria = :id_cuenta
            AND fecha_emision <= :hasta
            AND estado = 'EMITIDO' 
        ORDER BY fecha_emision
    """)
    
    cheques_pendientes = session.exec(
        sql_cheques, 
        {"id_cuenta": id_cuenta, "hasta": hasta}
    ).all()

    return {
        "movimientos_pendientes": [dict(r._mapping) for r in movimientos_pendientes],
        "cheques_pendientes": [dict(r._mapping) for r in cheques_pendientes],
    }
    
