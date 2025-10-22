from sqlmodel import Session,select
from sqlalchemy.exc import IntegrityError
from connection.models.modelos import Banco, CuentaBancaria,TipoCuenta, TipoMoneda
from fastapi import HTTPException, status

def crear_banco(session: Session, nombre: str, direccion: str | None, telefono: str | None) -> int:
    try: 
        
        b = Banco(nombre_banco=nombre, direccion=direccion, telefono=telefono, activo=True)
        session.add(b); session.commit(); session.refresh(b)
        return b.id_banco
    except IntegrityError as e:
        session.rollback()
        # Asume que si falla es por el UniqueConstraint de nombre (si lo agregaste al modelo)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'Ya existe un banco con el nombre: {nombre}')from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Error al crear banco: {str(e)}')

def listar_bancos(session: Session,estado: str = "ACTIVO") -> list[dict]:
    '''listar bancos con filtro de activo o inactivo '''
    try: 
        q = select(Banco)
        if estado == "ACTIVO":
            q = q.where(Banco.activo == True)
        elif estado == "INACTIVO": 
            q = q.where(Banco.activo == False)
        rows = session.exec(q.order_by(Banco.nombre_banco)).all()
        return {"items" : [r.dict() for r in rows]}
    except Exception as e: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error al listar bancos: {str(e)}")
          

def crear_cuenta(session: Session, id_banco: int, id_tipo_cuenta: int, id_tipo_moneda: int,
                 numero: str, titular: str) -> int:
    verificar_banco = session.get(Banco, id_banco)
    #verificaciones 
    if not verificar_banco or not verificar_banco.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Banco no existe/activo")
    
    if not session.get(TipoCuenta, id_tipo_cuenta):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de cuenta no existe")
    
    if not session.get(TipoMoneda, id_tipo_moneda):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de moneda no existe")
    
    c = CuentaBancaria(
        id_banco=id_banco, id_tipo_cuenta=id_tipo_cuenta, id_tipo_moneda=id_tipo_moneda,
        numero_cuenta=numero, titular=titular, estado="ACTIVA"
    )
    try:
        session.add(c)
        session.commit()
        session.refresh(c)
        return c.id_cuenta_bancaria
    except IntegrityError as e:
        session.rollback()
        
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El número de cuenta ya está registrado para este banco.") from e
