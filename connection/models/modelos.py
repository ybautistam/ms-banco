from sqlmodel import SQLModel, Field,Relationship
from typing import Optional, List,Literal
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import UniqueConstraint, Index, Column
from sqlalchemy.dialects.postgresql import UUID as SAUUID, ENUM as PGEnum
from sqlalchemy import Numeric, Boolean, text
from pydantic import BaseModel, Field as PydField
from enum import Enum

SCHEMA = "bancos"

TipoMovCol = Column(PGEnum(
    "DEPOSITO","RETIRO","TRANSFERENCIA_IN","TRANSFERENCIA_OUT","CHEQUE_EMITIDO","CHEQUE_COBRADO",
    name="tipo_mov", schema=SCHEMA, create_type=False
))

class EstadoFactura(str, Enum):
    PENDIENTE = "PENDIENTE"
    PARCIAL   = "PARCIAL"
    PAGADA    = "PAGADA"
    ANULADA   = "ANULADA"
    
EstadoFacturaCol = Column(PGEnum(
    "PENDIENTE","PARCIAL","PAGADA","ANULADA",
    name="estado_factura", schema=SCHEMA, create_type=False
))

class FormaPago(str, Enum):
    TRANSFERENCIA = "TRANSFERENCIA"
    DEPOSITO      = "DEPOSITO"
    CHEQUE        = "CHEQUE"
    

FormaPagoCol = Column(PGEnum(
    "TRANSFERENCIA","DEPOSITO","CHEQUE",
    name="forma_pago", schema=SCHEMA, create_type=False
))

#----------agregacion de nuevo modelo -------
class TipoMov(str, Enum):
    DEPOSITO = "DEPOSITO"
    RETIRO = "RETIRO"
    TRANSFERENCIA_IN = "TRANSFERENCIA_IN"
    TRANSFERENCIA_OUT = "TRANSFERENCIA_OUT"
    CHEQUE_EMITIDO = "CHEQUE_EMITIDO"
    CHEQUE_COBRADO = "CHEQUE_COBRADO"

#--------------------------------------

Dinero = Decimal 


# ---------- tablas  ----------


class Banco(SQLModel, table=True):
    __tablename__ = "bancos"
    __table_args__ = {"schema": SCHEMA}
    id_banco: Optional[int] = Field(default=None, primary_key=True)
    nombre_banco: str = Field(max_length=100)
    direccion: Optional[str] = Field(default=None, max_length=150)
    telefono: Optional[str] = Field(default=None, max_length=8)
    activo: bool = Field(default=True)

    cuentas: list["CuentaBancaria"] = Relationship(back_populates="banco")
    

class TipoCuenta(SQLModel, table=True):
    __tablename__ = "tipos_cuenta"
    __table_args__ = {"schema": SCHEMA}
    id_tipo_cuenta: Optional[int] = Field(default=None, primary_key=True)
    descripcion: str = Field(max_length=50)

class TipoMoneda(SQLModel, table=True):
    __tablename__ = "tipos_moneda"
    __table_args__ = {"schema": SCHEMA}
    id_tipo_moneda: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=10)
    descripcion: str = Field(max_length=50)

# ---------- Cuentas ----------
class CuentaBancaria(SQLModel, table=True):
    __tablename__ = "cuentas_bancarias"
    __table_args__ = (
        UniqueConstraint("id_banco", "numero_cuenta", name="uq_cuenta"),
        {"schema": SCHEMA},
    )
    id_cuenta_bancaria: Optional[int] = Field(default=None, primary_key=True)
    id_banco: int = Field(foreign_key=f"{SCHEMA}.bancos.id_banco")
    id_tipo_cuenta: int = Field(foreign_key=f"{SCHEMA}.tipos_cuenta.id_tipo_cuenta")
    id_tipo_moneda: int = Field(foreign_key=f"{SCHEMA}.tipos_moneda.id_tipo_moneda")
    numero_cuenta: str = Field(max_length=30)
    titular: str = Field(max_length=120)
    estado: str = Field(default="ACTIVA", max_length=12)
    fecha_apertura: date = Field(default_factory=date.today)

    banco: "Banco" = Relationship(back_populates="cuentas")
    movimientos: list["MovimientoBancario"] = Relationship(back_populates="cuenta")
    
