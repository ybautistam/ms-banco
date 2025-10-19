-- Idempotencia de movimientos por referencia externa (si el cliente reintenta)
CREATE UNIQUE INDEX IF NOT EXISTS uq_mov_ref_externa
ON bancos.movimientos_bancarios (referencia_externa)
WHERE referencia_externa IS NOT NULL;