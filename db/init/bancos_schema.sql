CREATE SCHEMA IF NOT EXISTS bancos;
-- Todo lo que sigue se crea dentro de 'bancos'

-- ===============================
-- Catálogos
-- ===============================
CREATE TABLE IF NOT EXISTS bancos.bancos (
  id_banco      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre_banco  VARCHAR(100) NOT NULL,
  direccion     VARCHAR(150),
  telefono      VARCHAR(8) CHECK (telefono ~ '^[0-9]{8}$'),
  activo        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS bancos.tipos_cuenta (
  id_tipo_cuenta INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  descripcion    VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bancos.tipos_moneda (
  id_tipo_moneda INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  codigo         VARCHAR(10) NOT NULL UNIQUE,  -- GTQ,
  descripcion    VARCHAR(50) NOT NULL
);

-- ===============================
-- Cuentas bancarias
-- ===============================
CREATE TABLE IF NOT EXISTS bancos.cuentas_bancarias (
  id_cuenta_bancaria INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_banco           INTEGER NOT NULL REFERENCES bancos.bancos(id_banco),
  id_tipo_cuenta     INTEGER NOT NULL REFERENCES bancos.tipos_cuenta(id_tipo_cuenta),
  id_tipo_moneda     INTEGER NOT NULL REFERENCES bancos.tipos_moneda(id_tipo_moneda),
  numero_cuenta      VARCHAR(30) NOT NULL,
  titular            VARCHAR(120) NOT NULL,
  estado             VARCHAR(12) NOT NULL DEFAULT 'ACTIVA'
                      CHECK (estado IN ('ACTIVA','INACTIVA','CERRADA')),
  fecha_apertura     DATE NOT NULL DEFAULT CURRENT_DATE,
  
  CONSTRAINT uq_cuenta UNIQUE (id_banco, numero_cuenta)
);

CREATE INDEX IF NOT EXISTS idx_cuentas_bancarias_banco ON bancos.cuentas_bancarias(id_banco);
CREATE INDEX IF NOT EXISTS idx_cuentas_bancarias_estado_activa ON bancos.cuentas_bancarias(id_banco)
  WHERE estado='ACTIVA';

-- ===============================
--  movimientos
-- ===============================
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = 'tipo_mov' AND n.nspname = 'bancos'
  ) THEN
    CREATE TYPE bancos.tipo_mov AS ENUM
      ('DEPOSITO','RETIRO','TRANSFERENCIA_IN','TRANSFERENCIA_OUT','CHEQUE_EMITIDO','CHEQUE_COBRADO');
  END IF;

  ALTER TYPE bancos.tipo_mov ADD VALUE IF NOT EXISTS 'DEPOSITO';
  ALTER TYPE bancos.tipo_mov ADD VALUE IF NOT EXISTS 'RETIRO';
  ALTER TYPE bancos.tipo_mov ADD VALUE IF NOT EXISTS 'TRANSFERENCIA_IN';
  ALTER TYPE bancos.tipo_mov ADD VALUE IF NOT EXISTS 'TRANSFERENCIA_OUT';
  ALTER TYPE bancos.tipo_mov ADD VALUE IF NOT EXISTS 'CHEQUE_EMITIDO';
  ALTER TYPE bancos.tipo_mov ADD VALUE IF NOT EXISTS 'CHEQUE_COBRADO';
END $$;


CREATE TABLE IF NOT EXISTS bancos.movimientos_bancarios (
  id_movimiento       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_cuenta_bancaria  INTEGER NOT NULL REFERENCES bancos.cuentas_bancarias(id_cuenta_bancaria),
  fecha               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tipo_mov            bancos.tipo_mov NOT NULL,
  monto               NUMERIC(18,2) NOT NULL CHECK (monto > 0),
  referencia          VARCHAR(60),
  descripcion         VARCHAR(250),
  referencia_externa  VARCHAR(60),     -- p.ej. id_pago_proveedor, id_cheque, id_conciliacion
  transferencia_id    UUID,            -- para parear in/out en transferencias internas
  usuario_registro    VARCHAR(60)
);

CREATE INDEX IF NOT EXISTS idx_movs_cuenta_fecha ON bancos.movimientos_bancarios(id_cuenta_bancaria, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_movs_ref_externa   ON bancos.movimientos_bancarios(referencia_externa);
CREATE INDEX IF NOT EXISTS idx_movs_transfer_id   ON bancos.movimientos_bancarios(transferencia_id);

-- ===============================
-- Cheques 
-- ===============================
CREATE TABLE IF NOT EXISTS bancos.tipos_cheque (
  id_tipo_cheque INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  descripcion    VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS bancos.cheques (
  id_cheque         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_cuenta_bancaria INTEGER NOT NULL REFERENCES bancos.cuentas_bancarias(id_cuenta_bancaria),
  id_tipo_cheque     INTEGER NOT NULL REFERENCES bancos.tipos_cheque(id_tipo_cheque),
  numero_cheque      VARCHAR(30) NOT NULL,
  fecha_emision      DATE NOT NULL DEFAULT CURRENT_DATE,
  beneficiario       VARCHAR(120) NOT NULL,
  monto              NUMERIC(18,2) NOT NULL CHECK (monto > 0),
  estado             VARCHAR(12) NOT NULL DEFAULT 'EMITIDO' 
                      CHECK (estado IN ('EMITIDO','COBRADO','ANULADO')),
  UNIQUE (id_cuenta_bancaria, numero_cheque)
);
CREATE INDEX IF NOT EXISTS idx_cheques_cuenta ON bancos.cheques(id_cuenta_bancaria);

-- ===============================
-- Conciliaciones
-- ===============================
CREATE TABLE IF NOT EXISTS bancos.conciliaciones_bancarias (
  id_conciliacion     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_cuenta_bancaria  INTEGER NOT NULL REFERENCES bancos.cuentas_bancarias(id_cuenta_bancaria),
  fecha_conciliacion  DATE NOT NULL DEFAULT CURRENT_DATE,
  saldo_libros        NUMERIC(18,2) NOT NULL,
  saldo_banco         NUMERIC(18,2) NOT NULL,
  diferencia          NUMERIC(18,2) NOT NULL,
  observaciones       TEXT
);
CREATE INDEX IF NOT EXISTS idx_conciliacion_cuenta_fecha ON bancos.conciliaciones_bancarias(id_cuenta_bancaria, fecha_conciliacion DESC);

-- ===============================
-- Proveedores y CxP (intermedio Compras)
-- ===============================
CREATE TABLE IF NOT EXISTS bancos.proveedores (
  proveedor_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre         VARCHAR(150) NOT NULL,
  nit            VARCHAR(10),
  telefono       VARCHAR(8) CHECK (telefono ~ '^[0-9]{8}$'),
  correo         VARCHAR(120),
  activo         BOOLEAN NOT NULL DEFAULT TRUE
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = 'estado_factura' AND n.nspname = 'bancos'
  ) THEN
    CREATE TYPE bancos.estado_factura AS ENUM
      ('PENDIENTE','PARCIAL','PAGADA','ANULADA');
  END IF;

  ALTER TYPE bancos.estado_factura ADD VALUE IF NOT EXISTS 'PENDIENTE';
  ALTER TYPE bancos.estado_factura ADD VALUE IF NOT EXISTS 'PARCIAL';
  ALTER TYPE bancos.estado_factura ADD VALUE IF NOT EXISTS 'PAGADA';
  ALTER TYPE bancos.estado_factura ADD VALUE IF NOT EXISTS 'ANULADA';
END $$;


CREATE TABLE IF NOT EXISTS bancos.facturas_compra (
  factura_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proveedor_id     BIGINT NOT NULL REFERENCES bancos.proveedores(proveedor_id),
  numero_factura   VARCHAR(40) NOT NULL,
  fecha_emision    DATE NOT NULL DEFAULT CURRENT_DATE,
  fecha_vencimiento DATE,
  moneda_id        INTEGER NOT NULL REFERENCES bancos.tipos_moneda(id_tipo_moneda),
  monto_total      NUMERIC(18,2) NOT NULL CHECK (monto_total >= 0),
  saldo_pendiente  NUMERIC(18,2) NOT NULL CHECK (saldo_pendiente >= 0),
  estado           bancos.estado_factura NOT NULL DEFAULT 'PENDIENTE',

  UNIQUE (proveedor_id, numero_factura),
  CONSTRAINT chk_fact_total CHECK (monto_total >= 0),
  CONSTRAINT chk_fact_saldo CHECK (saldo_pendiente >= 0 AND saldo_pendiente <= monto_total),
  CONSTRAINT chk_fact_fechas CHECK (fecha_vencimiento IS NULL OR fecha_vencimiento >= fecha_emision)
);
CREATE INDEX IF NOT EXISTS idx_facturas_prov_estado ON bancos.facturas_compra(proveedor_id, estado);
CREATE INDEX IF NOT EXISTS idx_facturas_estado     ON bancos.facturas_compra(estado);
CREATE INDEX IF NOT EXISTS idx_facturas_prov_venc  ON bancos.facturas_compra(proveedor_id, fecha_vencimiento);
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = 'forma_pago' AND n.nspname = 'bancos'
  ) THEN
    CREATE TYPE bancos.forma_pago AS ENUM
      ('TRANSFERENCIA','DEPOSITO','CHEQUE');
  END IF;

  ALTER TYPE bancos.forma_pago ADD VALUE IF NOT EXISTS 'TRANSFERENCIA';
  ALTER TYPE bancos.forma_pago ADD VALUE IF NOT EXISTS 'DEPOSITO';
  ALTER TYPE bancos.forma_pago ADD VALUE IF NOT EXISTS 'CHEQUE';
END $$;

CREATE TABLE IF NOT EXISTS bancos.pagos_proveedor (
  pago_id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  proveedor_id       BIGINT NOT NULL REFERENCES bancos.proveedores(proveedor_id),
  factura_id         BIGINT REFERENCES bancos.facturas_compra(factura_id), -- puede ser NULL si se abona a cuenta
  id_cuenta_bancaria INTEGER NOT NULL REFERENCES bancos.cuentas_bancarias(id_cuenta_bancaria),
  fecha_pago         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  monto_pagado       NUMERIC(18,2) NOT NULL CHECK (monto_pagado > 0),
  forma              bancos.forma_pago NOT NULL,
  referencia_banco   VARCHAR(60),
  observacion        VARCHAR(250)
);
CREATE INDEX IF NOT EXISTS idx_pagos_prov      ON bancos.pagos_proveedor(proveedor_id, fecha_pago DESC);
CREATE INDEX IF NOT EXISTS idx_pagos_factura   ON bancos.pagos_proveedor(factura_id);
CREATE INDEX IF NOT EXISTS idx_pagos_cuenta    ON bancos.pagos_proveedor(id_cuenta_bancaria);

-- consultas por moneda o cuenta activa
CREATE INDEX IF NOT EXISTS idx_cuentas_moneda   ON bancos.cuentas_bancarias(id_tipo_moneda);

CREATE INDEX IF NOT EXISTS idx_facturas_prov_venc ON bancos.facturas_compra(proveedor_id, fecha_vencimiento);
-- pendientes (parcial/pendiente) para dashboard
CREATE INDEX IF NOT EXISTS idx_facturas_pendientes ON bancos.facturas_compra(estado) WHERE estado IN ('PENDIENTE','PARCIAL');



-- ===============================
-- vistas para reportes 

-- Extracto con signo (positivo/negativo) por movimiento
CREATE OR REPLACE VIEW bancos.vw_extracto AS
SELECT
  m.id_cuenta_bancaria,
  m.fecha,
  m.tipo_mov,
  CASE 
    WHEN m.tipo_mov IN ('DEPOSITO','TRANSFERENCIA_IN','CHEQUE_COBRADO') THEN  m.monto
    WHEN m.tipo_mov IN ('RETIRO','TRANSFERENCIA_OUT','CHEQUE_EMITIDO')   THEN -m.monto
  END AS importe,
  m.referencia,
  m.descripcion,
  m.referencia_externa
FROM bancos.movimientos_bancarios m;

-- Saldo actual por cuenta (derivado de movimientos)
CREATE OR REPLACE VIEW bancos.vw_saldo_cuenta AS
SELECT
  c.id_cuenta_bancaria,
  COALESCE(SUM(importe), 0)::NUMERIC(18,2) AS saldo_calculado
FROM bancos.cuentas_bancarias c
LEFT JOIN bancos.vw_extracto e USING (id_cuenta_bancaria)
GROUP BY c.id_cuenta_bancaria;

-- Estado de cuentas por pagar por proveedor
CREATE OR REPLACE VIEW bancos.vw_cxp_proveedor AS
SELECT
  p.proveedor_id,
  p.nombre,
  COUNT(*) FILTER (WHERE f.estado IN ('PENDIENTE','PARCIAL')) AS facturas_abiertas,
  SUM(f.saldo_pendiente)::NUMERIC(14,2)                          AS total_pendiente
FROM bancos.proveedores p
LEFT JOIN bancos.facturas_compra f ON f.proveedor_id = p.proveedor_id
GROUP BY p.proveedor_id, p.nombre;

-- Detalle de facturas abiertas por proveedor
CREATE OR REPLACE VIEW bancos.vw_cxp_detalle AS
SELECT f.factura_id, f.proveedor_id, p.nombre AS proveedor,
       f.numero_factura, f.fecha_emision, f.fecha_vencimiento,
       f.monto_total, f.saldo_pendiente, f.estado
FROM bancos.facturas_compra f
JOIN bancos.proveedores p ON p.proveedor_id = f.proveedor_id
WHERE f.estado IN ('PENDIENTE','PARCIAL');

-- Resumen por moneda 

CREATE OR REPLACE VIEW bancos.vw_cxp_resumen_moneda AS
SELECT tm.codigo AS moneda,
       SUM(f.saldo_pendiente)::NUMERIC(18,2) AS total_pendiente
FROM bancos.facturas_compra f
JOIN bancos.tipos_moneda tm ON tm.id_tipo_moneda = f.moneda_id
WHERE f.estado IN ('PENDIENTE','PARCIAL')
GROUP BY tm.codigo;


INSERT INTO bancos.tipos_cuenta (descripcion) VALUES ('CORRIENTE'), ('AHORRO') ON CONFLICT DO NOTHING;
INSERT INTO bancos.tipos_moneda (codigo, descripcion) VALUES ('GTQ','Quetzal'),('USD','Dólar') ON CONFLICT DO NOTHING;