# ---------- Movimientos ----------
class MovimientoBancario(SQLModel, table=True):
    __tablename__ = "movimientos_bancarios"
    __table_args__ = ({"schema": SCHEMA},)
    id_movimiento: Optional[int] = Field(default=None, primary_key=True)
    id_cuenta_bancaria: int = Field(foreign_key=f"{SCHEMA}.cuentas_bancarias.id_cuenta_bancaria")
    fecha: datetime = Field(default_factory=datetime.utcnow)
   
    #tipo_mov: str = Field(sa_column=TipoMovCol)
    tipo_mov: TipoMov = Field(sa_column=TipoMovCol)
    monto: Dinero = Field(sa_column=Column(Numeric(18, 2)))
    referencia: Optional[str] = Field(default=None, max_length=60)
    descripcion: Optional[str] = Field(default=None, max_length=250)
    referencia_externa: Optional[str] = Field(default=None, max_length=60)
    transferencia_id: Optional[str] = Field(default=None, sa_column=Column(SAUUID(as_uuid=False)))
    usuario_registro: Optional[str] = Field(default=None, max_length=60)
    
    conciliado: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false"))
    )

    cuenta: "CuentaBancaria" = Relationship(back_populates="movimientos")
    

# ---------- Cheques ----------
class TipoCheque(SQLModel, table=True):
    __tablename__ = "tipos_cheque"
    __table_args__ = {"schema": SCHEMA}
    id_tipo_cheque: Optional[int] = Field(default=None, primary_key=True)
    descripcion: str = Field(max_length=100)

class Cheque(SQLModel, table=True):
    __tablename__ = "cheques"
    __table_args__ = (
        UniqueConstraint("id_cuenta_bancaria", "numero_cheque", name="uq_cheque_cuenta_num"),
        {"schema": SCHEMA},
    )
    id_cheque: Optional[int] = Field(default=None, primary_key=True)
    id_cuenta_bancaria: int = Field(foreign_key=f"{SCHEMA}.cuentas_bancarias.id_cuenta_bancaria")
    id_tipo_cheque: int = Field(foreign_key=f"{SCHEMA}.tipos_cheque.id_tipo_cheque")
    numero_cheque: str = Field(max_length=30)
    fecha_emision: date = Field(default_factory=date.today)
    beneficiario: str = Field(max_length=120)
    monto: Dinero = Field(sa_column=Column(Numeric(18, 2)))
    estado: str = Field(default="EMITIDO", max_length=12)

# ---------- Conciliaciones ----------
class ConciliacionBancaria(SQLModel, table=True):
    __tablename__ = "conciliaciones_bancarias"
    __table_args__ = ({"schema": SCHEMA},)
    
    id_conciliacion: Optional[int] = Field(default=None, primary_key=True)
    id_cuenta_bancaria: int = Field(foreign_key=f"{SCHEMA}.cuentas_bancarias.id_cuenta_bancaria")
    fecha_conciliacion: date = Field(default_factory=date.today)
    saldo_libros: Dinero = Field(sa_column=Column(Numeric(18, 2)))
    saldo_banco: Dinero = Field(sa_column=Column(Numeric(18, 2)))
    diferencia: Dinero = Field(sa_column=Column(Numeric(18, 2)))
    observaciones: Optional[str] = None
    
#---------cuentas por pagar a proveedores
    
class Proveedor(SQLModel, table=True):
    __tablename__ = "proveedores"
    __table_args__ = {"schema": SCHEMA}
    proveedor_id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150)
    nit: Optional[str] = Field(default=None, max_length=10)
    telefono: Optional[str] = Field(default=None, max_length=8)
    correo: Optional[str] = Field(default=None, max_length=120)
    activo: bool = Field(default=True)

    facturas: list["FacturaCompra"] = Relationship(back_populates="proveedor")
    
    
class FacturaCompra(SQLModel, table=True):
    __tablename__ = "facturas_compra"
    __table_args__ = (
        UniqueConstraint("proveedor_id", "numero_factura", name="uq_factura_prov_num"),
        {"schema": SCHEMA},
    )
    factura_id: Optional[int] = Field(default=None, primary_key=True)
    proveedor_id: int = Field(foreign_key=f"{SCHEMA}.proveedores.proveedor_id")
    numero_factura: str = Field(max_length=40)
    fecha_emision: date = Field(default_factory=date.today)
    fecha_vencimiento: Optional[date] = None
    moneda_id: int = Field(foreign_key=f"{SCHEMA}.tipos_moneda.id_tipo_moneda")
    monto_total: Dinero = Field(sa_column=Column(Numeric(18,2)))
    saldo_pendiente: Dinero = Field(sa_column=Column(Numeric(18,2)))
    
    #estado: str = Field(sa_column=EstadoFacturaCol)
    estado: EstadoFactura = Field(sa_column=EstadoFacturaCol)

    proveedor: "Proveedor" = Relationship(back_populates="facturas")
    

