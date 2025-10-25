from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import Optional, Literal
from connection.data.db import get_session
from connection.models.modelos import (
    MovimientoCreate, TransferenciaCreate, PagoProveedorCreate,
    BancoCreate, CuentaCreate, TipoMoneda, Banco, TipoCuenta, CuentaBancaria, AuthUsuario
)
from function.fbancos import (
    crear_movimiento, transferencia_interna, obtener_saldo,
    pago_a_proveedor, facturas_abiertas_por_proveedor
)
from function.fbanco_cuentas import listar_bancos, crear_banco, crear_cuenta, mostrar_catalogo
from services.seguridad_cliente import get_current_user

banco = APIRouter(
    prefix="/admin/bancos",
    responses={404: {"description": "Not found"}, 500: {"description": "Internal Server Error"}},
    tags=["bancos"],
)

# -------- Bancos --------
@banco.post("", status_code=201, dependencies=[])
def api_crear_banco(dto: BancoCreate, session: Session = Depends(get_session)):
    banco_id = crear_banco(session, dto.nombre_banco, dto.direccion, dto.telefono)
    return {"id_banco": banco_id}

@banco.get("", dependencies=[])
def api_listar_bancos(
    estado: Optional[Literal["ACTIVO", "INACTIVO"]] = "ACTIVO",
    session: Session = Depends(get_session),
):
    data = listar_bancos(session, estado)
    return {"items": data}

@banco.patch("/{id_banco}/estado", dependencies=[])
def api_cambiar_estado_banco(
    id_banco: int,
    nuevo_estado: Literal["ACTIVO", "INACTIVO"],
    session: Session = Depends(get_session),
):
    b = session.get(Banco, id_banco)
    if not b:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Banco no existe")
    b.activo = (nuevo_estado == "ACTIVO")
    session.add(b); session.commit(); session.refresh(b)
    return {"ok": True, "estado": "ACTIVO" if b.activo else "INACTIVO"}

# -------- Catálogos / Cuentas --------
@banco.get("/catalogos", dependencies=[])
def catalogos(session: Session = Depends(get_session)):
    return mostrar_catalogo(session)

@banco.post("/cuentas", status_code=201, dependencies=[])
def api_crear_cuenta(dto: CuentaCreate, session: Session = Depends(get_session)):
    if not session.get(Banco, dto.id_banco):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Banco no existe")
    if not session.get(TipoCuenta, dto.id_tipo_cuenta):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de cuenta no existe")
    if not session.get(TipoMoneda, dto.id_tipo_moneda):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tipo de moneda no existe")
    cuenta_id = crear_cuenta(
        session,
        id_banco=dto.id_banco, id_tipo_cuenta=dto.id_tipo_cuenta,
        id_tipo_moneda=dto.id_tipo_moneda, numero=dto.numero_cuenta,
        titular=dto.titular,
    )
    return {"id_cuenta_bancaria": cuenta_id}

@banco.get("/listcuentas", dependencies=[])
def api_listar_cuentas(
    banco_id: Optional[int] = None,
    moneda_id: Optional[int] = None,
    estado: Optional[str] = None,
    session: Session = Depends(get_session),
):
    q = select(CuentaBancaria)
    if banco_id is not None:
        q = q.where(CuentaBancaria.id_banco == banco_id)
    if moneda_id is not None:
        q = q.where(CuentaBancaria.id_tipo_moneda == moneda_id)
    if estado is not None:
        q = q.where(CuentaBancaria.estado == estado)
    rows = session.exec(q.order_by(CuentaBancaria.id_cuenta_bancaria.desc())).all()
    return {"items": [r.model_dump() for r in rows]}

@banco.patch("/cuentas/{id_cuenta}/estado", dependencies=[])
def api_cambiar_estado_cuenta(id_cuenta: int, nuevo_estado: str, session: Session = Depends(get_session)):
    if nuevo_estado not in ("ACTIVA", "INACTIVA", "CERRADA"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Estado inválido")
    c = session.get(CuentaBancaria, id_cuenta)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no existe")
    c.estado = nuevo_estado
    session.add(c); session.commit()
    return {"ok": True, "estado": c.estado}

# -------- Saldos / Movs / Transfer / Pagos --------
@banco.get("/saldos/{id_cuenta}", dependencies=[])
def obtener_saldo_cuenta(id_cuenta: int, session: Session = Depends(get_session)) -> dict:
    saldo = obtener_saldo(session, id_cuenta)
    return {"id_cuenta": id_cuenta, "saldo": str(saldo)}

@banco.post("/movimientos", status_code=status.HTTP_201_CREATED)
def crear_movimiento_bancario(
    mov: MovimientoCreate,
    session: Session = Depends(get_session),
    usuario: AuthUsuario = Depends(get_current_user),   # aquí sí usamos el usuario
) -> dict:
    id_mov = crear_movimiento(session, mov, usuario=usuario.nombre, usuario_rol=usuario.rol)
    return {"id_movimiento": id_mov, "detalle": mov.model_dump()}

@banco.post("/transferencias", status_code=status.HTTP_201_CREATED)
def realizar_transferencia(
    trans: TransferenciaCreate,
    session: Session = Depends(get_session),
    usuario: AuthUsuario = Depends(get_current_user),
):
    id_trans = transferencia_interna(session, trans, usuario=usuario.nombre, usuario_rol=usuario.rol)
    return {"id_transferencia": id_trans, "detalle": trans}

@banco.post("/pagos_proveedor", status_code=status.HTTP_201_CREATED)
def registrar_pago_proveedor(
    pago: PagoProveedorCreate,
    session: Session = Depends(get_session),
    usuario: AuthUsuario = Depends(get_current_user),
) -> dict:
    user_nombre = usuario.nombre or "system"
    id_pago = pago_a_proveedor(session, pago, usuario=user_nombre, usuario_rol=usuario.rol)
    return {"id_pago": id_pago, "detalle": pago}

@banco.get("/proveedor/{proveedor_id}/factura_abiertas", dependencies=[Depends(get_current_user)])
def obtener_facturas_abiertas(proveedor_id: int, limite: int = 20, session: Session = Depends(get_session)) -> list:
    facturas = facturas_abiertas_por_proveedor(session, proveedor_id, limite)
    return {"proveedor_id": proveedor_id, "facturas_abiertas": facturas}
