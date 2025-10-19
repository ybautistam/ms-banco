-- pagos por fecha
CREATE INDEX IF NOT EXISTS idx_pagos_fecha
ON bancos.pagos_proveedor (fecha_pago);

-- facturas por fecha de emisión 
CREATE INDEX IF NOT EXISTS idx_facturas_emision
ON bancos.facturas_compra (fecha_emision);