class PagoProveedor(SQLModel, table=True):
    __tablename__ = "pagos_proveedor"
    __table_args__ = ({"schema": SCHEMA},)
    pago_id: Optional[int] = Field(default=None, primary_key=True)
    proveedor_id: int = Field(foreign_key=f"{SCHEMA}.proveedores.proveedor_id")
    factura_id: Optional[int] = Field(default=None, foreign_key=f"{SCHEMA}.facturas_compra.factura_id")
    id_cuenta_bancaria: int = Field(foreign_key=f"{SCHEMA}.cuentas_bancarias.id_cuenta_bancaria")
    fecha_pago: datetime = Field(default_factory=datetime.utcnow)
    monto_pagado: Dinero = Field(sa_column=Column(Numeric(18,2)))
    
    #forma: str = Field(sa_column=FormaPagoCol)
    forma: FormaPago = Field(sa_column=FormaPagoCol)
    
    referencia_banco: Optional[str] = Field(default=None, max_length=60)
    observacion: Optional[str] = Field(default=None, max_length=250)
    
    
#-------------mis dtos

class MovimientoCreate(BaseModel):
    id_cuenta_bancaria: int
    tipo_mov: Literal["DEPOSITO","RETIRO","TRANSFERENCIA_IN","TRANSFERENCIA_OUT","CHEQUE_EMITIDO","CHEQUE_COBRADO"]
    monto: Decimal = PydField(gt=0)
    referencia: Optional[str] = None
    descripcion: Optional[str] = None
    referencia_externa: Optional[str] = None
    
class TransferenciaCreate(BaseModel):
    origen: int
    destino: int
    monto: Decimal = PydField(gt=0)
    referencia: Optional[str] = None

class PagoProveedorCreate(BaseModel):
    proveedor_id: int
    factura_id: Optional[int] = None
    id_cuenta_bancaria: int
    monto_pagado: Decimal = PydField(gt=0)
    forma: Literal["TRANSFERENCIA","DEPOSITO","CHEQUE"]
    referencia_banco: Optional[str] = None
    observacion: Optional[str] = None

class BancoCreate(BaseModel):
    nombre_banco: str = Field(min_length=2, max_length=100)
    direccion: Optional[str] = Field(default=None, max_length=150)
    telefono: Optional[str] = Field(default=None, min_length=8, max_length=8)
    
class CuentaCreate(BaseModel):
    id_banco: int
    id_tipo_cuenta: int
    id_tipo_moneda: int
    numero_cuenta: str = Field(min_length=4, max_length=30)
    titular: str = Field(min_length=2, max_length=120)
    
class EmitirCheque(BaseModel):
    id_cuenta_bancaria: int
    id_tipo_cheque: int
    numero_cheque: str = Field(min_length=1, max_length=30)
    beneficiario: str = Field(min_length=1, max_length=120)
    monto: Decimal = Field(gt=0)
    referencia: Optional[str] = None
    

class CobrarCheque(BaseModel):
 
    pass
class AnularCheque(BaseModel):
    motivo: Optional[str] = None
    
class ConciliacionCreate(BaseModel):
    
    id_cuenta_bancaria: int
    saldo_banco: Decimal = Field(gt=Decimal("0"))
    fecha_conciliacion: Optional[date] = None
    observaciones: Optional[str] = None
    # Si preview=True solo calcula y NO marca movimientos ni inserta conciliación
    bandera: bool = False
    
class ConciliacionQuery(BaseModel):
    id_cuenta_bancaria: int
    desde: Optional[date] = None
    hasta: Optional[date] = None
    limit: int = Field(default=100, gt=1, le=1000)
    
class FacturaCreate(BaseModel):
    proveedor_id: int
    numero_factura: str = Field(min_length=1, max_length=40)
    moneda_id: int
    monto_total: Decimal = Field(ge=0)
    fecha_vencimiento: Optional[date] = None
    
class FacturaAnular(BaseModel):
    motivo: Optional[str] = None
    
#--------------------------
class AuthUsuario(BaseModel):
    sub: str | None = None
    email: str | None = None
    scopes: list[str] = []