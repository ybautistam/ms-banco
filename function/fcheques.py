from sqlmodel import Session,select
from connection.models.modelos import Cheque, MovimientoBancario, TipoCheque
from fastapi import HTTPException, status
from decimal import Decimal
from function.fbancos import verificar_cuenta_activa, obtener_saldo

def emitir_cheque(session: Session, id_cuenta: int, id_tipo: int, numero: str,
                  beneficiario: str, monto: Decimal, referencia: str | None, observacion: str | None) -> int:
    verificar_cuenta_activa(session, id_cuenta)
    
    #validar saldo 
    saldo_actual = obtener_saldo(session, id_cuenta)
    if saldo_actual < monto:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Saldo insuficiente ({saldo_actual}) para emitir cheque de {monto}.")
    
    if not session.get(TipoCheque, id_tipo):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de cheque no existe")

    # Validar que el número no exista en esa cuenta
    exist = session.exec(
        select(Cheque.id_cheque).where(
            Cheque.id_cuenta_bancaria == id_cuenta,
            Cheque.numero_cheque == numero
        )
    ).first()
    if exist:
        raise HTTPException(status.HTTP_409_CONFLICT, "Número de cheque ya existe en la cuenta")

    with session.begin():
        #registrar cheque 
        ch = Cheque(
            id_cuenta_bancaria=id_cuenta,
            id_tipo_cheque=id_tipo,
            numero_cheque=numero,
            beneficiario=beneficiario,
            monto=monto,
            estado="EMITIDO",
        )
        session.add(ch)

        # Registrar retiro en movimientos bancarios
        mov = MovimientoBancario(
            id_cuenta_bancaria=id_cuenta,
            tipo_mov="CHEQUE_EMITIDO",
            monto=monto,
            referencia=referencia or f"Cheque {numero} a {beneficiario}",
            descripcion=observacion
        )
        session.add(mov)

        session.flush() #id del cheque y movimiento 
        
        mov.referencia_externa = str(ch.id_cheque)
        session.add(mov)
        return ch.id_cheque

def cobrar_cheque(session: Session, id_cheque: int) -> None:
    ch = session.get(Cheque, id_cheque)
    if not ch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cheque no existe")
    if ch.estado != "EMITIDO":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo cheques EMITIDOS se pueden cobrar")
    
    with session.begin():
        #actualizar estado del cheque
        ch.estado = "COBRADO"
        session.add(ch)
        
        # marcar movimiento asociado como conciliado
        # buscar en  MovimientoBancario de el tipo de cheque  asociado al cheque
        mov_asociado = session.exec(
            select(MovimientoBancario)
            .where(MovimientoBancario.referencia_externa == str(ch.id_cheque))
            .where(MovimientoBancario.tipo_mov == "CHEQUE_EMITIDO")
        ).first()

        if not mov_asociado:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail= "Movimiento bancario asociado al cheque no encontrado")
        
        mov_asociado.conciliado = True
        session.add(mov_asociado)
        
        

def anular_cheque(session: Session, id_cheque: int,motivo: str | None) -> None:
    ch = session.get(Cheque, id_cheque)
    if not ch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cheque no existe")
    if ch.estado != "EMITIDO":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo cheques EMITIDOS se pueden anular")
    
    with session.begin():
        ch.estado = "ANULADO"
        session.add(ch)
        
        # cambiar movimiento a deposito
        mov_reverso = MovimientoBancario(
            id_cuenta_bancaria=ch.id_cuenta_bancaria,
            tipo_mov="DEPOSITO",
            monto=ch.monto,
            referencia=f"Reverso Anulación Cheque {ch.numero_cheque}",
            descripcion=motivo or "Cheque anulado. Reverso de retiro en libros.",
            referencia_externa=f"ANULACION_{ch.id_cheque}", # Nueva referencia externa
            conciliado=False # Se conciliará con el movimiento original si aplica
        )
        session.add(mov_reverso)

        # Marcar el movimiento de CHEQUE_EMITIDO original como conciliado 
        # Esto lo saca de la lista de partidas pendientes si no quieres que aparezca.
        mov_original = session.exec(
            select(MovimientoBancario)
            .where(MovimientoBancario.referencia_externa == str(ch.id_cheque))
            .where(MovimientoBancario.tipo_mov == "CHEQUE_EMITIDO")
        ).first()
        
        if mov_original:
            mov_original.conciliado = True # Lo concilio para que no salga como pendiente
            session.add(mov_original)