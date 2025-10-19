from sqlmodel import Session,select
from connection.models.modelos import Proveedor, FacturaCompra
from fastapi import HTTPException, status
from datetime import date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError


# def crear_proveedor(session: Session, nombre: str, nit: str | None) -> int:
#     try:
#         existing = session.exec(
#             select(Proveedor).where(Proveedor.nombre == nombre, Proveedor.activo == True)
#         ).first()
#         if existing:
#             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail= "Proveedor ya existe")
        
#         p = Proveedor(nombre=nombre, nit=nit, activo=True)
#         session.add(p); session.commit(); session.refresh(p)
#         return p.proveedor_id
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail= f"Error al verificar proveedor existente: {str(e)}")

def crear_factura(session: Session, proveedor_id: int, numero: str,
                  moneda_id: int, monto_total: Decimal, fecha_vencimiento: date | None) -> int:
    
    if not session.get(Proveedor, proveedor_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no existe")

    # 1. Validación Previa de Unicidad
    existe = session.exec(
        select(FacturaCompra.factura_id)
        .where(FacturaCompra.proveedor_id == proveedor_id)
        .where(FacturaCompra.numero_factura == numero)
    ).first()
    if existe:
        raise HTTPException(status.HTTP_409_CONFLICT, 
                            f"Ya existe la factura {numero} para el proveedor {proveedor_id}.")

    # 2. Creación con Auditoría
    f = FacturaCompra(
        proveedor_id=proveedor_id,
        numero_factura=numero,
        moneda_id=moneda_id,
        monto_total=monto_total,
        saldo_pendiente=monto_total,
        fecha_vencimiento=fecha_vencimiento,
        estado="PENDIENTE",
        # usuario_registro=usuario_registro # Asumiendo que agregas esta columna al modelo
    )
    
    try:
        session.add(f)
        session.commit()
        session.refresh(f)
        return f.factura_id
    except IntegrityError as e:
         # Capturar cualquier otro error de unicidad que no se haya prevenido
        session.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al grabar factura: Violación de integridad.")


def anular_factura(session: Session, factura_id: int,) -> None: # <-- Recibir motivo
    f = session.get(FacturaCompra, factura_id)
    if not f:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Factura no existe")
    if f.estado in ("PAGADA", "ANULADA"):
        # Mejorar el mensaje si ya está anulada
        msg = "No puedes anular una factura ya pagada." if f.estado == "PAGADA" else "La factura ya está ANULADA."
        raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)
        
    f.estado = "ANULADA"
    session.add(f) 
    session.commit()