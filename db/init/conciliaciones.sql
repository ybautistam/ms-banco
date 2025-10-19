ALTER TABLE bancos.movimientos_bancarios
  ADD COLUMN conciliado boolean NOT NULL DEFAULT false;

-- 2) Índice para acelerar conciliaciones (solo pendientes)
CREATE INDEX IF NOT EXISTS idx_movs_no_conc
  ON bancos.movimientos_bancarios (id_cuenta_bancaria, fecha)
  WHERE conciliado = false;